"""Postgres-backed drop-in replacement for the Supabase client.

Migration SSS-T008: Wasden Watch moved off Supabase to a self-hosted
PostgreSQL database on the "daisy" server. Rather than rewrite the ~129
call sites that use the supabase-py query builder, this module reimplements
the *subset* of that fluent API the backend actually uses, executing directly
against local Postgres via psycopg.

Supported surface (verified against the codebase):
    client.table(name) / client.from_(name)
      .select(cols) .insert(v) .update(v) .upsert(v, on_conflict=) .delete()
      .eq/.neq/.gt/.gte/.lt/.lte(col, val) .in_(col, vals) .ilike(col, pat)
      .order(col, desc=) .limit(n) .range(start, end) .single()
      .execute()  -> APIResponse(data=..., count=...)

Fidelity notes:
    * filter/order columns support PostgREST-style jsonb paths, e.g.
      "final_decision->>action" -> "final_decision"->>'action'.
    * .single() returns data=<row dict> for exactly one match, else data=None
      (matches call sites that do `if not result.data:`), never raising.
    * insert/update/upsert/delete use RETURNING *, so .data holds affected rows.
    * jsonb/json columns are auto-wrapped with psycopg Jsonb(); Postgres ARRAY
      columns receive Python lists unchanged (introspected from the schema).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from psycopg.types.json import Jsonb
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_JSONPATH_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)((?:->>?[A-Za-z0-9_]+)+)$")


def _ident(name: str) -> str:
    """Validate and double-quote a SQL identifier.

    Table/column names originate from code literals, not user input, but we
    validate defensively so a bad literal fails loudly rather than injecting.
    """
    name = name.strip()
    if not _IDENT_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return f'"{name}"'


def _column_expr(col: str) -> str:
    """Quote a column, supporting PostgREST-style jsonb paths.

    Plain 'col' -> "col"; 'meta->>action' -> "meta"->>'action';
    'a->b->>c' -> "a"->'b'->>'c'. Keys are validated as identifiers.
    """
    col = col.strip()
    if "->" not in col:
        return _ident(col)
    m = _JSONPATH_RE.match(col)
    if not m:
        raise ValueError(f"Unsupported column expression: {col!r}")
    expr = _ident(m.group(1))
    for op, key in re.findall(r"(->>?)([A-Za-z0-9_]+)", m.group(2)):
        expr += f"{op}'{key}'"
    return expr


@dataclass
class APIResponse:
    """Mirror of supabase-py's response object (only .data/.count are read)."""

    data: Any = None
    count: int | None = None


# --- connection pool ---------------------------------------------------------

_pool: ConnectionPool | None = None
_column_types: dict[str, dict[str, str]] = {}


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        dsn = settings.database_url
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL not configured. Set DATABASE_URL in .env "
                "(self-hosted Postgres) — see ticket SSS-T008."
            )
        _pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=10,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=False,
        )
        _pool.open()
    return _pool


def _table_types(table: str) -> dict[str, str]:
    """Return {column: data_type} for a table, cached. Used to decide jsonb
    wrapping vs. native array/scalar binding."""
    if table not in _column_types:
        pool = _get_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            )
            _column_types[table] = {r["column_name"]: r["data_type"] for r in cur.fetchall()}
    return _column_types[table]


def _adapt(table: str, col: str, value: Any) -> Any:
    """Adapt a Python value for binding based on the destination column type."""
    if value is None:
        return None
    dtype = _table_types(table).get(col)
    if dtype in ("jsonb", "json") and isinstance(value, (dict, list)):
        return Jsonb(value)
    return value  # scalars, and Python lists destined for ARRAY columns, pass through


# --- query builder -----------------------------------------------------------


class _Query:
    def __init__(self, table: str):
        self._table = table
        self._op = "select"
        self._columns = "*"
        self._payload: Any = None
        self._on_conflict: str | None = None
        self._filters: list[tuple[str, str, Any]] = []
        self._in: list[tuple[str, list]] = []
        self._ilike: list[tuple[str, str]] = []
        self._order: list[tuple[str, bool]] = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._single = False

    # operation selectors
    def select(self, columns: str = "*", count: str | None = None) -> "_Query":
        self._op, self._columns = "select", (columns or "*")
        return self

    def insert(self, values: Any) -> "_Query":
        self._op, self._payload = "insert", values
        return self

    def update(self, values: dict) -> "_Query":
        self._op, self._payload = "update", values
        return self

    def upsert(self, values: Any, on_conflict: str | None = None) -> "_Query":
        self._op, self._payload, self._on_conflict = "upsert", values, on_conflict
        return self

    def delete(self) -> "_Query":
        self._op = "delete"
        return self

    # filters
    def _add(self, col: str, op: str, val: Any) -> "_Query":
        self._filters.append((col, op, val))
        return self

    def eq(self, col, val):
        return self._add(col, "=", val)

    def neq(self, col, val):
        return self._add(col, "<>", val)

    def gt(self, col, val):
        return self._add(col, ">", val)

    def gte(self, col, val):
        return self._add(col, ">=", val)

    def lt(self, col, val):
        return self._add(col, "<", val)

    def lte(self, col, val):
        return self._add(col, "<=", val)

    def in_(self, col, vals):
        self._in.append((col, list(vals)))
        return self

    def ilike(self, col, pattern):
        self._ilike.append((col, pattern))
        return self

    # modifiers
    def order(self, col: str, desc: bool = False) -> "_Query":
        self._order.append((col, desc))
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "_Query":
        # supabase .range() is inclusive on both ends
        self._offset = start
        self._limit = end - start + 1
        return self

    def single(self) -> "_Query":
        self._single = True
        return self

    # execution
    def _where(self) -> tuple[str, list]:
        clauses: list[str] = []
        params: list[Any] = []
        for col, op, val in self._filters:
            clauses.append(f"{_column_expr(col)} {op} %s")
            params.append(_adapt(self._table, col, val))
        for col, vals in self._in:
            clauses.append(f"{_column_expr(col)} = ANY(%s)")
            params.append(list(vals))
        for col, pat in self._ilike:
            clauses.append(f"{_column_expr(col)} ILIKE %s")
            params.append(pat)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def _run(self, sql: str, params: list) -> list[dict]:
        pool = _get_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return []
            return cur.fetchall()

    def _rows(self) -> list[dict]:
        payload = self._payload
        return payload if isinstance(payload, list) else [payload]

    def _write_rows(self, tbl: str, rows: list[dict], conflict: str | None) -> APIResponse:
        rows = [r for r in rows if r is not None]
        if not rows:
            return APIResponse(data=[], count=0)
        cols: list[str] = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        col_sql = ", ".join(_ident(c) for c in cols)
        row_ph = "(" + ", ".join(["%s"] * len(cols)) + ")"
        values_sql = ", ".join([row_ph] * len(rows))
        params: list[Any] = []
        for r in rows:
            for c in cols:
                params.append(_adapt(self._table, c, r.get(c)))
        sql = f"INSERT INTO {tbl} ({col_sql}) VALUES {values_sql}"
        if conflict is not None:
            targets = [c.strip() for c in conflict.split(",")]
            target_sql = ", ".join(_ident(c) for c in targets)
            updatable = [c for c in cols if c not in targets]
            if updatable:
                set_sql = ", ".join(f"{_ident(c)} = EXCLUDED.{_ident(c)}" for c in updatable)
                sql += f" ON CONFLICT ({target_sql}) DO UPDATE SET {set_sql}"
            else:
                sql += f" ON CONFLICT ({target_sql}) DO NOTHING"
        sql += " RETURNING *"
        result = self._run(sql, params)
        return APIResponse(data=result, count=len(result))

    def execute(self) -> APIResponse:
        tbl = _ident(self._table)

        if self._op == "select":
            if self._columns.strip() == "*":
                cols = "*"
            else:
                cols = ", ".join(_ident(c.strip()) for c in self._columns.split(","))
            where, params = self._where()
            sql = f"SELECT {cols} FROM {tbl}{where}"
            if self._order:
                sql += " ORDER BY " + ", ".join(
                    f"{_column_expr(c)} {'DESC' if d else 'ASC'}" for c, d in self._order
                )
            if self._limit is not None:
                sql += " LIMIT %s"
                params.append(self._limit)
            if self._offset is not None:
                sql += " OFFSET %s"
                params.append(self._offset)
            rows = self._run(sql, params)
            if self._single:
                return APIResponse(data=(rows[0] if rows else None), count=len(rows))
            return APIResponse(data=rows, count=len(rows))

        if self._op == "insert":
            return self._write_rows(tbl, self._rows(), conflict=None)

        if self._op == "upsert":
            return self._write_rows(tbl, self._rows(), conflict=self._on_conflict)

        if self._op == "update":
            cols = list(self._payload.keys())
            set_sql = ", ".join(f"{_ident(c)} = %s" for c in cols)
            params = [_adapt(self._table, c, self._payload[c]) for c in cols]
            where, wparams = self._where()
            params += wparams
            sql = f"UPDATE {tbl} SET {set_sql}{where} RETURNING *"
            rows = self._run(sql, params)
            return APIResponse(data=rows, count=len(rows))

        if self._op == "delete":
            where, params = self._where()
            sql = f"DELETE FROM {tbl}{where} RETURNING *"
            rows = self._run(sql, params)
            return APIResponse(data=rows, count=len(rows))

        raise ValueError(f"Unsupported operation: {self._op}")


class PostgresClient:
    """Stands in for supabase.Client — only .table()/.from_() are used."""

    def table(self, name: str) -> _Query:
        return _Query(name)

    def from_(self, name: str) -> _Query:
        return _Query(name)


_client: PostgresClient | None = None


def get_supabase() -> PostgresClient:
    """Return the singleton Postgres client (name kept for call-site compatibility)."""
    global _client
    if _client is None:
        _client = PostgresClient()
    return _client


def check_connection() -> bool:
    """Quick connectivity check. Returns True if the local Postgres responds."""
    if settings.use_mock_data:
        return False
    try:
        get_supabase().table("system_settings").select("*").limit(1).execute()
        return True
    except Exception:
        return False
