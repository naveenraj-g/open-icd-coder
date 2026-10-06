"""Terminology import CLI.

Usage examples (run from backend/):
  uv run python -m app.terminology.import_.cli --source icd10cm \\
      --file ../data/icd10cm-code-descriptions-2027.zip \\
      --tabular-file ../data/icd10cm-table-and-index-2027.zip

  # Embed the loaded release with the model in configs/config.yaml (resumable)
  uv run python -m app.terminology.import_.cli --source embeddings [--limit 2000]

Re-running icd10cm for the same release replaces that release's concepts
(and, via cascade, their embeddings).
"""

import argparse
import asyncio
import sys
import time


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Terminology Import CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--source",
        required=True,
        choices=["icd10cm", "icd10cm-index", "embeddings"],
        help=(
            "icd10cm = load the code set; icd10cm-index = load Alphabetic Index "
            "terms into a loaded release; embeddings = embed a loaded release"
        ),
    )
    p.add_argument(
        "--file",
        help=(
            "[icd10cm] Code descriptions zip, or the extracted icd10cm-order-YYYY.txt · "
            "[icd10cm-index] Table-and-index zip, or the extracted icd10cm-index-YYYY.xml"
        ),
    )
    p.add_argument(
        "--tabular-file",
        help="[icd10cm] Table-and-index zip, or the extracted icd10cm-tabular-YYYY.xml (optional — adds synonyms + notes)",
    )
    p.add_argument(
        "--version",
        help="Release year, e.g. 2027 (icd10cm default: detected from the file name; embeddings default: latest loaded)",
    )
    p.add_argument(
        "--target",
        choices=["concepts", "index-terms", "all"],
        default="all",
        help="[embeddings] What to embed (default: all)",
    )
    p.add_argument(
        "--limit",
        type=int,
        help="[embeddings] Embed at most N rows per target this run (for trying it out)",
    )
    return p


async def run(args: argparse.Namespace) -> None:
    from app.core.config import settings

    if args.source == "icd10cm":
        if not args.file:
            raise ValueError("--source icd10cm requires --file")
        from app.terminology.import_.loaders.icd10cm import Icd10cmLoader

        async with Icd10cmLoader(settings.DATABASE_URL) as loader:
            await loader.load(args.file, args.tabular_file, args.version)

    elif args.source == "icd10cm-index":
        if not args.file:
            raise ValueError("--source icd10cm-index requires --file")
        from app.terminology.import_.loaders.icd10cm_index import Icd10cmIndexLoader

        async with Icd10cmIndexLoader(settings.DATABASE_URL) as loader:
            await loader.load(args.file, args.version, settings.terminology.index_holdout_percent)

    elif args.source == "embeddings":
        from app.core.embeddings import EmbeddingClient
        from app.terminology.icd10cm import ICD10CM_URL
        from app.terminology.import_.loaders.embeddings import EmbeddingLoader

        targets = ["concepts", "index-terms"] if args.target == "all" else [args.target]
        client = EmbeddingClient(settings.embedding, settings.EMBEDDING_API_KEY)
        try:
            async with EmbeddingLoader(settings.DATABASE_URL, client) as loader:
                await loader.load(ICD10CM_URL, args.version, targets, args.limit)
        finally:
            await client.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    t0 = time.monotonic()
    from app.errors.base import ApplicationError

    try:
        asyncio.run(run(args))
    except (FileNotFoundError, ValueError, ApplicationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted — progress so far is saved; re-run to continue.", file=sys.stderr)
        sys.exit(130)
    print(f"\nTotal elapsed: {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
