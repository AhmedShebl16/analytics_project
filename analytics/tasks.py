import os
import re
import pandas as pd
from celery import shared_task
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DUMP_FILE = BASE_DIR / "data" / "data.sql"
OUTPUT_DIR = "output"
TABLES     = ["customers", "enhanced_orders", "order_products"]

@shared_task
def extract_data():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(DUMP_FILE, encoding="utf8", errors="ignore") as f:
        sql = f.read()

    def has_inserts(tbl):
        return bool(re.search(rf"INSERT INTO\s+`?{tbl}`?\s*\(", sql, re.I))

    def parse_insert(tbl):
        pattern = re.compile(
            rf"INSERT INTO\s+`?{tbl}`?\s*\((?P<cols>.*?)\)\s*VALUES\s*(?P<vals>.*?);",
            re.S | re.I
        )
        cols, rows = None, []
        for m in pattern.finditer(sql):
            if cols is None:
                cols = [c.strip(" `") for c in m.group("cols").split(",")]
            for tup in re.findall(r"\((.*?)\)(?:,|$)", m.group("vals"), re.S):
                row, curr, in_str, prev = [], "", False, ""
                for ch in tup:
                    if ch=="'" and prev!="\\":
                        in_str = not in_str
                        curr += ch
                    elif ch=="," and not in_str:
                        row.append(curr.strip().strip("'")); curr = ""
                    else:
                        curr += ch
                    prev = ch
                if curr:
                    row.append(curr.strip().strip("'"))
                rows.append(row)
        if not rows or cols is None:
            return pd.DataFrame()
        return pd.DataFrame(rows, columns=cols)

    exported = {}
    for tbl in TABLES:
        if not has_inserts(tbl):
            continue
        df = parse_insert(tbl)
        if not df.empty:
            path = os.path.join(OUTPUT_DIR, f"{tbl}.csv")
            df.to_csv(path, index=False)
            exported[tbl] = len(df)

    return {"exported_rows": exported}


@shared_task
def analyze_data():
    df_cust = pd.read_csv(f"{OUTPUT_DIR}/customers.csv")
    df_ord  = pd.read_csv(f"{OUTPUT_DIR}/enhanced_orders.csv", parse_dates=["created_at"])
    df_prod = pd.read_csv(f"{OUTPUT_DIR}/order_products.csv")

    # Customer stats
    df_ord = df_ord.sort_values(["customer_id","created_at"])
    df_ord["prev_date"] = df_ord.groupby("customer_id")["created_at"].shift(1)
    df_ord["diff_days"] = (df_ord["created_at"] - df_ord["prev_date"]).dt.days
    avg_int = df_ord.groupby("customer_id")["diff_days"].mean().rename("avg_interval_days")
    last_v  = df_ord.groupby("customer_id")["created_at"].max().rename("last_visit")
    stats   = df_cust.set_index("id").join([last_v, avg_int]).reset_index()
    stats["next_visit_pred"] = stats["last_visit"] + pd.to_timedelta(stats["avg_interval_days"], unit="D")

    # Sales forecast
    df_prod["quantity"] = pd.to_numeric(df_prod["quantity"], errors="coerce").fillna(0)
    df_prod["price"]    = pd.to_numeric(df_prod["price"], errors="coerce").fillna(0)
    df_prod["line_total"] = df_prod["quantity"] * df_prod["price"]
    dates = df_ord[["id","created_at"]].rename(columns={"id":"order_id","created_at":"date"})
    df_prod = df_prod.merge(dates, on="order_id", how="left").set_index("date")
    weekly = df_prod["line_total"].resample("W-MON").sum()
    forecast = weekly.tail(3).mean() if len(weekly)>=3 else weekly.mean()


    return {
        "customer_stats_sample": stats[["name","last_visit","avg_interval_days","next_visit_pred"]]
                                    .head(5)
                                    .to_dict(orient="records"),
        "weekly_sales_tail": weekly.tail(6).to_dict(),
        "forecast_next_week": float(forecast),
    }


@shared_task
def generate_report():
    # Re‐use analysis to get forecast and plan
    analysis = analyze_data()
    # (Here you’d re‐run report‐generation logic, e.g. write Excel)
    report_path = "sales_report.xlsx"
    return {"report_path": report_path}
