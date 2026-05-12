from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Grain Futures Intelligence Dashboard", page_icon="🌾", layout="wide")

COMMODITIES = {
    "Corn Futures": "zc.f",
    "Wheat Futures": "zw.f",
    "Soybean Futures": "zs.f",
}

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

st.title("🌾 Grain Futures Intelligence Dashboard")
st.caption("Live futures dashboard using Stooq free futures data, with cached fallback.")

def fetch_stooq(symbol):
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)
    if df.empty or "Close" not in df.columns:
        raise ValueError("Stooq returned no usable data")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["Close"]).sort_values("Date")
    return df

def get_data(symbol):
    cache_file = DATA_DIR / f"{symbol.replace('.', '_')}.csv"
    try:
        df = fetch_stooq(symbol)
        df.to_csv(cache_file, index=False)
        return df, "Live Stooq"
    except Exception as e:
        if cache_file.exists():
            return pd.read_csv(cache_file, parse_dates=["Date"]), "Cached fallback"
        raise RuntimeError(f"Could not fetch live data and no cache exists. Error: {e}")

def signal(change_pct):
    if change_pct >= 2:
        return "BUY/WATCH"
    if change_pct <= -2:
        return "SELL/WATCH"
    return "HOLD"

commodity = st.sidebar.selectbox("Select commodity", list(COMMODITIES.keys()))
symbol = COMMODITIES[commodity]

try:
    df, source = get_data(symbol)
except Exception as e:
    st.error(str(e))
    st.stop()

df["MA20"] = df["Close"].rolling(20).mean()
df["MA60"] = df["Close"].rolling(60).mean()

latest = df["Close"].iloc[-1]
previous = df["Close"].iloc[-2]
daily_change = (latest - previous) / previous * 100

recent_trend = df["Close"].tail(30).diff().mean()
future_dates = pd.bdate_range(df["Date"].max(), periods=31)[1:]
forecast = pd.DataFrame({
    "Date": future_dates,
    "Forecast": [latest + recent_trend * i for i in range(1, 31)]
})

forecast_30d = forecast["Forecast"].iloc[-1]
forecast_change = (forecast_30d - latest) / latest * 100
trade_signal = signal(forecast_change)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Commodity", commodity)
m2.metric("Source symbol", symbol.upper())
m3.metric("Latest futures price", f"{latest:.2f}", f"{daily_change:.2f}%")
m4.metric("30D forecast", f"{forecast_30d:.2f}", f"{forecast_change:.2f}%")
m5.metric("Signal", trade_signal)

st.caption(f"Data source: {source}")

st.subheader("Market Overview")
fig = px.line(df.tail(365), x="Date", y=["Close", "MA20", "MA60"],
              title=f"{commodity} — Close Price + 20D/60D Moving Averages")
st.plotly_chart(fig, use_container_width=True)

st.subheader("30 Business Day Forecast")
st.plotly_chart(px.line(forecast, x="Date", y="Forecast"), use_container_width=True)

st.subheader("Seasonality Layer")
season_df = df.copy()
season_df["Month"] = season_df["Date"].dt.month_name()
seasonality = season_df.groupby("Month")["Close"].mean().reset_index()
month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
seasonality["Month"] = pd.Categorical(seasonality["Month"], categories=month_order, ordered=True)
seasonality = seasonality.sort_values("Month")
st.plotly_chart(px.bar(seasonality, x="Month", y="Close"), use_container_width=True)

st.subheader("Latest Raw Data")
st.dataframe(df.tail(100), use_container_width=True)

st.warning("Decision-support analytics only. Not financial advice.")
