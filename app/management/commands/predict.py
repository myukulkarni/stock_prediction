from django.core.management.base import BaseCommand, CommandError
from app.utils import predict_stock_price
import json

class Command(BaseCommand):
    help = "Predict stock price using LSTM model"

    def add_arguments(self, parser):
        parser.add_argument('--ticker', type=str, help='Stock ticker symbol (e.g., TSLA)')
        parser.add_argument('--all', action='store_true', help='Run prediction for all tickers')

    def handle(self, *args, **options):
        if options['ticker']:
            ticker = options['ticker']
            try:
                result = predict_stock_price(ticker)
                self.stdout.write(self.style.SUCCESS(json.dumps(result, indent=2)))
            except Exception as e:
                raise CommandError(f"Failed to predict for {ticker}: {e}")

        elif options['all']:
            tickers = ['AAPL', 'TSLA', 'GOOGL']  # 🔁 Add more tickers if needed
            for ticker in tickers:
                try:
                    result = predict_stock_price(ticker)
                    self.stdout.write(self.style.SUCCESS(f"Prediction for {ticker}:\n{json.dumps(result, indent=2)}"))
                except Exception as e:
                    self.stderr.write(f"Error predicting for {ticker}: {e}")
        else:
            raise CommandError("Please provide either --ticker or --all")
