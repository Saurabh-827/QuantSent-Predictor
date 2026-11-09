# X Sentiment and Price Prediction for TSLA: Evaluation Report

Author: Saurabh | Date: 9 Nov 2026 | Asset: TSLA (daily bars)

## 1. Summary

I built an end-to-end pipeline that scrapes X posts (Apify), pulls recent news (Tavily), aligns both with daily TSLA prices in a SQLite database, engineers sentiment and price features, and predicts the TSLA daily return for horizons n+0 to n+5 with a walk-forward validated Ridge model.

**Main result: the model has no out-of-sample predictive skill.**

- RMSE skill versus a naive "training mean return" baseline is at or below zero for every horizon and variant (about -0.024 to +0.001).
- Hit rates are 44% to 53%, which is indistinguishable from a coin flip.
- Adding sentiment features did not help: on the 2017-2019 walk-forward test the sentiment+price model is slightly worse than the price-only model (average RMSE skill about -0.006 vs -0.005).
- No model variant beats buy-and-hold on Sharpe ratio in the 2017-2019 test.
- The few positive Sharpe cells (for example live n+4) are consistent with chance: 24 variant/period/horizon cells were examined and each live cell has only about 100 to 125 days.

One descriptive finding: on the Kaggle data, daily sentiment correlates with the **same-day** return (0.241) but not with the **next-day** return (0.002). This is consistent with sentiment reacting to price rather than leading it.

## 2. Data

| Source                                                       | What                                                                     | Size             | Period                   |
| ------------------------------------------------------------ | ------------------------------------------------------------------------ | ---------------- | ------------------------ |
| Kaggle "Tweets about the Top Companies 2015-2020"            | TSLA tweets (text, likes, retweets, comments)                            | 1,096,868 tweets | 2015-01-01 to 2019-12-31 |
| Apify actor `xquik/x-tweet-scraper` (ID `wAusCMrm284Voaw86`) | Live X posts: query `$TSLA since:D until:D+1`, `Latest`, max 100 per day | 6,844 tweets     | 2026-05-11 to 2026-11-07 |
| Tavily search API                                            | News for "Tesla TSLA stock", last 7 days                                 | 10 results       | Nov 2026                 |
| yfinance                                                     | TSLA daily OHLCV (split-adjusted)                                        | 2015 to Nov 2026 |                          |

Notes:

- The Kaggle data has no follower counts or views. The live Apify data has views and author followers; they are stored in the raw JSON and CSV but **not used as model features** (engagement weighting uses likes + retweets + replies only).
- The live scrape cost about $0.98 in total, including tests (pay-per-result, $0.00015 per tweet).
- News is stored in the `news` table and used only for the sentiment summary, not as a model input (the task asks for a sentiment-and-price-only model).

## 3. Alignment

- All timestamps are converted from UTC to America/New_York.
- A tweet posted at or after 16:00 ET belongs to the next trading day. Weekend and holiday tweets are assigned to the next trading day.
- Tables in `data/quant.db`: `prices`, `tweets`, `daily_sentiment`, `news`.
- Features for day D use only tweets and prices up to the close of D.

## 4. Sentiment and features

Sentiment is the VADER compound score with a few finance terms added to the lexicon (bullish, bearish, rally, plunge, and similar).

Daily sentiment features: mean sentiment, engagement-weighted mean (weight = 1 + log1p(likes + retweets + replies)), positive-minus-negative share (threshold +/-0.05), standard deviation, log tweet-count z-score over 20 days, lags 1 and 2, 3- and 5-day rolling means, and the change versus the 5-day mean.

Price features: daily log return of D and lags 1, 2 and 4, 5-day momentum, 10-day volatility, day of week.

## 5. Model and validation

- Model: standardised features into Ridge regression (alpha = 300, fixed, **no tuning**). One model per horizon.
- Target for horizon h: the log return of trading day D+1+h, where D is the feature day. So n = D+1, and n+0 is the very next session.
- Walk-forward on Kaggle data: expanding window, minimum 504 training days (first out-of-sample day is in early 2017), refit every 21 trading days, with an embargo of h+1 days so no training target overlaps the test block.
- Live data: 126 days is too short to train on, so the model is trained on Kaggle data and applied to live data ("live transfer"). Training and test periods are about 6 years apart.
- Baseline: the mean return of the training window.
- Variants: `full` (sentiment + price) and `price_only`.

Strategy used for risk metrics: position = sign of the predicted return (long or short) for the target day, P&L = position x realised log return minus 5 bps per unit change in position. Sharpe = mean/std x sqrt(252). Sortino = mean/downside deviation (target 0) x sqrt(252). Max drawdown is computed on the equity curve exp(cumulative P&L). These are research metrics with a simple cost model, not a tradable backtest.

## 6. Results

Full output: `results/metrics.csv`. Max DD is the worst peak-to-trough fall of the strategy; B&H Sharpe is buy-and-hold over the same target days.

### 6.1 Kaggle walk-forward (2017-2019)

**Sentiment + price (`full`)**

| Horizon | Days | Hit rate | RMSE skill | Sharpe | Sortino | Max DD | B&H Sharpe |
| ------- | ---- | -------- | ---------- | ------ | ------- | ------ | ---------- |
| n+0     | 736  | 0.469    | -0.007     | -0.954 | -1.267  | -82.2% | 0.395      |
| n+1     | 736  | 0.492    | -0.006     | 0.075  | 0.108   | -55.0% | 0.416      |
| n+2     | 736  | 0.504    | -0.004     | 0.033  | 0.047   | -60.8% | 0.436      |
| n+3     | 736  | 0.486    | -0.007     | -0.633 | -0.888  | -74.6% | 0.469      |
| n+4     | 736  | 0.477    | -0.007     | -0.868 | -1.184  | -82.1% | 0.436      |
| n+5     | 736  | 0.486    | -0.007     | -1.071 | -1.413  | -88.1% | 0.432      |

**Price only (`price_only`)**

| Horizon | Days | Hit rate | RMSE skill | Sharpe | Sortino | Max DD | B&H Sharpe |
| ------- | ---- | -------- | ---------- | ------ | ------- | ------ | ---------- |
| n+0     | 745  | 0.472    | -0.003     | -0.995 | -1.302  | -84.8% | 0.431      |
| n+1     | 745  | 0.466    | -0.003     | -0.830 | -1.159  | -72.2% | 0.429      |
| n+2     | 745  | 0.495    | -0.003     | -0.276 | -0.391  | -52.6% | 0.452      |
| n+3     | 745  | 0.495    | -0.006     | -0.683 | -0.935  | -81.5% | 0.473      |
| n+4     | 745  | 0.475    | -0.005     | -1.221 | -1.670  | -87.9% | 0.442      |
| n+5     | 745  | 0.495    | -0.007     | -0.814 | -1.097  | -90.8% | 0.438      |

### 6.2 Live transfer (May to Nov 2026)

**Sentiment + price (`full`)**

| Horizon | Days | Hit rate | RMSE skill | Sharpe | Sortino | Max DD | B&H Sharpe |
| ------- | ---- | -------- | ---------- | ------ | ------- | ------ | ---------- |
| n+0     | 105  | 0.457    | -0.009     | -1.437 | -1.834  | -41.8% | -0.541     |
| n+1     | 104  | 0.442    | -0.020     | -3.171 | -3.636  | -51.6% | -0.436     |
| n+2     | 103  | 0.437    | -0.020     | -0.685 | -1.071  | -24.2% | -0.152     |
| n+3     | 102  | 0.480    | -0.020     | -1.080 | -1.470  | -29.4% | -0.668     |
| n+4     | 101  | 0.525    | -0.006     | 1.057  | 1.700   | -19.3% | -0.627     |
| n+5     | 100  | 0.460    | -0.024     | -2.066 | -2.501  | -38.4% | -0.815     |

**Price only (`price_only`)**

| Horizon | Days | Hit rate | RMSE skill | Sharpe | Sortino | Max DD | B&H Sharpe |
| ------- | ---- | -------- | ---------- | ------ | ------- | ------ | ---------- |
| n+0     | 125  | 0.512    | 0.001      | -0.258 | -0.330  | -26.8% | -0.839     |
| n+1     | 124  | 0.516    | 0.001      | -1.201 | -1.491  | -30.9% | -0.742     |
| n+2     | 123  | 0.512    | 0.000      | -1.058 | -1.324  | -42.0% | -0.853     |
| n+3     | 122  | 0.492    | -0.001     | -0.987 | -1.228  | -38.0% | -0.839     |
| n+4     | 121  | 0.529    | 0.000      | 1.477  | 2.386   | -17.4% | -0.655     |
| n+5     | 120  | 0.450    | -0.004     | -1.744 | -2.148  | -41.6% | -0.542     |

### 6.3 Figures

- Sentiment vs price, live: `results/charts/sentiment_vs_price_live.png`
- Sentiment vs price, Kaggle: `results/charts/sentiment_vs_price_kaggle.png`
- Sharpe by horizon and variant: `results/charts/sharpe_heatmap.png`
- RMSE skill by horizon and variant: `results/charts/rmse_skill_heatmap.png`
- Equity curves, n+1: `results/charts/equity_h1_kaggle.png`, `results/charts/equity_h1_live.png`

## 7. Interpretation

1. **No usable signal.** RMSE skill is at or below zero and hit rates sit near 50%. Predicting daily TSLA returns from VADER sentiment plus lagged returns does not work in this setup.
2. **Sentiment did not add value.** In the live transfer the sentiment model is clearly worse than the price-only one (skill -0.006 to -0.024 vs about 0). Part of this is distribution shift (section 8.1).
3. **Positive Sharpe values are not evidence.** The two best cells (live n+4: 1.06 and 1.48) use about 100 to 125 days and are 2 of 24 cells examined. Kaggle n+1 and n+2 have Sharpe near zero (0.075, 0.033) and the n+1 equity curve peaks near 2.0 in 2018 and falls back to about 1.1 by the end of 2019, while buy-and-hold ends near 1.8.
4. **Sentiment follows price.** The Kaggle correlation of 0.241 with same-day return versus 0.002 with next-day return suggests sentiment mostly reacts to price moves.
5. **The forecast is nearly flat.** Predicted prices stay within about 1% of the last close, so they carry no trading information (table below).

### Demonstration forecast (origin: close of 2026-11-06)

| Horizon | Predicted daily log return | Predicted price |
| ------- | -------------------------- | --------------- |
| n+0     | -0.0033                    | 357.02          |
| n+1     | 0.0054                     | 358.96          |
| n+2     | 0.0036                     | 360.26          |
| n+3     | 0.0010                     | 360.64          |
| n+4     | -0.0020                    | 359.93          |
| n+5     | 0.0008                     | 360.22          |

Predicted prices compound the predicted daily returns from the last close. This table demonstrates that the pipeline runs end to end; it is not a recommendation.

## 8. Limitations

1. **Distribution shift between Kaggle and live data.** Daily sentiment has mean 0.10 and std 0.04 on Kaggle versus mean 0.20 and std 0.13 live, and tweets per day are about 871 versus about 53. A model trained on Kaggle sees live sentiment as unusually high. This likely explains much of the live degradation of the `full` model.
2. **Sparse and uneven live sampling.** The scrape is capped at 100 tweets per calendar day, and some days returned far fewer (for example 16 to 18). Tweets cover all 24 hours with peaks around 22-00 UTC and 13-15 UTC. Monday contains weekend tweets by construction. I did not investigate why some days returned few tweets.
3. **VADER on tweets.** Many tweets are neutral, duplicated spam, or cashtag lists, which VADER scores at zero. A finance-specific model could do better.
4. **Short live test.** Only about 100 to 125 live days, and the live window is 6 years after the training window.
5. **Multiple comparisons.** 24 cells were examined and no correction was applied.
6. **Simple cost model.** 5 bps per position change, no slippage, borrow costs or position sizing.
7. **No tuning.** Ridge alpha and the feature set were fixed before looking at results to avoid fitting the test set.
8. **Single asset, single model family.** Only TSLA and Ridge were tested.
9. **Collected but unused fields.** Views and author followers from the live data are not used as features.

## 9. Reproducing

See `README.md`. API keys go in `.env` (see `.env.example`). The Apify actor ID is `wAusCMrm284Voaw86` (`xquik/x-tweet-scraper`).
