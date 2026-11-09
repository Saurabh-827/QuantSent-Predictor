import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results/charts"
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect("data/quant.db")
prices = pd.read_sql("SELECT date, close FROM prices", con, parse_dates=["date"])
daily = pd.read_sql("SELECT * FROM daily_sentiment", con, parse_dates=["trading_date"])
con.close()
prices["ret"] = np.log(prices["close"]).diff()


def sentiment_vs_price(source, title, fname, roll=5):
    s = daily[daily["source"] == source].rename(columns={"trading_date": "date"})
    d = prices.merge(s, on="date", how="inner").sort_values("date").reset_index(drop=True)
    d["sent_roll"] = d["sent_wmean"].rolling(roll).mean()
    c_same = d["sent_wmean"].corr(d["ret"])
    c_next = d["sent_wmean"].corr(d["ret"].shift(-1))

    fig, (ax1, ax3) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    l1 = ax1.plot(d["date"], d["close"], color="tab:blue", label="TSLA close")
    ax1.set_ylabel("Close (split-adjusted, USD)")
    ax2 = ax1.twinx()
    l2 = ax2.plot(d["date"], d["sent_roll"], color="tab:orange", label=f"{roll}-day mean sentiment")
    ax2.axhline(0, color="gray", lw=0.5)
    ax2.set_ylabel("VADER sentiment (engagement-weighted)")
    ax1.legend(l1 + l2, [x.get_label() for x in l1 + l2], loc="upper left")
    ax1.set_title(f"{title}\ncorr(sentiment, same-day ret)={c_same:.3f} | "
                  f"corr(sentiment, next-day ret)={c_next:.3f}")
    ax3.bar(d["date"], d["n_tweets"], color="tab:gray", width=1.0)
    ax3.set_ylabel("Tweets/day")
    fig.tight_layout()
    fig.savefig(f"{OUT}/{fname}", dpi=150)
    plt.close(fig)


def metrics_heatmap(metric="sharpe", fname="sharpe_heatmap.png", lim=2.0, fmt=".2f"):
    m = pd.read_csv("results/metrics.csv")
    m["row"] = m["variant"] + " | " + m["period"]
    pv = m.pivot(index="row", columns="horizon", values=metric)
    fig, ax = plt.subplots(figsize=(9, 4))
    
    im = ax.imshow(pv.values, cmap="RdYlGn", vmin=-lim, vmax=lim, aspect="auto")
    
    ax.set_xticks(range(len(pv.columns)))
    ax.set_xticklabels(pv.columns)
    ax.set_yticks(range(len(pv.index)))
    ax.set_yticklabels(pv.index)
    
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            ax.text(j, i, format(pv.values[i, j], fmt), ha="center", va="center", fontsize=9)
            
    ax.set_title(f"{metric} by horizon and variant")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{fname}", dpi=150)
    plt.close(fig)


def equity_curves(horizon=1, period="kaggle_walkforward", fname="equity_h1_kaggle.png"):
    p = pd.read_csv("results/predictions.csv", parse_dates=["date"])
    p = p[(p["horizon"] == horizon) & (p["period"] == period)]
    fig, ax = plt.subplots(figsize=(11, 5))
    for v, g in p.groupby("variant"):
        g = g.sort_values("date")
        ax.plot(g["date"], np.exp(g["pnl_net"].cumsum()), label=f"model ({v})")
    g = p[p["variant"] == "full"].sort_values("date")
    ax.plot(g["date"], np.exp(g["actual"].cumsum()), color="black", ls="--", label="buy & hold")
    ax.set_title(f"Out-of-sample equity, horizon n+{horizon}, {period}")
    ax.set_ylabel("Growth of 1 (log-return compounding)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{OUT}/{fname}", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    sentiment_vs_price("live", "Live X sentiment vs TSLA price (May-Nov 2026)", "sentiment_vs_price_live.png")
    sentiment_vs_price("kaggle", "Kaggle X sentiment vs TSLA price (2015-2019)", "sentiment_vs_price_kaggle.png", roll=20)
    
    metrics_heatmap("sharpe", "sharpe_heatmap.png")
    metrics_heatmap("rmse_skill", "rmse_skill_heatmap.png", lim=0.03, fmt=".3f")
    
    equity_curves(1, "kaggle_walkforward", "equity_h1_kaggle.png")
    equity_curves(1, "live_transfer", "equity_h1_live.png")
    print("Charts saved in", OUT)