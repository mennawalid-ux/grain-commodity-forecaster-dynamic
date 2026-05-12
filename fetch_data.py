from pathlib import Path
import pandas as pd
import yfinance as yf
from config import COMMODITIES, DEFAULT_PERIOD, DEFAULT_INTERVAL

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

def fetch_prices(period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL):
    tickers = list(COMMODITIES.values())
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no data. Try again later or check ticker availability.")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})

    close = close.reset_index()
    if "Datetime" in close.columns:
        close = close.rename(columns={"Datetime": "Date"})
    close["Date"] = pd.to_datetime(close["Date"]).dt.tz_localize(None)
    close = close.dropna(how="all", subset=tickers)
    close.to_csv(DATA_DIR / "latest_prices.csv", index=False)
    return close

if __name__ == "__main__":
    df = fetch_prices()
    print(f"Saved {len(df)} rows to data/latest_prices.csv")
