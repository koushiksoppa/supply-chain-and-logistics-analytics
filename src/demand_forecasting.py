"""
demand_forecasting.py
------------------------
Monthly/regional demand trends, forecast accuracy analysis (using the
Forecast Error features engineered in Step 3), and a time-series
decomposition + short-horizon forecast to demonstrate the technique.

Run: python3 demand_forecasting.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

CLEAN_PATH = "../data/processed/supply_chain_orders_clean.csv"

OUT_MONTHLY = "../data/processed/monthly_trends.csv"
OUT_REGIONAL = "../data/processed/regional_trends.csv"
OUT_FORECAST_ACCURACY = "../data/processed/forecast_accuracy.csv"
OUT_FORECAST_RESULT = "../data/processed/demand_forecast_next_quarter.csv"

CHART_MONTHLY_TREND = "../images/charts/monthly_revenue_demand_trend.png"
CHART_FORECAST_ACCURACY = "../images/charts/forecast_accuracy_by_category.png"
CHART_DECOMPOSITION = "../images/charts/demand_time_series_decomposition.png"


def load_data():
    df = pd.read_csv(CLEAN_PATH, parse_dates=["Order Date"])
    print(f"Loaded {len(df):,} orders spanning {df['Order Date'].min().date()} to {df['Order Date'].max().date()}")
    return df


def monthly_trend_analysis(df: pd.DataFrame) -> pd.DataFrame:
    monthly = df.groupby(pd.Grouper(key="Order Date", freq="MS")).agg(
        Total_Orders=("Order ID", "count"),
        Total_Revenue=("Selling Price", "sum"),
        Total_Demand=("Demand", "sum"),
        Total_Profit=("Profit", "sum"),
        Avg_Order_Value=("Selling Price", "mean"),
    ).reset_index()

    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.bar(monthly["Order Date"], monthly["Total_Revenue"] / 1e7, width=20, color="#2E5FA3", alpha=0.75, label="Revenue (₹ Cr)")
    ax1.set_ylabel("Revenue (₹ Crore)", color="#2E5FA3")
    ax1.set_xlabel("Month")
    ax2 = ax1.twinx()
    ax2.plot(monthly["Order Date"], monthly["Total_Demand"], color="#D9534F", marker="o", linewidth=2, label="Total Demand")
    ax2.set_ylabel("Total Demand (units)", color="#D9534F")
    plt.title("Monthly Revenue & Demand Trend")
    fig.tight_layout()
    plt.savefig(CHART_MONTHLY_TREND, dpi=130)
    plt.close()

    monthly.to_csv(OUT_MONTHLY, index=False)
    print(f"\nSaved monthly trends to {OUT_MONTHLY} and chart to {CHART_MONTHLY_TREND}")
    preview = monthly.tail(6).copy()
    preview["Order Date"] = preview["Order Date"].dt.date
    print(preview.round(1).to_string(index=False))
    return monthly


def regional_trend_analysis(df: pd.DataFrame) -> pd.DataFrame:
    regional = df.groupby(["Region", "Order Quarter"]).agg(
        Total_Orders=("Order ID", "count"),
        Total_Revenue=("Selling Price", "sum"),
        Total_Demand=("Demand", "sum"),
        Late_Delivery_Rate=("Late Delivery Flag", lambda x: round((x == "Yes").mean() * 100, 1)),
    ).reset_index()
    regional.to_csv(OUT_REGIONAL, index=False)
    print(f"\nSaved regional trends to {OUT_REGIONAL}")
    return regional


def forecast_accuracy_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """MAE, MAPE, and forecast bias by category — surfaces which product
    categories are hardest to forecast (this traces back to the
    category-specific forecast noise built into Step 2's simulation)."""
    acc = df.groupby("Category").agg(
        Total_Orders=("Order ID", "count"),
        Avg_Actual_Demand=("Demand", "mean"),
        Avg_Forecast_Demand=("Forecast Demand", "mean"),
        MAE=("Absolute Forecast Error", "mean"),
        MAPE=("Forecast Error %", "mean"),
        Forecast_Bias=("Forecast Error", "mean"),  # positive = over-forecasting, negative = under-forecasting
    ).round(2).sort_values("MAPE", ascending=False)

    acc["Forecast Accuracy %"] = round(100 - acc["MAPE"], 1)

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = plt.cm.RdYlGn(np.linspace(0.15, 0.85, len(acc)))
    ax.barh(acc.index, acc["Forecast Accuracy %"], color=colors)
    ax.set_xlabel("Forecast Accuracy %")
    ax.set_title("Demand Forecast Accuracy by Category")
    ax.invert_yaxis()
    fig.tight_layout()
    plt.savefig(CHART_FORECAST_ACCURACY, dpi=130)
    plt.close()

    acc.to_csv(OUT_FORECAST_ACCURACY)
    print(f"\n--- Forecast accuracy by category ---\n{acc[['MAPE', 'Forecast Accuracy %', 'Forecast_Bias']]}")
    print(f"\nSaved to {OUT_FORECAST_ACCURACY} and chart to {CHART_FORECAST_ACCURACY}")
    return acc


def time_series_decomposition_and_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly decomposition for visualization, plus a monthly seasonal-index
    forecast for the next quarter.

    Note on method: with only 2 years of history, statsmodels' built-in
    seasonal Holt-Winters needs more full annual cycles than we can spare
    for an honest holdout test (a trend-only fallback was tried first and
    failed badly — ~100% MAPE — specifically because the holdout window
    landed on the Nov/Dec peak season it had never learned a seasonal
    pattern for). Instead we compute explicit month-of-year seasonal
    indices from the training data and apply them to a fitted trend line —
    simpler, fully transparent, and validates cleanly on a holdout.
    """
    weekly = df.groupby(pd.Grouper(key="Order Date", freq="W"))["Demand"].sum()
    weekly = weekly.asfreq("W").fillna(weekly.mean())

    decomposition = seasonal_decompose(weekly, model="additive", period=52, extrapolate_trend="freq")
    fig = decomposition.plot()
    fig.set_size_inches(10, 8)
    fig.suptitle("Weekly Demand — Time Series Decomposition", y=1.02)
    fig.tight_layout()
    fig.savefig(CHART_DECOMPOSITION, dpi=130)
    plt.close(fig)
    print(f"\nSaved time series decomposition chart to {CHART_DECOMPOSITION}")

    # --- Monthly seasonal-index forecast ---
    monthly = df.groupby(pd.Grouper(key="Order Date", freq="MS"))["Demand"].sum()
    monthly_idx = pd.DataFrame({"Demand": monthly})
    monthly_idx["t"] = np.arange(len(monthly_idx))
    monthly_idx["Month"] = monthly_idx.index.month

    def fit_and_forecast(train_df, forecast_periods, seasonal_source):
        # Linear trend fit on the training window
        slope, intercept = np.polyfit(train_df["t"], train_df["Demand"], 1)
        # Seasonal index: each month's average deviation from its own trend value
        seasonal_source = seasonal_source.copy()
        seasonal_source["Trend"] = slope * seasonal_source["t"] + intercept
        seasonal_source["Ratio"] = seasonal_source["Demand"] / seasonal_source["Trend"]
        seasonal_index = seasonal_source.groupby("Month")["Ratio"].mean()
        seasonal_index = seasonal_index / seasonal_index.mean()  # normalize so index averages to 1.0

        forecasts = []
        for t, month in forecast_periods:
            trend_val = slope * t + intercept
            idx = seasonal_index.get(month, 1.0)
            forecasts.append(max(trend_val * idx, 0))
        return forecasts, seasonal_index

    # Holdout validation: train on everything except the last 3 months, test on them
    train = monthly_idx.iloc[:-3]
    test = monthly_idx.iloc[-3:]
    test_periods = list(zip(test["t"], test["Month"]))
    test_forecast, _ = fit_and_forecast(train, test_periods, seasonal_source=train)
    mape = np.mean(np.abs((test["Demand"].values - np.array(test_forecast)) / test["Demand"].values)) * 100
    print(f"\nSeasonal-index model holdout MAPE (last 3 months, incl. Dec peak): {mape:.1f}%")

    # Final forecast: fit on full history, forecast next 3 months (Q1 2026)
    future_t = np.arange(len(monthly_idx), len(monthly_idx) + 3)
    future_months = [((monthly_idx.index[-1] + pd.DateOffset(months=i)).month) for i in range(1, 4)]
    future_periods = list(zip(future_t, future_months))
    future_forecast, seasonal_index = fit_and_forecast(monthly_idx, future_periods, seasonal_source=monthly_idx)

    future_dates = [monthly_idx.index[-1] + pd.DateOffset(months=i) for i in range(1, 4)]
    forecast_df = pd.DataFrame({
        "Month": [d.strftime("%Y-%m") for d in future_dates],
        "Forecasted Demand": np.round(future_forecast, 0),
    })
    forecast_df.to_csv(OUT_FORECAST_RESULT, index=False)
    print(f"\nNext-quarter monthly demand forecast saved to {OUT_FORECAST_RESULT}")
    print(forecast_df.to_string(index=False))
    return forecast_df


def main():
    df = load_data()
    monthly_trend_analysis(df)
    regional_trend_analysis(df)
    forecast_accuracy_analysis(df)
    time_series_decomposition_and_forecast(df)


if __name__ == "__main__":
    main()
