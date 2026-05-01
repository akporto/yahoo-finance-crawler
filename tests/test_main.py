import pytest
from unittest.mock import patch
from dataclasses import asdict

from crawler.models import StockData
from crawler.main import export_to_csv, main


SAMPLE_STOCK = StockData(symbol="AMX.BA", name="América Móvil", price=2089.0)


class TestExportToCsv:

    def test_writes_correct_headers_and_rows(self, tmp_path):
        output = tmp_path / "out.csv"
        export_to_csv([asdict(SAMPLE_STOCK)], str(output))

        lines = output.read_text(encoding="utf-8").splitlines()
        assert lines[0] == '"symbol","name","price"'
        assert lines[1] == '"AMX.BA","América Móvil","2089.00"'

    def test_price_is_formatted_with_two_decimals(self, tmp_path):
        output = tmp_path / "out.csv"
        export_to_csv([asdict(StockData(symbol="X", name="X Corp", price=100))], str(output))

        lines = output.read_text(encoding="utf-8").splitlines()
        assert lines[1] == '"X","X Corp","100.00"'

    def test_all_values_are_quoted(self, tmp_path):
        output = tmp_path / "out.csv"
        export_to_csv([asdict(StockData(symbol="ABC", name="ABC Inc", price=1.5))], str(output))

        lines = output.read_text(encoding="utf-8").splitlines()
        for value in ("ABC", "ABC Inc", "1.50"):
            assert f'"{value}"' in lines[1]

    def test_does_not_create_file_when_data_is_empty(self, tmp_path):
        output = tmp_path / "out.csv"
        export_to_csv([], str(output))
        assert not output.exists()

    def test_exits_on_write_error(self):
        with patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(SystemExit):
                export_to_csv([asdict(SAMPLE_STOCK)], "/invalid/path.csv")


class TestMain:

    def _run_main(self, args, fetch_records=None, parse_result=SAMPLE_STOCK):
        fetch_records = fetch_records or [asdict(SAMPLE_STOCK)]
        with patch("sys.argv", ["main"] + args), \
             patch("crawler.main.YahooSession"), \
             patch("crawler.main.YahooFinanceScreenerClient") as mock_client_cls, \
             patch("crawler.main.YahooFinanceParser.parse", return_value=parse_result), \
             patch("crawler.main.export_to_csv") as mock_export:
            mock_client_cls.return_value.fetch_all.return_value = iter(fetch_records)
            main()
            return mock_export

    def test_successful_pipeline_calls_export(self):
        mock_export = self._run_main(["--region", "Argentina"])
        mock_export.assert_called_once()

    def test_output_flag_is_passed_to_export(self):
        mock_export = self._run_main(["--region", "ar", "--output", "custom.csv"])
        _, filename = mock_export.call_args[0]
        assert filename == "custom.csv"

    def test_exits_on_unknown_region(self):
        with patch("sys.argv", ["main", "--region", "Narnia"]):
            with pytest.raises(SystemExit):
                main()

    def test_exits_when_no_valid_records_extracted(self):
        with patch("sys.argv", ["main", "--region", "ar"]), \
             patch("crawler.main.YahooSession"), \
             patch("crawler.main.YahooFinanceScreenerClient") as mock_client_cls, \
             patch("crawler.main.YahooFinanceParser.parse", return_value=None):
            mock_client_cls.return_value.fetch_all.return_value = iter([{"symbol": "X"}])
            with pytest.raises(SystemExit):
                main()

    def test_exits_on_client_exception(self):
        with patch("sys.argv", ["main", "--region", "ar"]), \
             patch("crawler.main.YahooSession"), \
             patch("crawler.main.YahooFinanceScreenerClient") as mock_client_cls:
            mock_client_cls.return_value.fetch_all.side_effect = RuntimeError("API down")
            with pytest.raises(SystemExit):
                main()
