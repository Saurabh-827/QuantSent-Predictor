import os
import json
import sqlite3
import numpy as np
import pandas as pd

DB = "data/quant.db"


def assign_trading_date(ts_utc, trading_days):
    """Map each tweet to the first trading session whose close it precedes."""
    et = ts_utc.dt.tz_convert("America/New_York")
    cand = et.dt.normalize().dt.tz_localize(None)
    after_close = (et.dt.hour >= 16).astype(int)
    cand = cand + pd.to_timedelta(after_close, unit="D")

    idx = np.asarray(trading_days.searchsorted(pd.DatetimeIndex(cand)))
    valid = idx < len(trading_days)
    picked = trading_days[np.minimum(idx, len(trading_days) - 1)].to_numpy()
    return pd.Series(picked, index=ts_utc.index).where(valid)


def daily_agg(df):
    df = df.copy()
    df["w"] = 1 + np.log1p(df["likes"] + df["retweets"] + df["replies"])
    df["ws"] = df["sentiment"] * df["w"]
    df["pos"] = (df["sentiment"] > 0.05).astype(int)
    df["neg"] = (df["sentiment"] < -0.05).astype(int)
    g = df.groupby("trading_date")
    out = pd.DataFrame({
        "n_tweets": g.size(),
        "sent_mean": g["sentiment"].mean(),
        "sent_std": g["sentiment"].std(),
        "pos_share": g["pos"].mean(),
        "neg_share": g["neg"].mean(),
        "sent_wmean": g["ws"].sum() / g["w"].sum(),
    })
    out["balance"] = out["pos_share"] - out["neg_share"]
    out["source"] = df["source"].iloc[0]
    return out.reset_index()


def main():
    prices = pd.read_csv("data/TSLA_prices.csv", parse_dates=["Date"])
    prices = prices.rename(columns={"Date": "date", "Close_TSLA": "close", "return_log": "ret"})
    prices = prices[["date", "close", "ret"]]
    trading_days = pd.DatetimeIndex(prices["date"]).sort_values()

    frames = []
    for source in ["kaggle", "live"]:
        df = pd.read_csv(f"data/{source}_scored.csv")
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df["trading_date"] = assign_trading_date(df["ts"], trading_days)
        before = len(df)
        df = df.dropna(subset=["trading_date"])
        print(f"{source}: {len(df)} tweets assigned ({before - len(df)} dropped, outside price range)")
        frames.append(df)

    tweets = pd.concat(frames, ignore_index=True)
    daily = pd.concat([daily_agg(f) for f in frames], ignore_index=True)

    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB)
    prices.assign(date=prices["date"].dt.strftime("%Y-%m-%d")).to_sql(
        "prices", con, if_exists="replace", index=False)
    daily.assign(trading_date=daily["trading_date"].dt.strftime("%Y-%m-%d")).to_sql(
        "daily_sentiment", con, if_exists="replace", index=False)
    tweets.assign(
        ts=tweets["ts"].astype(str),
        trading_date=tweets["trading_date"].dt.strftime("%Y-%m-%d"),
    ).to_sql("tweets", con, if_exists="replace", index=False, chunksize=100_000)

    if os.path.exists("data/tsla_news.json"):
        with open("data/tsla_news.json", encoding="utf-8") as f:
            news = pd.DataFrame(json.load(f)["results"])
        keep = [c for c in ["title", "url", "published_date", "content", "score"] if c in news.columns]
        news[keep].to_sql("news", con, if_exists="replace", index=False)

    check = pd.read_sql("""
        SELECT s.source,
               COUNT(*) AS days,
               MIN(p.date) AS first_day,
               MAX(p.date) AS last_day,
               ROUND(AVG(s.n_tweets), 1) AS avg_tweets,
               ROUND(AVG(s.sent_mean), 3) AS avg_sent
        FROM prices p JOIN daily_sentiment s ON s.trading_date = p.date
        GROUP BY s.source
    """, con)
    print(check.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()