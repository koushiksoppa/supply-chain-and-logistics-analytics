"""
clean_and_engineer.py
----------------------
Takes the raw synthetic order data and produces an analysis-ready dataset:

1. Missing value handling  — distinguishes *structural* nulls (a Cancelled
   order will never have a Delivery Date — that's not "missing data", it's
   correct) from genuine data-quality nulls, which get logged and handled
   explicitly rather than silently dropped.
2. Outlier detection        — flags statistical outliers per category using
   the IQR method, but does NOT delete them. In supply chain data, a huge
   bulk order or an unusually long transit time is often a real business
   event, not bad data — flagging preserves it for the analyst to decide.
3. Feature engineering      — derives the time, cost, and delay features
   that later KPI/BI work depends on (lead times, profit margin, delivery
   delay vs. a defined SLA, calendar fields, fill-rate inputs).

Run: python3 clean_and_engineer.py
"""

import numpy as np
import pandas as pd

RAW_PATH = "../data/raw/supply_chain_orders.csv"
OUT_PATH = "../data/processed/supply_chain_orders_clean.csv"

# Business-defined SLA (promised delivery days from Order Date), independent
# of how the raw data was generated — this is the "policy" an analyst would
# be handed by Ops to measure delivery performance against.
SLA_DAYS_BY_MODE = {"Air": 3, "Road": 6, "Rail": 5, "Sea": 9}

# Columns where extreme values are checked for outliers (right-skewed cost /
# time fields — the ones that actually matter for financial and ops analysis)
OUTLIER_COLUMNS = ["Selling Price", "Procurement Cost", "Shipping Cost", "Distance"]


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(
        RAW_PATH,
        parse_dates=["Order Date", "Ship Date", "Delivery Date"],
    )
    print(f"Loaded raw data: {df.shape[0]:,} rows, {df.shape[1]} columns")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Log every column's null count, then handle each type explicitly."""
    null_counts = df.isnull().sum()
    null_counts = null_counts[null_counts > 0]
    print("\n--- Missing value audit ---")
    print(null_counts if len(null_counts) else "No nulls found.")

    # Delivery Date is structurally null for Cancelled / Backordered / In
    # Transit orders (there's nothing to fill it with — the order was never
    # delivered). We make that explicit with a boolean flag instead of
    # leaving an unexplained blank column, which is what a stakeholder
    # opening the CSV would otherwise wonder about.
    df["Is Delivered"] = df["Order Status"].eq("Delivered") | df["Order Status"].eq("Returned")
    undelivered_statuses = df.loc[df["Delivery Date"].isna(), "Order Status"].unique()
    print(f"\nDelivery Date is null only for statuses: {sorted(undelivered_statuses)}")
    assert set(undelivered_statuses) <= {"Cancelled", "Backordered", "In Transit"}, \
        "Unexpected status has a null Delivery Date — investigate before proceeding."

    # Guard rail: any other unexpected nulls (e.g. from a future re-run with
    # a bug) get imputed conservatively and logged, never silently dropped.
    other_nulls = null_counts.drop(labels=["Delivery Date"], errors="ignore")
    for col in other_nulls.index:
        if df[col].dtype == object:
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = df[col].fillna(df[col].median())
        print(f"Imputed {other_nulls[col]} unexpected nulls in '{col}'")

    return df


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """IQR-based outlier flagging, computed per Category (a ₹500 grocery
    order and a ₹500 electronics order are not on the same distribution —
    flagging on the global column would just mark every electronics row
    as an 'outlier')."""
    print("\n--- Outlier detection (IQR method, per category) ---")
    for col in OUTLIER_COLUMNS:
        flag_col = f"{col} Outlier"
        df[flag_col] = False
        for category, group in df.groupby("Category"):
            q1, q3 = group[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (df["Category"] == category) & ((df[col] < lower) | (df[col] > upper))
            df.loc[mask, flag_col] = True
        pct = df[flag_col].mean() * 100
        print(f"{col}: {df[flag_col].sum():,} outliers flagged ({pct:.1f}%) — kept in dataset, not removed")

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    print("\n--- Feature engineering ---")

    # --- Time-based features ---
    df["Order Year"] = df["Order Date"].dt.year
    df["Order Month"] = df["Order Date"].dt.month
    df["Order Month Name"] = df["Order Date"].dt.strftime("%b")
    df["Order Quarter"] = df["Order Date"].dt.quarter
    df["Order Day Of Week"] = df["Order Date"].dt.day_name()
    df["Is Weekend Order"] = df["Order Date"].dt.dayofweek.isin([5, 6])

    # --- Lead time / fulfillment features ---
    df["Order To Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Ship To Delivery Days"] = (df["Delivery Date"] - df["Ship Date"]).dt.days
    df["Order To Delivery Days"] = (df["Delivery Date"] - df["Order Date"]).dt.days

    # --- Delivery delay vs. a defined SLA (business policy, not generator internals) ---
    df["SLA Days"] = df["Transportation Mode"].map(SLA_DAYS_BY_MODE)
    df["Delivery Delay Days"] = np.where(
        df["Is Delivered"],
        (df["Order To Delivery Days"] - df["SLA Days"]).clip(lower=0),
        np.nan,
    )
    # Recompute Late Delivery Flag against this explicit SLA definition so the
    # flag is reproducible from data alone, not tied to hidden generation logic.
    df["Late Delivery Flag"] = np.where(
        df["Is Delivered"], np.where(df["Delivery Delay Days"] > 0, "Yes", "No"), "No"
    )

    # --- Financial features ---
    df["Total Cost"] = df["Procurement Cost"] + df["Shipping Cost"] + df["Warehouse Cost"]
    df["Profit"] = round(df["Selling Price"] - df["Total Cost"], 2)
    df["Profit Margin %"] = np.round(np.where(
        df["Selling Price"] > 0, df["Profit"] / df["Selling Price"] * 100, 0
    ), 2)
    df["Revenue Per Unit"] = round(df["Selling Price"] / df["Order Quantity"], 2)
    df["Cost Per Unit"] = round(df["Total Cost"] / df["Order Quantity"], 2)

    # --- Inventory / fill-rate inputs (used for Fill Rate & Stockout KPIs later) ---
    df["Fill Rate"] = np.where(
        df["Demand"] > 0, (df["Stock Issued"] / df["Demand"]).clip(upper=1.0), 1.0
    )
    df["Stockout Flag"] = df["Inventory Level"] <= 0
    df["Fully Fulfilled Flag"] = df["Stock Issued"] >= df["Order Quantity"]

    # --- Forecast accuracy input (used in Step 6 demand forecasting analysis) ---
    df["Forecast Error"] = df["Forecast Demand"] - df["Demand"]
    df["Absolute Forecast Error"] = df["Forecast Error"].abs()
    df["Forecast Error %"] = np.round(
        np.where(df["Demand"] > 0, df["Absolute Forecast Error"] / df["Demand"] * 100, 0), 2
    )

    print(f"Added {19} engineered feature columns")
    return df


def run_quality_checks(df: pd.DataFrame) -> None:
    print("\n--- Post-processing quality checks ---")
    assert (df["Order To Ship Days"] >= 0).all(), "Negative lead time detected"
    assert (df.loc[df["Is Delivered"], "Order To Delivery Days"] >= 0).all(), "Negative fulfillment time detected"
    assert df["Profit Margin %"].between(-1000, 100).all(), "Profit margin out of plausible range"
    print("All quality checks passed.")


def main():
    df = load_raw()
    df = handle_missing_values(df)
    df = detect_outliers(df)
    df = engineer_features(df)
    run_quality_checks(df)

    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved cleaned + engineered dataset to {OUT_PATH}")
    print(f"Final shape: {df.shape[0]:,} rows, {df.shape[1]} columns")


if __name__ == "__main__":
    main()
