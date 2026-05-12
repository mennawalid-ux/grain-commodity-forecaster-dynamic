import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
import pandas as pd
from config import ALERT_THRESHOLD_PCT

ROOT = Path(__file__).resolve().parents[1]
summary_path = ROOT / "data" / "forecast_summary.csv"

def build_message(summary: pd.DataFrame) -> str:
    alert_rows = summary[summary["ForecastChangePct"].abs() >= ALERT_THRESHOLD_PCT]
    if alert_rows.empty:
        return "No grain futures crossed the alert threshold today."

    lines = ["Grain futures alert:"]
    for _, row in alert_rows.iterrows():
        lines.append(
            f"- {row['Commodity']} ({row['Ticker']}): {row['Signal']}, "
            f"30D forecast change {row['ForecastChangePct']:.2f}%, "
            f"last {row['LastPrice']:.2f}, forecast {row['Forecast30D']:.2f}, "
            f"backtest MAPE {row['MAPE']:.2f}%"
        )
    return "\n".join(lines)

def send_email(subject: str, body: str):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    if not all([user, password, receiver]):
        print(body)
        print("Email credentials not configured. Add EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECEIVER to GitHub secrets.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [receiver], msg.as_string())

if __name__ == "__main__":
    summary = pd.read_csv(summary_path)
    message = build_message(summary)
    send_email("Grain Futures Forecast Alert", message)
