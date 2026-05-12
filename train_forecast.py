from pathlib import Path
import pandas as pd
from config import COMMODITIES, FORECAST_DAYS
from scripts.modeling import fit_forecast

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

if __name__ == "__main__":
    prices = pd.read_csv(DATA_DIR / "latest_prices.csv", parse_dates=["Date"]).set_index("Date")
    all_forecasts = []
    summary_rows = []
    for name, ticker in COMMODITIES.items():
        result = fit_forecast(prices[ticker], horizon=FORECAST_DAYS)
        fc = result["forecast"]
        fc.insert(0, "Commodity", name)
        fc.insert(1, "Ticker", ticker)
        all_forecasts.append(fc)

        row = {"Commodity": name, "Ticker": ticker, **result["summary"]}
        summary_rows.append(row)

    pd.concat(all_forecasts, ignore_index=True).to_csv(DATA_DIR / "forecast_30d.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(DATA_DIR / "forecast_summary.csv", index=False)
    print("Saved forecast files.")
