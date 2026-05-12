from pathlib import Path
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Grain Futures Intelligence Dashboard",
    page_icon="🌾",
    layout="wide",
)

COMMODITIES = {
    "Corn": "CORN",
    "Wheat": "WHEAT",
    "Soybeans": "SOYBEANS",
}

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

st.title("🌾 Grain Futures Intelligence Dashboard")
st.caption("Live commodity intelligence dashboard using Alpha Vantage, with cached fallback.")

api_key = st.secrets.get("ALPHAVANTAGE_API_KEY", "")

@st.cache_data(ttl=3600)
def fetch_alpha_vantage(function_name, api_key):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": function_name,
        "interval": "daily",
        "apikey": api_key,
    }

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    if "data" not in data:
        raise ValueError(str(data)[:300])

    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date")
    return df

def signal(change):
    if change >= 2:
        return "BUY/WATCH"
    elif change <= -2:
        return "SELL/WATCH"
    return "HOLD"

commodity = st.sidebar.selectbox("Select commodity", list(COMMODITIES.keys()))
function_name = COMMODITIES[commodity]

if not api_key:
    st.error("Missing Alpha Vantage API key. Add ALPHAVANTAGE_API_KEY in Streamlit Secrets.")
    st.stop()

try:
    df = fetch_alpha_vantage(function_name, api_key)
    df.to_csv(DATA_DIR / f"{function_name.lower()}_latest.csv", index=False)
except Exception as e:
    cached = DATA_DIR / f"{function_name.lower()}_latest.csv"
    if cached.exists():
        st.warning("Live API failed. Showing cached data.")
        df = pd.read_csv(cached, parse_dates=["date"])
    else:
        st.error(f"Could not fetch live data and no cached file exists. Error: {e}")
        st.stop()

latest = df.iloc[-1]["value"]
previous = df.iloc[-2]["value"]
daily_change = (latest - previous) / previous * 100

df["MA20"] = df["value"].rolling(20).mean()
df["MA60"] = df["value"].rolling(60).mean()
df["month"] = df["date"].dt.month_name()

forecast_days = 30
recent_trend = df["value"].tail(30).diff().mean()
future_dates = pd.bdate_range(df["date"].max(), periods=forecast_days + 1)[1:]
forecast = pd.DataFrame({
    "date": future_dates,
    "forecast": [latest + recent_trend * i for i in range(1, forecast_days + 1)]
})

forecast_30d = forecast.iloc[-1]["forecast"]
forecast_change = (forecast_30d - latest) / latest * 100
trade_signal = signal(forecast_change)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Commodity", commodity)
m2.metric("Latest price/index", f"{latest:.2f}", f"{daily_change:.2f}%")
m3.metric("30D forecast", f"{forecast_30d:.2f}", f"{forecast_change:.2f}%")
m4.metric("Signal", trade_signal)

st.subheader("Market Overview")
fig = px.line(df.tail(365), x="date", y=["value", "MA20", "MA60"], title=f"{commodity} Trend: Price + 20D/60D Moving Averages")
st.plotly_chart(fig, use_container_width=True)

st.subheader("30 Business Day Forecast")
fc_fig = px.line(forecast, x="date", y="forecast", title=f"{commodity} Forecast")
st.plotly_chart(fc_fig, use_container_width=True)

st.subheader("Seasonality Layer")
seasonality = df.groupby("month")["value"].mean().reset_index()
seasonality["month"] = pd.Categorical(
    seasonality["month"],
    categories=[
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ],
    ordered=True
)
seasonality = seasonality.sort_values("month")
season_fig = px.bar(seasonality, x="month", y="value", title=f"{commodity} Average Monthly Seasonality")
st.plotly_chart(season_fig, use_container_width=True)

st.subheader("Trading Desk Interpretation")
if trade_signal == "BUY/WATCH":
    st.success("Forecast indicates upward pressure. Review long exposure, procurement timing, and hedge coverage.")
elif trade_signal == "SELL/WATCH":
    st.error("Forecast indicates downward pressure. Review short exposure, inventory risk, and hedge strategy.")
else:
    st.info("Forecast movement is within normal threshold. Current signal is HOLD.")

st.subheader("Raw Data")
st.dataframe(df.tail(100), use_container_width=True)

st.warning("This is decision-support analytics only. It is not financial advice and does not execute trades.")
