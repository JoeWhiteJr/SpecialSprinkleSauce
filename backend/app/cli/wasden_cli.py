"""
CLI tool for the Wasden Watch RAG pipeline.

Usage:
    python -m app.cli.wasden_cli ingest
    python -m app.cli.wasden_cli verdict NVDA --company "NVIDIA" --sector "Technology"
    python -m app.cli.wasden_cli stats
    python -m app.cli.wasden_cli search "inflation Federal Reserve" --top-k 5
    python -m app.cli.wasden_cli pilot
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Configure logging before imports that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("wasden_watch.cli")

# Add project root to path so src.intelligence can be imported
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Try to import colorama for colored output
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def _color(text: str, color: str) -> str:
    """Apply color if colorama is available."""
    if not HAS_COLOR:
        return text
    color_map = {
        "green": Fore.GREEN,
        "red": Fore.RED,
        "yellow": Fore.YELLOW,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "white": Fore.WHITE,
        "bold": Style.BRIGHT,
        "reset": Style.RESET_ALL,
    }
    c = color_map.get(color, "")
    return f"{c}{text}{Style.RESET_ALL}" if c else text


def _verdict_color(verdict: str) -> str:
    """Color-code a verdict string."""
    if verdict == "APPROVE":
        return _color(verdict, "green")
    elif verdict == "VETO":
        return _color(verdict, "red")
    return _color(verdict, "yellow")


PILOT_TICKERS = ["NVDA", "PYPL", "NFLX", "TSM", "XOM", "AAPL", "MSFT", "AMZN", "TSLA", "AMD", "GOOGL"]


def cmd_ingest(args: argparse.Namespace) -> None:
    """Process PDFs and ingest into vector store."""
    from src.intelligence.wasden_watch.config import WasdenWatchSettings
    from src.intelligence.wasden_watch.pdf_processor import PDFProcessor
    from src.intelligence.wasden_watch.vector_store import VectorStore

    settings = WasdenWatchSettings()
    processor = PDFProcessor(settings)
    store = VectorStore(settings)

    print(_color("Processing PDF corpus...", "cyan"))
    documents, chunks = processor.process_corpus()
    print(f"  Extracted {len(documents)} documents, {len(chunks)} chunks")

    if args.force:
        print(_color("Forcing re-ingestion (clearing existing data)...", "yellow"))
        store.clear()

    count = store.ingest(chunks)
    print(f"  Ingested {count} chunks into ChromaDB")

    stats = store.stats()
    print(_color("\nVector Store Stats:", "bold"))
    print(f"  Total chunks:    {stats['total_chunks']}")
    print(f"  Collection:      {stats['collection_name']}")
    if stats.get("date_range"):
        print(f"  Date range:      {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    print(_color("\nIngestion complete!", "green"))


def cmd_verdict(args: argparse.Namespace) -> None:
    """Generate a verdict for a ticker."""
    from src.intelligence.wasden_watch.models import VerdictRequest
    from src.intelligence.wasden_watch.verdict_generator import VerdictGenerator

    request = VerdictRequest(
        ticker=args.ticker,
        company_name=args.company,
        sector=args.sector,
        top_k=args.top_k,
    )

    print(_color(f"Generating verdict for {args.ticker}...", "cyan"))
    generator = VerdictGenerator()
    response = generator.generate(request)

    v = response.verdict
    print(f"\n{'=' * 60}")
    print(f"  Ticker:      {response.ticker}")
    print(f"  Verdict:     {_verdict_color(v.verdict)}")
    print(f"  Confidence:  {v.confidence:.2f}")
    print(f"  Mode:        {v.mode}")
    print(f"  Model:       {response.model_used}")
    print(f"  Passages:    {v.passages_retrieved}")
    print(f"  Generated:   {response.generated_at.isoformat()}")
    print(f"{'=' * 60}")
    print(f"\n{_color('Reasoning:', 'bold')}")
    print(f"  {v.reasoning}")
    print()


def cmd_stats(args: argparse.Namespace) -> None:
    """Show vector store statistics."""
    from src.intelligence.wasden_watch.config import WasdenWatchSettings
    from src.intelligence.wasden_watch.vector_store import VectorStore

    settings = WasdenWatchSettings()
    store = VectorStore(settings)
    stats = store.stats()

    print(_color("Wasden Watch Vector Store Stats", "bold"))
    print(f"  Collection:      {stats['collection_name']}")
    print(f"  Total chunks:    {stats['total_chunks']}")
    if stats.get("date_range"):
        print(f"  Date range:      {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    else:
        print(f"  Date range:      (empty — run 'ingest' first)")

    if stats["total_chunks"] == 0:
        print(_color("\n  Vector store is empty. Run 'ingest' to populate.", "yellow"))


def cmd_search(args: argparse.Namespace) -> None:
    """Search the corpus and print top passages."""
    from src.intelligence.wasden_watch.config import WasdenWatchSettings
    from src.intelligence.wasden_watch.vector_store import VectorStore

    settings = WasdenWatchSettings()
    store = VectorStore(settings)

    if not store.is_ingested():
        print(_color("Vector store is empty. Run 'ingest' first.", "red"))
        sys.exit(1)

    print(_color(f"Searching for: '{args.query}' (top {args.top_k})", "cyan"))
    passages = store.search(args.query, top_k=args.top_k)

    if not passages:
        print("  No passages found.")
        return

    for i, p in enumerate(passages, 1):
        print(f"\n{'─' * 60}")
        print(f"  {_color(f'Passage {i}', 'bold')} | Score: {p.final_score:.4f}")
        print(f"  Source: {p.source_title} ({p.source_date})")
        print(f"  File:   {p.source_filename}")
        print(f"  Relevance: {p.relevance_score:.4f} | Time decay: {p.time_decay_weight:.4f}")
        print(f"\n  {p.text[:300]}{'...' if len(p.text) > 300 else ''}")

    print(f"\n{'─' * 60}")
    print(f"  {len(passages)} passages returned")


def cmd_pilot(args: argparse.Namespace) -> None:
    """Run verdicts for all 11 pilot tickers and print summary table."""
    from src.intelligence.wasden_watch.models import VerdictRequest
    from src.intelligence.wasden_watch.verdict_generator import VerdictGenerator

    generator = VerdictGenerator()

    print(_color("Wasden Watch Pilot Run — 11 Tickers", "bold"))
    print(f"{'=' * 70}")
    print(f"  {'Ticker':<8} {'Verdict':<10} {'Conf':>6} {'Mode':<25} {'Model'}")
    print(f"  {'─' * 8} {'─' * 10} {'─' * 6} {'─' * 25} {'─' * 20}")

    results = []
    for ticker in PILOT_TICKERS:
        try:
            request = VerdictRequest(ticker=ticker, top_k=args.top_k)
            response = generator.generate(request)
            v = response.verdict
            results.append((ticker, v.verdict, v.confidence, v.mode, response.model_used))
            verdict_display = _verdict_color(v.verdict)
            print(f"  {ticker:<8} {verdict_display:<10} {v.confidence:>6.2f} {v.mode:<25} {response.model_used}")
        except Exception as e:
            results.append((ticker, "ERROR", 0.0, str(e)[:25], "N/A"))
            print(f"  {ticker:<8} {_color('ERROR', 'red'):<10} {'N/A':>6} {str(e)[:25]:<25} N/A")

    print(f"{'=' * 70}")

    # Summary
    approvals = sum(1 for r in results if r[1] == "APPROVE")
    neutrals = sum(1 for r in results if r[1] == "NEUTRAL")
    vetoes = sum(1 for r in results if r[1] == "VETO")
    errors = sum(1 for r in results if r[1] == "ERROR")

    print(f"\n  Summary: {_color(f'{approvals} APPROVE', 'green')} | "
          f"{_color(f'{neutrals} NEUTRAL', 'yellow')} | "
          f"{_color(f'{vetoes} VETO', 'red')}"
          f"{f' | {errors} ERROR' if errors else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wasden Watch RAG Pipeline CLI",
        prog="python -m app.cli.wasden_cli",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Process PDFs and ingest into vector store")
    ingest_parser.add_argument("--force", action="store_true", help="Force re-ingestion (clear existing data)")
    ingest_parser.set_defaults(func=cmd_ingest)

    # verdict
    verdict_parser = subparsers.add_parser("verdict", help="Generate a verdict for a ticker")
    verdict_parser.add_argument("ticker", help="Stock ticker symbol (e.g., NVDA)")
    verdict_parser.add_argument("--company", default=None, help="Company name")
    verdict_parser.add_argument("--sector", default=None, help="Sector")
    verdict_parser.add_argument("--top-k", type=int, default=10, help="Number of passages to retrieve")
    verdict_parser.set_defaults(func=cmd_verdict)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show vector store statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # search
    search_parser = subparsers.add_parser("search", help="Search the corpus")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.set_defaults(func=cmd_search)

    # pilot
    pilot_parser = subparsers.add_parser("pilot", help="Run verdicts for all 11 pilot tickers")
    pilot_parser.add_argument("--top-k", type=int, default=10, help="Number of passages to retrieve per ticker")
    pilot_parser.set_defaults(func=cmd_pilot)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
