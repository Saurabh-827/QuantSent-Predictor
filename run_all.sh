#!/usr/bin/env bash
set -e
mkdir -p data
python3 price_ingestion.py
python3 kaggle_loader.py
if [ -n "$RUN_APIFY" ]; then
  python3 -c "from apify_scraper import fetch_range; fetch_range('2026-05-11', '2026-11-07')"
elif [ ! -f data/tsla_live_tweets.csv ]; then
  cp sample_data/tsla_live_tweets.csv data/tsla_live_tweets.csv
fi
python3 news_ingestion.py
python3 sentiment.py
python3 build_db.py
python3 model.py
python3 charts.py