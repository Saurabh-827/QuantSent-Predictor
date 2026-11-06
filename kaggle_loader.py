import os
import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter


df = kagglehub.dataset_load(KaggleDatasetAdapter.PANDAS, "omermetinn/tweets-about-the-top-companies-from-2015-to-2020", "Company_Tweet.csv")
TSLA_Tweets = df[df['ticker_symbol'] == "TSLA"]

cache_dir = "data"
cache_file = f"{cache_dir}/TSLA_tweets.csv"
os.makedirs(cache_dir, exist_ok=True)

if os.path.exists(cache_file):
    Tweet_TSLA = pd.read_csv(cache_file, parse_dates=["post_date"])
    if "Unnamed: 0" in Tweet_TSLA.columns:
        Tweet_TSLA.drop(columns=["Unnamed: 0"], inplace=True)
else:
    tsla_tweet_ids = set(TSLA_Tweets['tweet_id'])
    path = kagglehub.dataset_download("omermetinn/tweets-about-the-top-companies-from-2015-to-2020")
    chunks = pd.read_csv(f"{path}/Tweet.csv", chunksize=200_000, dtype={"tweet_id": "int64"})
    processedChunks = []
    
    for chunk in chunks:
        filtered_TSLA_chunks = chunk[chunk["tweet_id"].isin(tsla_tweet_ids)]
        if not filtered_TSLA_chunks.empty:
            processedChunks.append(filtered_TSLA_chunks)

    if not processedChunks:
        raise ValueError("Error: len(Tweet_TSLA) is 0! Dtype or ID matching failed.")
    
    Tweet_TSLA = pd.concat(processedChunks, ignore_index=True)
    Tweet_TSLA['post_date'] = pd.to_datetime(Tweet_TSLA["post_date"], unit='s')
    
    Tweet_TSLA.to_csv(cache_file, index=False)

# --- DIAGNOSTICS & VALIDATION ---
print("\n--- SANITY CHECKS ---")
print(f"Total TSLA Tweets in Memory: {len(Tweet_TSLA)}")

print("\n--- DATAFRAME INFO ---")
print("Columns:", Tweet_TSLA.columns.tolist())

print("\n--- DATE RANGE & DAILY STATS ---")
print(f"Start Date: {Tweet_TSLA['post_date'].min()}")
print(f"End Date: {Tweet_TSLA['post_date'].max()}")

daily_counts = Tweet_TSLA.groupby(Tweet_TSLA["post_date"].dt.date).size()
print("\nDaily Tweets Statistics:\n", daily_counts.describe())