from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

from config import COMMODITIES, DEFAULT_PERIOD, DEFAULT_INTERVAL, FORECAST_DAYS, ALERT_THRESHOLD_PCT, MIN_HISTORY_DAYS
from scripts.modeling import fit_forecast, trend_seasonality

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Grain Futures Intelligence Dashboard",
    page_icon="🌾",
    layout="wide",
)

st.sidebar.title("🌾 Grain Desk Controls")
period = st.sidebar.selectbox("Yahoo Finance history window", ["1y", "2y", "5y", "10y", "max"], index=2)
force_refresh = st.sidebar.button("Refresh data now")
selected_names = st.sidebar.multiselect(
    "Commodities",
    list(COMMODITIES.keys()),
    default=list(COMMODITIES.keys()),
)
forecast_days = st.sidebar.slider("Forecast horizon", 5, 60, FORECAST_DAYS, 5)
threshold = st.sidebar.slider("Alert threshold ±%", 0.5, 10.0, ALERT_THRESHOLD_PCT, 0.5)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_live_prices(period: str, interval: str):
    tickers = [COMMODITIES[name] for name in COMMODITIES]
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
        raise RuntimeError("Yahoo Finance returned no data.")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})

    close = close.reset_index()
    if "Datetime" in close.columns:
        close = close.rename(columns={"Datetime": "Date"})
    close["Date"] = pd.to_datetime(close["Date"]).dt.tz_localize(None)
    close = close.dropna(how="all", subset=tickers)
    return close

if force_refresh:
    fetch_live_prices.clear()

st.title("🌾 Grain Futures Intelligence Dashboard")
st.caption("Dynamic Yahoo Finance extraction, automated model retraining, trend/seasonality layer, verified backtest metrics, and trading-desk alerts.")

try:
    prices = fetch_live_prices(period, DEFAULT_INTERVAL)
    source_status = "Live data from Yahoo Finance via yfinance"
    prices.to_csv(DATA_DIR / "latest_prices.csv", index=False)
except Exception as exc:
    fallback = DATA_DIR / "latest_prices.csv"
    if fallback.exists():
        prices = pd.read_csv(fallback, parse_dates=["Date"])
        source_status = f"Using cached fallback data because live fetch failed: {exc}"
    else:
        st.error(f"Could not fetch live data and no cached file exists. Error: {exc}")
        st.stop()

prices = prices.sort_values("Date")
last_update = prices["Date"].max()

st.info(f"Data source: {source_status}. Latest market date in dataset: {last_update.date()}.")

price_indexed = prices.set_index("Date")

summary_rows = []
forecast_frames = []
fitted_frames = {}
trend_frames = {}
seasonal_frames = {}

for name in selected_names:
    ticker = COMMODITIES[name]
    series = price_indexed[ticker].dropna()
    if len(series) < MIN_HISTORY_DAYS:
        st.warning(f"{name} ({ticker}) has only {len(series)} observations. Forecast may be weak.")
        continue

    result = fit_forecast(series, horizon=forecast_days)
    fc = result["forecast"].copy()
    fc["Commodity"] = name
    fc["Ticker"] = ticker
    forecast_frames.append(fc)

    fitted_frames[ticker] = result["fitted"]
    trend_df, seasonal_df = trend_seasonality(series)
    trend_frames[ticker] = trend_df
    seasonal_frames[ticker] = seasonal_df

    row = {
        "Commodity": name,
        "Ticker": ticker,
        **result["summary"],
    }
    row["Alert"] = "YES" if abs(row["ForecastChangePct"]) >= threshold else "NO"
    summary_rows.append(row)

if not summary_rows:
    st.error("No commodities have enough data to model.")
    st.stop()

summary = pd.DataFrame(summary_rows)
forecast = pd.concat(forecast_frames, ignore_index=True)

summary.to_csv(DATA_DIR / "forecast_summary.csv", index=False)
forecast.to_csv(DATA_DIR / "forecast_30d.csv", index=False)

st.subheader("Market Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tracked markets", len(summary))
c2.metric("Active alerts", int((summary["Alert"] == "YES").sum()))
c3.metric("Average 30D forecast", f"{summary['ForecastChangePct'].mean():.2f}%")
c4.metric("Best backtest MAPE", f"{summary['MAPE'].min():.2f}%")

overview = summary.copy()
overview["Latest Price"] = overview["LastPrice"].map(lambda x: f"{x:.2f}")
overview["30D Forecast"] = overview["Forecast30D"].map(lambda x: f"{x:.2f}")
overview["Forecast Change"] = overview["ForecastChangePct"].map(lambda x: f"{x:.2f}%")
overview["Backtest MAPE"] = overview["MAPE"].map(lambda x: f"{x:.2f}%")
st.dataframe(
    overview[["Commodity", "Ticker", "Latest Price", "30D Forecast", "Forecast Change", "Signal", "Alert", "Backtest MAPE"]],
    use_container_width=True,
)

st.divider()

commodity_name = st.selectbox("Detailed commodity view", selected_names)
ticker = COMMODITIES[commodity_name]
row = summary[summary["Ticker"] == ticker].iloc[0]

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Ticker", ticker)
m2.metric("Latest price", f"{row['LastPrice']:.2f}")
m3.metric("Forecast end", f"{row['Forecast30D']:.2f}", f"{row['ForecastChangePct']:.2f}%")
m4.metric("Backtest MAPE", f"{row['MAPE']:.2f}%")
m5.metric("Signal", row["Signal"])

if row["Alert"] == "YES":
    if row["ForecastChangePct"] > 0:
        st.success("Alert: forecast is above the selected threshold. Review long exposure, procurement cost risk, and hedge strategy.")
    else:
        st.error("Alert: forecast is below the selected threshold. Review short exposure, inventory valuation, and hedge strategy.")
else:
    st.info("No alert triggered under the selected threshold. Signal remains decision-support only.")

st.subheader("Historical Price, Trend, and Forecast")
hist = price_indexed[[ticker]].rename(columns={ticker: "Price"}).dropna().reset_index()
fc = forecast[forecast["Ticker"] == ticker][["Date", "ForecastPrice"]].rename(columns={"ForecastPrice": "Price"})
hist["Type"] = "Historical"
fc["Type"] = "Forecast"
chart_df = pd.concat([hist.tail(520), fc], ignore_index=True)

fig = px.line(chart_df, x="Date", y="Price", color="Type", title=f"{commodity_name} ({ticker}) - Price and Forecast")
trend_df = trend_frames[ticker].tail(520)
fig.add_trace(go.Scatter(x=trend_df["Date"], y=trend_df["Trend20"], mode="lines", name="20D Trend"))
fig.add_trace(go.Scatter(x=trend_df["Date"], y=trend_df["Trend60"], mode="lines", name="60D Trend"))
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Seasonality Layer")
    seasonal = seasonal_frames[ticker]
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    seasonal["Month"] = pd.Categorical(seasonal["Month"], categories=month_order, ordered=True)
    seasonal = seasonal.sort_values("Month")
    fig_season = px.bar(
        seasonal,
        x="Month",
        y="DailyReturnPct",
        title="Average daily return by calendar month",
        labels={"DailyReturnPct": "Avg Daily Return %"},
    )
    st.plotly_chart(fig_season, use_container_width=True)

with right:
    st.subheader("Model Verification")
    fitted = fitted_frames[ticker].tail(180)
    verify = fitted.melt(id_vars="Date", value_vars=["Price", "ModelPrice"], var_name="Series", value_name="Value")
    fig_verify = px.line(verify, x="Date", y="Value", color="Series", title="Recent fitted model vs actual price")
    st.plotly_chart(fig_verify, use_container_width=True)
    st.caption("Verification uses historical backtest MAPE/MAE. It does not guarantee future accuracy.")

st.subheader("Forecast Table")
st.dataframe(forecast[forecast["Ticker"] == ticker], use_container_width=True)

st.subheader("Decision Maker Notes")
st.markdown(
    """
- **BUY/WATCH** means the model forecast is above the positive alert threshold.
- **SELL/WATCH** means the model forecast is below the negative alert threshold.
- **HOLD** means the expected move is inside the threshold.
- Review external market drivers before acting: USDA reports, weather, export demand, FX, freight, war/geopolitical risk, energy prices, and inventory levels.
- This website is an analytics and decision-support tool only. It does not execute trades and is not financial advice.
"""
)
