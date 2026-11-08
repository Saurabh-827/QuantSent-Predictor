import os
import re
import json
import pandas as pd
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

ACTOR = "xquik/x-tweet-scraper"
RAW_DIR = "data/raw"
PRICE_PER_TWEET = 0.00015


def _get_items(query, max_items):
    """Returns (items, from_cache). Cache key includes max_items."""
    os.makedirs(RAW_DIR, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9]+", "_", query)
    path = f"{RAW_DIR}/{name}_{max_items}.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f), True

    client = ApifyClient(os.getenv("APIFY_TOKEN"))
    run_input = {
        "searchTerms": [query],
        "maxItems": max_items,
        "lang": "en",
        "queryType": "Latest",
    }
    run = client.actor(ACTOR).call(run_input=run_input, logger=None)
    items = list(client.dataset(run.default_dataset_id).iterate_items())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    return items, False


def _parse(items):
    rows = []
    for it in items:
        author = it.get("author") or {}
        rows.append({
            "id": it.get("id"),
            "createdAt": it.get("createdAt"),
            "text": it.get("text"),
            "likeCount": it.get("likeCount", 0),
            "retweetCount": it.get("retweetCount", 0),
            "replyCount": it.get("replyCount", 0),
            "viewCount": it.get("viewCount", 0),
            "authorFollowers": author.get("followers", it.get("authorFollowers", 0)),
            "authorUsername": author.get("username", it.get("authorUsername", "")),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["createdAt"] = pd.to_datetime(
        df["createdAt"], format="%a %b %d %H:%M:%S %z %Y", errors="coerce"
    )
    return df.drop_duplicates(subset="id").sort_values("createdAt")


def fetch_range(start, end, ticker="$TSLA", max_items=100,
                budget_usd=3.0, out="data/tsla_live_tweets.csv"):
    spent, frames = 0.0, []
    for day in pd.date_range(start, end):
        nxt = day + pd.Timedelta(days=1)
        query = f"{ticker} since:{day:%Y-%m-%d} until:{nxt:%Y-%m-%d}"
        try:
            items, cached = _get_items(query, max_items)
        except Exception as e:
            print(f"{day:%Y-%m-%d} FAILED: {e}", flush=True)
            continue
        if not cached:
            spent += len(items) * PRICE_PER_TWEET
        frames.append(_parse(items))
        print(f"{day:%Y-%m-%d} rows={len(items)} cached={cached} spent=${spent:.3f}", flush=True)
        if spent >= budget_usd:
            print("Budget reached, stopping.", flush=True)
            break

    frames = [f for f in frames if not f.empty]
    if not frames:
        print("No data fetched.")
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="id").sort_values("createdAt")
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} tweets -> {out}")
    print("NaT dates:", df["createdAt"].isna().sum())
    print("Range:", df["createdAt"].min(), "->", df["createdAt"].max())
    return df


if __name__ == "__main__":
    # fetch_range("2026-11-03", "2026-11-05")
    fetch_range("2026-05-11", "2026-11-07")