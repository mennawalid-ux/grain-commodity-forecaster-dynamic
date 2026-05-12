import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error

FEATURE_COLS = [
    "t",
    "lag_1",
    "lag_5",
    "lag_20",
    "roll_5",
    "roll_20",
    "roll_60",
    "return_1",
    "return_5",
    "sin_doy",
    "cos_doy",
    "sin_month",
    "cos_month",
]

def make_features(series: pd.Series) -> pd.DataFrame:
    s = series.dropna().copy()
    df = pd.DataFrame({"Date": s.index, "Price": s.values})
    df["t"] = np.arange(len(df))
    df["lag_1"] = df["Price"].shift(1)
    df["lag_5"] = df["Price"].shift(5)
    df["lag_20"] = df["Price"].shift(20)
    df["roll_5"] = df["Price"].shift(1).rolling(5).mean()
    df["roll_20"] = df["Price"].shift(1).rolling(20).mean()
    df["roll_60"] = df["Price"].shift(1).rolling(60).mean()
    df["return_1"] = df["Price"].pct_change(1).shift(1)
    df["return_5"] = df["Price"].pct_change(5).shift(1)
    doy = pd.to_datetime(df["Date"]).dt.dayofyear
    month = pd.to_datetime(df["Date"]).dt.month
    df["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    df["sin_month"] = np.sin(2 * np.pi * month / 12)
    df["cos_month"] = np.cos(2 * np.pi * month / 12)
    return df.dropna().reset_index(drop=True)

def fit_forecast(series: pd.Series, horizon: int = 30):
    feature_df = make_features(series)
    if len(feature_df) < 120:
        raise ValueError("Not enough history after feature engineering.")

    split = max(int(len(feature_df) * 0.8), len(feature_df) - 90)
    train = feature_df.iloc[:split]
    test = feature_df.iloc[split:]

    model = Ridge(alpha=5.0)
    model.fit(train[FEATURE_COLS], train["Price"])

    test_pred = model.predict(test[FEATURE_COLS])
    mape = float(mean_absolute_percentage_error(test["Price"], test_pred) * 100)
    mae = float(mean_absolute_error(test["Price"], test_pred))

    full_model = Ridge(alpha=5.0)
    full_model.fit(feature_df[FEATURE_COLS], feature_df["Price"])

    future_rows = []
    work = series.dropna().copy()
    last_date = pd.to_datetime(work.index[-1])
    for step in range(1, horizon + 1):
        next_date = last_date + pd.tseries.offsets.BDay(step)
        temp = pd.concat([work, pd.Series([np.nan], index=[next_date])])
        temp_features = make_features(temp.ffill())
        row = temp_features.iloc[-1:].copy()
        pred = float(full_model.predict(row[FEATURE_COLS])[0])
        pred = max(pred, 0.01)
        work.loc[next_date] = pred
        future_rows.append({"Date": next_date, "ForecastPrice": pred, "Step": step})

    forecast = pd.DataFrame(future_rows)
    last_price = float(series.dropna().iloc[-1])
    forecast_30d = float(forecast["ForecastPrice"].iloc[-1])
    change_pct = (forecast_30d / last_price - 1) * 100

    if change_pct >= 2:
        signal = "BUY/WATCH"
    elif change_pct <= -2:
        signal = "SELL/WATCH"
    else:
        signal = "HOLD"

    fitted = feature_df[["Date", "Price"]].copy()
    fitted["ModelPrice"] = full_model.predict(feature_df[FEATURE_COLS])

    return {
        "forecast": forecast,
        "fitted": fitted,
        "summary": {
            "LastPrice": last_price,
            "Forecast30D": forecast_30d,
            "ForecastChangePct": float(change_pct),
            "MAPE": mape,
            "MAE": mae,
            "Signal": signal,
        },
    }

def trend_seasonality(series: pd.Series):
    s = series.dropna().copy()
    df = pd.DataFrame({"Date": s.index, "Price": s.values})
    df["Trend20"] = df["Price"].rolling(20).mean()
    df["Trend60"] = df["Price"].rolling(60).mean()
    df["DailyReturnPct"] = df["Price"].pct_change() * 100
    seasonal = df.copy()
    seasonal["Month"] = pd.to_datetime(seasonal["Date"]).dt.month_name()
    seasonal = seasonal.groupby("Month", sort=False)["DailyReturnPct"].mean().reset_index()
    return df, seasonal
