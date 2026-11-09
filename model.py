import os
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from features import build, HORIZONS, SENT_COLS, PRICE_COLS

ALPHA = 300        
COST = 0.0005      
MIN_TRAIN = 504    
STEP = 21          


def make_model():
    return make_pipeline(StandardScaler(), Ridge(alpha=ALPHA))


def walk_forward(df, feats, h):
    d = df.dropna(subset=feats).reset_index(drop=True)
    t = f"y{h}"
    out = []
    for s in range(MIN_TRAIN, len(d), STEP):
        train = d.iloc[: s - (h + 1)].dropna(subset=[t])
        test = d.iloc[s: s + STEP].dropna(subset=[t])
        if len(train) < 100 or test.empty:
            continue
        m = make_model().fit(train[feats], train[t])
        o = test[["date", t]].rename(columns={t: "actual"}).copy()
        o["pred"] = m.predict(test[feats])
        o["baseline"] = train[t].mean()
        out.append(o)
    return pd.concat(out, ignore_index=True)


def transfer(train_df, test_df, feats, h):
    t = f"y{h}"
    tr = train_df.dropna(subset=feats + [t])
    te = test_df.dropna(subset=feats + [t])
    m = make_model().fit(tr[feats], tr[t])
    o = te[["date", t]].rename(columns={t: "actual"}).copy()
    o["pred"] = m.predict(te[feats])
    o["baseline"] = tr[t].mean()
    return o


def perf(pnl):
    pnl = pnl.dropna()
    mu, sd = pnl.mean(), pnl.std()
    downside = np.sqrt((np.minimum(pnl, 0) ** 2).mean())
    equity = np.exp(pnl.cumsum())
    dd = equity / equity.cummax() - 1
    ann = np.sqrt(252)
    return {
        "sharpe": mu / sd * ann if sd > 0 else np.nan,
        "sortino": mu / downside * ann if downside > 0 else np.nan,
        "max_dd": dd.min(),
        "total_ret": equity.iloc[-1] - 1,
    }


def evaluate(p):
    p = p.sort_values("date").reset_index(drop=True)
    p["pos"] = np.sign(p["pred"])
    p["pnl_gross"] = p["pos"] * p["actual"]
    p["pnl_net"] = p["pnl_gross"] - COST * p["pos"].diff().abs().fillna(0)
    rmse_m = np.sqrt(((p["pred"] - p["actual"]) ** 2).mean())
    rmse_b = np.sqrt(((p["baseline"] - p["actual"]) ** 2).mean())
    m = perf(p["pnl_net"])
    bh = perf(p["actual"])
    row = {
        "n_days": len(p),
        "hit_rate": (np.sign(p["pred"]) == np.sign(p["actual"])).mean(),
        "rmse_skill": 1 - rmse_m / rmse_b,  
        **m,
        "bh_sharpe": bh["sharpe"],
        "bh_max_dd": bh["max_dd"],
    }
    return row, p


def forecast(kaggle, live, feats):
    full = pd.concat([kaggle, live], ignore_index=True)
    last = live.dropna(subset=feats).iloc[[-1]]
    close = last["close"].iloc[0]
    cum, rows = 0.0, []
    for h in HORIZONS:
        t = f"y{h}"
        tr = full.dropna(subset=feats + [t])
        m = make_model().fit(tr[feats], tr[t])
        r = m.predict(last[feats])[0]
        cum += r
        rows.append({"origin": last["date"].iloc[0].date(), "horizon": f"n+{h}",
                     "pred_daily_logret": r, "pred_price": close * np.exp(cum)})
    return pd.DataFrame(rows)


def main():
    os.makedirs("results", exist_ok=True)
    kaggle, live = build("kaggle"), build("live")
    variants = {"full": SENT_COLS + PRICE_COLS, "price_only": PRICE_COLS}
    rows, preds = [], []
    for vname, feats in variants.items():
        for h in HORIZONS:
            for period, pdf in [("kaggle_walkforward", walk_forward(kaggle, feats, h)),
                                ("live_transfer", transfer(kaggle, live, feats, h))]:
                row, ev = evaluate(pdf)
                rows.append({"variant": vname, "period": period, "horizon": f"n+{h}", **row})
                preds.append(ev.assign(variant=vname, period=period, horizon=h))
    res = pd.DataFrame(rows)
    res.to_csv("results/metrics.csv", index=False)
    pd.concat(preds).to_csv("results/predictions.csv", index=False)
    cols = ["variant", "period", "horizon", "n_days", "hit_rate", "rmse_skill",
            "sharpe", "sortino", "max_dd", "bh_sharpe"]
    print(res[cols].round(3).to_string(index=False))

    fc = forecast(kaggle, live, SENT_COLS + PRICE_COLS)
    fc.to_csv("results/forecast.csv", index=False)
    print(fc.round(4).to_string(index=False))


if __name__ == "__main__":
    main()