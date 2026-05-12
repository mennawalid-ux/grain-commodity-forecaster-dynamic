import requests
import pandas as pd
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent

API_KEY = st.secrets["ALPHAVANTAGE_API_KEY"]

TICKERS = {
    "Corn": "CORN",
    "Wheat": "WHEAT",
    "Soybeans": "SOYBEAN"
}

def fetch_commodity(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=COMMODITY_EXCHANGE_RATE"
        f"&from_symbol={symbol}"
        f"&to_symbol=USD"
        f"&apikey={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if "Realtime Currency Exchange Rate" not in data:
        raise ValueError(f"No data returned for {symbol}")

    price = float(
        data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
    )

    return price

rows = []

for name, symbol in TICKERS.items():
    try:
        price = fetch_commodity(symbol)

        rows.append({
            "Commodity": name,
            "Price": price
        })

    except Exception as e:
        print(e)

df = pd.DataFrame(rows)

df.to_csv(ROOT / "latest_prices.csv", index=False)

print(df)
