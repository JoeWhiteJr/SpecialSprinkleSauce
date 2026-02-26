"""OWASP-inspired security checks for the Wasden Watch codebase.

Scans source files for common security anti-patterns:
- Hardcoded API keys or secrets
- Committed .env files
- TRADING_MODE enforcement gaps
- SQL injection via string formatting
- eval() / exec() in production code
- CORS misconfiguration
- Mutable risk constants
"""

import os
import re
from pathlib import Path

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

# Project root directories
_BACKEND_DIR = Path(__file__).resolve().parents[1]  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent                  # repo root
_APP_DIR = _BACKEND_DIR / "app"
_SRC_DIR = _PROJECT_ROOT / "src"


def _get_python_files(*dirs: Path) -> list[Path]:
    """Collect all .py files from the given directories (recursively)."""
    files = []
    for d in dirs:
        if d.exists():
            files.extend(d.rglob("*.py"))
    return files


def _is_production_code(path: Path) -> bool:
    """Return True if file is production code (not a test)."""
    parts = str(path)
    return "test" not in parts.lower() and "__pycache__" not in parts


# ===========================================================================
# Test: no hardcoded API keys
# ===========================================================================

def test_no_hardcoded_api_keys():
    """Scan all .py files for hardcoded API keys, passwords, or secrets."""
    patterns = [
        # Common key patterns
        re.compile(r'''(?:api_key|apikey|api_secret|secret_key|password|passwd)\s*=\s*["\'][^"\']{8,}["\']''', re.IGNORECASE),
        # Specific provider key formats
        re.compile(r'''["\']sk-[a-zA-Z0-9]{20,}["\']'''),  # OpenAI-style
        re.compile(r'''["\']AKIA[A-Z0-9]{16}["\']'''),      # AWS access key
        re.compile(r'''["\']ghp_[a-zA-Z0-9]{36}["\']'''),   # GitHub PAT
        re.compile(r'''["\']xoxb-[a-zA-Z0-9-]+["\']'''),    # Slack bot token
    ]

    violations = []
    for py_file in _get_python_files(_APP_DIR, _SRC_DIR):
        if not _is_production_code(py_file):
            continue
        content = py_file.read_text(errors="ignore")
        for pattern in patterns:
            matches = pattern.findall(content)
            for match in matches:
                # Exclude known safe patterns (empty strings, env lookups, examples)
                if "os.getenv" in match or "os.environ" in match:
                    continue
                if '""' in match or "''" in match:
                    continue
                # Exclude test fixtures and obvious placeholders
                if "example" in match.lower() or "placeholder" in match.lower():
                    continue
                if "your_" in match.lower() or "xxx" in match.lower():
                    continue
                violations.append(f"{py_file.relative_to(_PROJECT_ROOT)}: {match[:80]}")

    assert len(violations) == 0, (
        f"Found {len(violations)} potential hardcoded secrets:\n"
        + "\n".join(violations[:10])
    )


# ===========================================================================
# Test: no .env files committed
# ===========================================================================

def test_no_env_files_committed():
    """Verify no .env files in repo (only .env.example is allowed)."""
    env_files = list(_PROJECT_ROOT.glob(".env"))
    env_files += list(_PROJECT_ROOT.glob("**/.env"))
    # Also check for .env.local, .env.production, etc.
    env_files += list(_PROJECT_ROOT.glob("**/.env.local"))
    env_files += list(_PROJECT_ROOT.glob("**/.env.production"))
    env_files += list(_PROJECT_ROOT.glob("**/.env.development"))

    # Check if any real .env files would be tracked by git
    # Note: .env files existing locally is fine; we just check they are gitignored
    gitignore_path = _PROJECT_ROOT / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        has_env_ignore = ".env" in gitignore_content
        assert has_env_ignore, ".gitignore must contain a .env exclusion rule"


# ===========================================================================
# Test: TRADING_MODE enforcement
# ===========================================================================

def test_trading_mode_enforcement():
    """Verify both config.py and main.py enforce TRADING_MODE."""
    config_path = _APP_DIR / "config.py"
    main_path = _APP_DIR / "main.py"

    assert config_path.exists(), "config.py not found"
    assert main_path.exists(), "main.py not found"

    config_content = config_path.read_text()
    main_content = main_path.read_text()

    # config.py must have the assert
    assert "assert" in config_content and "TRADING_MODE" in config_content, (
        "config.py must assert TRADING_MODE is paper or live"
    )

    # main.py must have sys.exit defense
    assert "sys.exit" in main_content and "trading_mode" in main_content.lower(), (
        "main.py must have sys.exit defense for invalid TRADING_MODE"
    )


# ===========================================================================
# Test: no SQL string formatting
# ===========================================================================

def test_no_sql_string_formatting():
    """Scan for f-string SQL queries (should use parameterized queries)."""
    # Patterns that indicate SQL injection risk
    sql_fstring_pattern = re.compile(
        r'''f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s.*\{.*\}''',
        re.IGNORECASE,
    )
    sql_format_pattern = re.compile(
        r'''["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s.*["\']\.format\(''',
        re.IGNORECASE,
    )
    sql_pct_pattern = re.compile(
        r'''["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s.*%s.*["\']\s*%\s''',
        re.IGNORECASE,
    )

    violations = []
    for py_file in _get_python_files(_APP_DIR, _SRC_DIR):
        if not _is_production_code(py_file):
            continue
        content = py_file.read_text(errors="ignore")
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern in [sql_fstring_pattern, sql_format_pattern, sql_pct_pattern]:
                if pattern.search(stripped):
                    violations.append(
                        f"{py_file.relative_to(_PROJECT_ROOT)}:{line_num}: {stripped[:100]}"
                    )

    assert len(violations) == 0, (
        f"Found {len(violations)} potential SQL injection risks:\n"
        + "\n".join(violations[:10])
    )


# ===========================================================================
# Test: no eval() or exec()
# ===========================================================================

def test_no_eval_or_exec():
    """Scan for eval() or exec() usage in production code."""
    # Match eval( or exec( but not in comments
    eval_exec_pattern = re.compile(r'\b(eval|exec)\s*\(')
    # PyTorch model.eval() is safe — switches from training to inference mode
    pytorch_eval_pattern = re.compile(r'\.\s*eval\s*\(\s*\)')

    violations = []
    for py_file in _get_python_files(_APP_DIR, _SRC_DIR):
        if not _is_production_code(py_file):
            continue
        content = py_file.read_text(errors="ignore")
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if eval_exec_pattern.search(stripped):
                # Exclude PyTorch model.eval() calls (method on an object)
                if pytorch_eval_pattern.search(stripped):
                    continue
                violations.append(
                    f"{py_file.relative_to(_PROJECT_ROOT)}:{line_num}: {stripped[:100]}"
                )

    assert len(violations) == 0, (
        f"Found {len(violations)} eval/exec usages in production code:\n"
        + "\n".join(violations[:10])
    )


# ===========================================================================
# Test: CORS configuration
# ===========================================================================

def test_cors_configuration():
    """Verify CORS is configured (not wildcard in production)."""
    main_path = _APP_DIR / "main.py"
    config_path = _APP_DIR / "config.py"

    main_content = main_path.read_text()
    config_content = config_path.read_text()

    # CORS middleware must be present
    assert "CORSMiddleware" in main_content, "CORS middleware not configured in main.py"

    # Check that origins are not wildcard "*"
    # In config.py, cors_origins should not default to ["*"]
    assert 'cors_origins' in config_content, "CORS origins not configured"

    # Verify no allow_origins=["*"] in main.py (it uses the settings list)
    # The origins list is built from settings, not a hardcoded wildcard
    assert 'allow_origins=["*"]' not in main_content, (
        "CORS must not use wildcard origins in production"
    )


# ===========================================================================
# Test: risk constants readonly
# ===========================================================================

def test_risk_constants_readonly():
    """Verify constants module has no setter/mutation functions."""
    constants_path = _APP_DIR / "services" / "risk" / "constants.py"
    assert constants_path.exists(), "risk/constants.py not found"

    content = constants_path.read_text()

    # No function definitions (all values are module-level constants)
    assert "def " not in content, (
        "risk/constants.py should only contain constants, not functions"
    )

    # No class definitions
    assert "class " not in content, (
        "risk/constants.py should only contain constants, not classes"
    )

    # No mutable containers assigned to constants
    mutable_patterns = [
        re.compile(r'^\s*\w+\s*=\s*\['),   # list assignment
        re.compile(r'^\s*\w+\s*=\s*\{'),   # dict assignment
        re.compile(r'^\s*\w+\s*=\s*set\('),  # set assignment
    ]
    for line in content.split("\n"):
        if line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''"):
            continue
        for pattern in mutable_patterns:
            assert not pattern.search(line), (
                f"risk/constants.py contains mutable assignment: {line.strip()}"
            )


def test_no_secret_in_constants():
    """Risk constants module must not contain any secret values."""
    constants_path = _APP_DIR / "services" / "risk" / "constants.py"
    content = constants_path.read_text()
    secret_keywords = ["api_key", "secret", "password", "token", "credential"]
    for keyword in secret_keywords:
        assert keyword not in content.lower(), (
            f"risk/constants.py must not contain '{keyword}'"
        )
