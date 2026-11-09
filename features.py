import sqlite3
import numpy as np
import pandas as pd

DB = "data/quant.db"
HORIZONS = range(6)  

SENT_COLS = ["sent_mean", "sent_wmean", "balance", "sent_std", "vol_z",
             "sent_wmean_l1", "sent_wmean_l2", "sent_roll3", "sent_roll5", "sent_chg"]
PRICE_COLS = ["ret_l0", "ret_l1", "ret_l2", "ret_l4", "mom5", "vol10", "dow"]


def load_tables():
    con = sqlite3.connect(DB)
    prices = pd.read_sql("SELECT date, close, ret FROM prices", con, parse_dates=["date"])
    daily = pd.read_sql("SELECT * FROM daily_sentiment", con, parse_dates=["trading_date"])
    con.close()
    return prices.sort_values("date").reset_index(drop=True), daily


def price_features(prices):
    p = prices.copy()
    p["ret_l0"] = p["ret"]            
    p["ret_l1"] = p["ret"].shift(1)
    p["ret_l2"] = p["ret"].shift(2)
    p["ret_l4"] = p["ret"].shift(4)
    p["mom5"] = p["ret"].rolling(5).sum()
    p["vol10"] = p["ret"].rolling(10).std()
    p["dow"] = p["date"].dt.day_of_week

    for h in HORIZONS:
        p[f"y{h}"] = p["ret"].shift(-(1 + h))
    return p


def sentiment_features(daily_src):
    s = daily_src.sort_values("trading_date").rename(columns={"trading_date": "date"}).copy()
    ln = np.log1p(s["n_tweets"])
    s["vol_z"] = (ln - ln.rolling(20).mean()) / ln.rolling(20).std()
    s["sent_wmean_l1"] = s["sent_wmean"].shift(1)
    s["sent_wmean_l2"] = s["sent_wmean"].shift(2)
    s["sent_roll3"] = s["sent_wmean"].rolling(3).mean()
    s["sent_roll5"] = s["sent_wmean"].rolling(5).mean()
    s["sent_chg"] = s["sent_wmean"] - s["sent_roll5"]
    return s[["date"] + SENT_COLS]


def build(source):
    prices, daily = load_tables()
    p = price_features(prices)
    s = sentiment_features(daily[daily["source"] == source])
    df = p.merge(s, on="date", how="inner")
    return df.replace([np.inf, -np.inf], np.nan)


if __name__ == "__main__":
    for src in ["kaggle", "live"]:
        d = build(src)
        print(src, d.shape, d["date"].min().date(), d["date"].max().date())
        print(d[SENT_COLS + PRICE_COLS].describe().T[["count", "mean", "std"]].round(4))