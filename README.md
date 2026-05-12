# Grain Futures Intelligence Dashboard

Dynamic Streamlit website for grain commodity analytics and forecasting.

## Commodities

- Corn Futures: `ZC=F`
- Wheat Futures: `ZW=F`
- Soybean Futures: `ZS=F`

## What it does

- Extracts live daily prices from Yahoo Finance using `yfinance`
- Refreshes data inside the Streamlit app
- Builds a new forecasting model when data refreshes
- Adds trend indicators: 20-day and 60-day moving trends
- Adds seasonality layer: average daily return by month
- Verifies model performance with historical backtest MAPE and MAE
- Generates decision-support signals: BUY/WATCH, SELL/WATCH, HOLD
- Includes GitHub Actions for daily automated data/forecast updates
- Includes optional email alert script

## Deploy on Streamlit Cloud

1. Upload all files and folders to GitHub.
2. Go to Streamlit Cloud.
3. Create a new app.
4. Select your repository.
5. Main file path: `app.py`
6. Advanced settings: select Python `3.11`
7. Deploy.

## Important GitHub structure

Keep the folders as folders:

```text
app.py
config.py
requirements.txt
runtime.txt
data/
scripts/
.github/workflows/
.streamlit/
README.md
```

Do not upload only the contents of `data` or `scripts` into the root if you want GitHub Actions to work cleanly.

## Alerts

Add these GitHub Secrets if you want email alerts:

```text
EMAIL_USER
EMAIL_PASSWORD
EMAIL_RECEIVER
```

## Notes

Yahoo Finance data through yfinance is useful for analytics and prototypes. For institutional trading production, validate against an approved market data provider.
