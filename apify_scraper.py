import os
import json
import pandas as pd
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

def fetch_tweets(query, max_items=50):
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        raise ValueError("Apify token not found in .env")
    
    client = ApifyClient(apify_token)

    os.makedirs("data/raw", exist_ok=True)

    safe_query_name = query.replace(":", "_").replace(" ","_").replace("$","_")
    raw_filepath = f"data/raw/{safe_query_name}.json"

    if os.path.exists(raw_filepath):
        print(f"Already fetched, Reading from cache: {raw_filepath}")
        with open(raw_filepath, "r", encoding="utf-8") as f:
            items = json.load(f)
            
    else:
        run_input = {
            "searchTerms": [query],
            "maxItems": max_items,
            "lang": "en",
            "queryType": "Latest",
        }
        
        run = client.actor("xquik/x-tweet-scraper").call(run_input=run_input)
        
        items = []
        for item in client.dataset(run.default_dataset_id).iterate_items():
            items.append(item)
            
        with open(raw_filepath, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(items)} raw tweets to {raw_filepath}")

    parsed_data = []
    for item in items:
        parsed_data.append({
            "id": item.get("id"),
            "createdAt": item.get("createdAt"),
            "text": item.get("text"),
            "likeCount": item.get("likeCount", 0),
            "retweetCount": item.get("retweetCount", 0),
            "viewCount": item.get("viewCount", 0),
            "authorFollowers": item.get("author", {}).get("followers", 0),
            "authorUsername": item.get("author", {}).get("username", "")
        })

    df = pd.DataFrame(parsed_data)
    if df.empty:
        print("Warning: DataFrame is empty. No tweets fetched.")
        return df

    df["createdAt"] = pd.to_datetime(df["createdAt"], format="%a %b %d %H:%M:%S %z %Y")
    df = df.sort_values("createdAt")
        
    initial_count = len(df)
    df = df.drop_duplicates(subset=["id"])
    print(f"Dropped {initial_count - len(df)} duplicates based on 'id'.")
    
    return df

if __name__ == "__main__":
    test_query = "$TSLA since:2026-10-26 until:2026-11-02"
    df = fetch_tweets(test_query, max_items=50)
    
    if not df.empty:
        print("\n--- TEST RESULTS ---")
        print(f"Total rows (after deduplication): {len(df)}")
        print(f"Min Date: {df['createdAt'].min()}")
        print(f"Max Date: {df['createdAt'].max()}")
    else:
        print("Pipeline failed to generate output.")