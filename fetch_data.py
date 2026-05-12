from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

COMMODITIES = {
    "Corn Futures": "zc.f",
    "Wheat Futures": "zw.f",
    "Soybean Futures": "zs.f",
}

def fetch_stooq(symbol):
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    return df

for name, symbol in COMMODITIES.items():
    try:
        df = fetch_stooq(symbol)

        filename = DATA_DIR / f"{symbol.replace('.', '_')}.csv"

        df.to_csv(filename, index=False)

        print(f"Saved {name}")

    except Exception as e:
        print(f"Failed {name}: {e}")
