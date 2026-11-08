import yfinance as yf
import os
import numpy as np

def get_prices(ticker, start, end):
    df = yf.download(ticker, start, end, interval="1d")
    df.columns = df.columns.get_level_values(0) + "_" + df.columns.get_level_values(1)
    df["return_log"] = np.log(df[f"Close_{ticker}"]/df[f"Close_{ticker}"].shift(1))
    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/{ticker}_prices.csv", index=True)
    return df

if __name__ == "__main__":
    get_prices("TSLA", start="2015-01-01", end="2026-11-10")