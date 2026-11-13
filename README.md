# QuantSent Predictor: X Sentiment and Price Prediction (TSLA)

Pipeline that scrapes X (Twitter) posts and news, aligns them with TSLA daily prices in SQLite, builds sentiment and price features, and forecasts the return at horizons n+0 to n+5 with walk-forward validation.

Results and discussion: see [REPORT.md](REPORT.md). Short version: the model shows no out-of-sample skill, and that is reported honestly.

## Services and IDs used

| Service  | What for          | ID / name                                                                                   |
| -------- | ----------------- | ------------------------------------------------------------------------------------------- |
| Apify    | Live X posts      | Actor `xquik/x-tweet-scraper` (ID `wAusCMrm284Voaw86`), pay-per-result ($0.00015 per tweet) |
| Tavily   | Recent news       | `tavily-python`, topic `news`                                                               |
| Kaggle   | Historical tweets | `omermetinn/tweets-about-the-top-companies-from-2015-to-2020`                               |
| yfinance | TSLA prices       | Yahoo Finance                                                                               |

Exa is not used.

## Setup

Tested with Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then fill in your own keys
```

`.env` needs `TAVILY_API_KEY`, and `APIFY_TOKEN` only if you scrape fresh live data.. Both services have free tiers. The live scrape of 181 daily windows costs about $1 on Apify. The Kaggle dataset is public; if kagglehub asks for credentials, set `KAGGLE_USERNAME` and `KAGGLE_KEY`.

## Run order

Run everything with one command: `bash run_all.sh`. By default the pipeline uses the bundled live tweet sample in `sample_data/`. Run `RUN_APIFY=1 bash run_all.sh` to scrape fresh data with your own Apify token.

Or step by step:

```bash
python3 price_ingestion.py     # TSLA daily prices      -> data/TSLA_prices.csv
python3 kaggle_loader.py       # TSLA tweets 2015-2019  -> data/TSLA_tweets.csv (first run is slow)
python3 apify_scraper.py       # live tweets            -> data/tsla_live_tweets.csv
python3 news_ingestion.py      # Tavily news            -> data/tsla_news.json
python3 sentiment.py           # VADER scores           -> data/kaggle_scored.csv, data/live_scored.csv
python3 build_db.py            # alignment + SQLite     -> data/quant.db
python3 features.py            # optional: feature summary
python3 model.py               # walk-forward models    -> results/metrics.csv, predictions.csv, forecast.csv
python3 charts.py              # figures                -> results/charts/*.png
```

`apify_scraper.py` caches each daily query in `data/raw/`, so re-running does not spend credits again. Edit the date range in its `__main__` block (a 3-day test range is set by default; the full run is `fetch_range("2026-05-11", "2026-11-07")`).

## Layout

| File                 | Purpose                                                                    |
| -------------------- | -------------------------------------------------------------------------- |
| `price_ingestion.py` | Download TSLA prices, compute log returns                                  |
| `kaggle_loader.py`   | Extract TSLA tweets from the Kaggle dataset                                |
| `apify_scraper.py`   | Daily-window live scrape with a spend guard ($3)                           |
| `news_ingestion.py`  | Tavily news search                                                         |
| `sentiment.py`       | VADER scoring (with a small finance lexicon)                               |
| `build_db.py`        | UTC to US Eastern, trading-day assignment, daily aggregates, SQLite tables |
| `features.py`        | Sentiment and price features, multi-horizon targets                        |
| `model.py`           | Ridge walk-forward validation, Sharpe / Sortino / Max Drawdown, forecast   |
| `charts.py`          | Sentiment vs price, metric heatmaps, equity curves                         |
| `results/`           | Metrics, predictions, forecast and charts                                  |

## Design choices

- Features for trading day D use only data up to the 16:00 ET close of D. The target for horizon h is the return of day D+1+h, so there is no look-ahead.
- Walk-forward: expanding window, refit every 21 days, embargo of h+1 days.
- Ridge alpha is fixed (not tuned) to avoid fitting the test set.
- Live data is too short to train on, so the model is trained on Kaggle data and evaluated on live data.

See the limitations section in [REPORT.md](REPORT.md).
