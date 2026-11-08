import sys
import os
import time
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()
analyzer.lexicon.update({
    "bullish": 2.5, "bearish": -2.5, "moon": 2.0, "rally": 1.5,
    "surge": 1.5, "soar": 2.0, "plunge": -2.5, "crash": -2.5,
    "dump": -2.0, "selloff": -2.0, "rekt": -2.5,
    "overvalued": -1.5, "undervalued": 1.5,
})

COLS = ["ts", "likes", "retweets", "replies", "sentiment", "source"]


def score_texts(texts):
    return [analyzer.polarity_scores(str(t))["compound"] for t in texts]


def load_kaggle():
    df = pd.read_csv("data/TSLA_tweets.csv")
    df = df.rename(columns={
        "post_date": "ts", "body": "text", "like_num": "likes",
        "retweet_num": "retweets", "comment_num": "replies",
    })
    df["source"] = "kaggle"
    return df


def load_live():
    df = pd.read_csv("data/tsla_live_tweets.csv")
    df = df.rename(columns={
        "createdAt": "ts", "likeCount": "likes",
        "retweetCount": "retweets", "replyCount": "replies",
    })
    df["source"] = "live"
    return df


def run(source, limit=None):
    out_path = f"data/{source}_scored.csv"
    if limit is None and os.path.exists(out_path):
        print(f"{source}: cached -> {out_path}")
        return

    df = load_kaggle() if source == "kaggle" else load_live()
    if limit:
        df = df.head(limit)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df[["likes", "retweets", "replies"]] = df[["likes", "retweets", "replies"]].fillna(0)

    t0 = time.time()
    df["sentiment"] = score_texts(df["text"])
    print(f"{source}: scored {len(df)} rows in {time.time() - t0:.1f}s")

    if limit:
        print(df[["text", "sentiment"]].head(10).to_string())
        print(df["sentiment"].describe())
        return
    df[COLS].to_csv(out_path, index=False)
    print(f"saved -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run("kaggle", limit=10_000)
    else:
        run("live")
        run("kaggle")