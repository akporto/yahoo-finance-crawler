import argparse
import csv
import logging
import sys
from dataclasses import asdict

from crawler.client import YahooFinanceScreenerClient, resolve_region_code
from crawler.parser import YahooFinanceParser
from crawler.session import YahooSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_CSV_FIELDS = ["symbol", "name", "price", "change", "change_percent"]


def export_to_csv(data: list[dict], filename: str) -> None:
    if not data:
        logger.warning("No data to export.")
        return

    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=_CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Exported {len(data)} records to '{filename}'.")
    except OSError as e:
        logger.error(f"Failed to write CSV: {e}")
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Yahoo Finance Equity Screener — fetches all stocks for a region and exports to CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m crawler.main --region Argentina\n"
            "  python -m crawler.main --region Brazil --output br_stocks.csv\n"
            "  python -m crawler.main --region us\n"
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Region name or ISO code. E.g.: 'Argentina', 'Brazil', 'ar', 'br'.",
    )
    parser.add_argument(
        "--output",
        default="market_data.csv",
        help="Output CSV filename (default: market_data.csv).",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    try:
        region_code = resolve_region_code(args.region)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Starting pipeline for region '{args.region}' (code: '{region_code}')")

    client = YahooFinanceScreenerClient(session=YahooSession())
    results: list[dict] = []
    skipped = 0

    try:
        for raw_record in client.fetch_all(region_code=region_code):
            stock = YahooFinanceParser.parse(raw_record)
            if stock:
                results.append(asdict(stock))
            else:
                skipped += 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    logger.info(f"Extraction complete: {len(results)} valid, {skipped} skipped.")

    if not results:
        logger.warning("No valid data extracted.")
        sys.exit(1)

    export_to_csv(results, args.output)
    logger.info("Pipeline finished successfully.")


if __name__ == "__main__":
    main()
