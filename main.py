from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"

RAW_DATA_PATH = DATA_DIR / "wordstat_dynamics_raw.csv"
MONTHLY_INDEX_PATH = DATA_DIR / "wordstat_monthly_index.csv"
LATEST_RANKING_PATH = DATA_DIR / "wordstat_latest_ranking.csv"

RAW_COUNTS_CHART = IMAGES_DIR / "wordstat_raw_counts_by_month.png"
SHARE_CHART = IMAGES_DIR / "wordstat_share_by_month.png"
SMOOTHED_SHARE_CHART = IMAGES_DIR / "wordstat_smoothed_share_by_month.png"
LATEST_SHARE_CHART = IMAGES_DIR / "wordstat_latest_share.png"
YEARLY_TREND_CHART = IMAGES_DIR / "wordstat_yearly_trend.png"

BASE_LANGUAGE = "Java"
SMOOTHING_WINDOW = 6
TREND_WINDOW = 12


@dataclass(frozen=True)
class SummaryResult:
    latest_month: pd.Timestamp
    leader_by_share: str
    leader_share_value: float
    fastest_growth_language: str
    fastest_growth_value: float
    highest_average_share_language: str
    highest_average_share_value: float


def ensure_directories() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def load_raw_data() -> pd.DataFrame:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {RAW_DATA_PATH}. "
            "Run `python load_wordstat.py` first."
        )

    df = pd.read_csv(RAW_DATA_PATH)
    required_columns = {"language", "phrase", "date", "count", "share"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            "The raw CSV does not contain required columns: "
            + ", ".join(sorted(missing_columns))
        )

    df["date"] = pd.to_datetime(df["date"])
    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
    df["share"] = pd.to_numeric(df["share"], errors="coerce").fillna(0)
    return df.sort_values(["language", "date"]).reset_index(drop=True)


def build_monthly_index(raw_df: pd.DataFrame) -> pd.DataFrame:
    monthly = raw_df[["language", "phrase", "date", "count", "share"]].copy()

    java_counts = (
        monthly[monthly["language"] == BASE_LANGUAGE][["date", "count"]]
        .rename(columns={"count": "java_count"})
        .drop_duplicates(subset=["date"])
    )

    if java_counts.empty:
        raise ValueError("Base language Java is missing from the raw dataset.")

    monthly = monthly.merge(java_counts, on="date", how="left")
    monthly["relative_to_java"] = monthly["count"] / monthly["java_count"]

    relative_totals = (
        monthly.groupby("date", as_index=False)["relative_to_java"]
        .sum()
        .rename(columns={"relative_to_java": "relative_total"})
    )
    monthly = monthly.merge(relative_totals, on="date", how="left")
    monthly["share_pct"] = monthly["relative_to_java"] / monthly["relative_total"] * 100

    monthly["smoothed_share_pct"] = (
        monthly.sort_values(["language", "date"])
        .groupby("language")["share_pct"]
        .transform(lambda s: s.rolling(window=SMOOTHING_WINDOW, min_periods=1).mean())
    )
    monthly["count_change_pct"] = (
        monthly.sort_values(["language", "date"])
        .groupby("language")["count"]
        .pct_change()
        .mul(100)
    )

    monthly["share_pct"] = monthly["share_pct"].round(4)
    monthly["smoothed_share_pct"] = monthly["smoothed_share_pct"].round(4)
    monthly["relative_to_java"] = monthly["relative_to_java"].round(6)
    monthly["count_change_pct"] = monthly["count_change_pct"].round(4)
    return monthly.sort_values(["date", "language"]).reset_index(drop=True)


def calculate_trend(series: pd.Series) -> float:
    clean_series = series.dropna()
    if len(clean_series) < 2:
        return 0.0

    if len(clean_series) > TREND_WINDOW:
        clean_series = clean_series.iloc[-TREND_WINDOW:]

    x_values = pd.Series(range(len(clean_series)), dtype="float64")
    y_values = clean_series.reset_index(drop=True).astype("float64")

    x_mean = x_values.mean()
    y_mean = y_values.mean()

    numerator = ((x_values - x_mean) * (y_values - y_mean)).sum()
    denominator = ((x_values - x_mean) ** 2).sum()

    if denominator == 0:
        return 0.0

    monthly_slope = numerator / denominator
    return round(monthly_slope * 12, 4)


def build_latest_ranking(monthly_index_df: pd.DataFrame) -> pd.DataFrame:
    latest_month = monthly_index_df["date"].max()
    latest_df = monthly_index_df[monthly_index_df["date"] == latest_month].copy()

    average_share = (
        monthly_index_df.groupby("language", as_index=False)["share_pct"]
        .mean()
        .rename(columns={"share_pct": "average_share_pct"})
    )
    trends = (
        monthly_index_df.groupby("language")["smoothed_share_pct"]
        .apply(calculate_trend)
        .reset_index(name="yearly_trend_pp")
    )

    latest_df = latest_df.merge(average_share, on="language", how="left")
    latest_df = latest_df.merge(trends, on="language", how="left")
    latest_df = latest_df.sort_values("share_pct", ascending=False).reset_index(drop=True)

    latest_df["average_share_pct"] = latest_df["average_share_pct"].round(4)
    latest_df["yearly_trend_pp"] = latest_df["yearly_trend_pp"].round(4)
    return latest_df


def plot_raw_counts(monthly_index_df: pd.DataFrame) -> None:
    plt.figure(figsize=(12, 7))
    for language in monthly_index_df["language"].unique():
        language_df = monthly_index_df[monthly_index_df["language"] == language]
        plt.plot(language_df["date"], language_df["count"], marker="o", linewidth=2, label=language)

    plt.title("Yandex Wordstat Query Counts by Month")
    plt.xlabel("Month")
    plt.ylabel("Query count")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(RAW_COUNTS_CHART)
    plt.close()


def plot_share(monthly_index_df: pd.DataFrame) -> None:
    plt.figure(figsize=(12, 7))
    for language in monthly_index_df["language"].unique():
        language_df = monthly_index_df[monthly_index_df["language"] == language]
        plt.plot(language_df["date"], language_df["share_pct"], marker="o", linewidth=2, label=language)

    plt.title("PYPL-like Share of Tutorial Searches by Month")
    plt.xlabel("Month")
    plt.ylabel("Share, %")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(SHARE_CHART)
    plt.close()


def plot_smoothed_share(monthly_index_df: pd.DataFrame) -> None:
    plt.figure(figsize=(12, 7))
    for language in monthly_index_df["language"].unique():
        language_df = monthly_index_df[monthly_index_df["language"] == language]
        plt.plot(
            language_df["date"],
            language_df["smoothed_share_pct"],
            linewidth=2.5,
            label=language,
        )

    plt.title("Smoothed PYPL-like Share by Month (6-month average)")
    plt.xlabel("Month")
    plt.ylabel("Smoothed share, %")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(SMOOTHED_SHARE_CHART)
    plt.close()


def plot_latest_share(latest_ranking_df: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 6))
    plt.bar(latest_ranking_df["language"], latest_ranking_df["share_pct"], color="steelblue")
    plt.title("Latest Month Share of Tutorial Searches")
    plt.xlabel("Programming language")
    plt.ylabel("Share, %")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(LATEST_SHARE_CHART)
    plt.close()


def plot_yearly_trend(latest_ranking_df: pd.DataFrame) -> None:
    sorted_df = latest_ranking_df.sort_values("yearly_trend_pp", ascending=False)
    plt.figure(figsize=(10, 6))
    plt.bar(sorted_df["language"], sorted_df["yearly_trend_pp"], color="darkorange")
    plt.title("Estimated Yearly Trend of Smoothed Share")
    plt.xlabel("Programming language")
    plt.ylabel("Trend, percentage points per year")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(YEARLY_TREND_CHART)
    plt.close()


def create_visualizations(monthly_index_df: pd.DataFrame, latest_ranking_df: pd.DataFrame) -> None:
    plot_raw_counts(monthly_index_df)
    plot_share(monthly_index_df)
    plot_smoothed_share(monthly_index_df)
    plot_latest_share(latest_ranking_df)
    plot_yearly_trend(latest_ranking_df)


def summarize_results(monthly_index_df: pd.DataFrame, latest_ranking_df: pd.DataFrame) -> SummaryResult:
    latest_month = latest_ranking_df["date"].max()
    leader_row = latest_ranking_df.loc[latest_ranking_df["share_pct"].idxmax()]
    growth_row = latest_ranking_df.loc[latest_ranking_df["yearly_trend_pp"].idxmax()]

    average_share = (
        monthly_index_df.groupby("language", as_index=False)["share_pct"]
        .mean()
        .sort_values("share_pct", ascending=False)
        .reset_index(drop=True)
    )
    average_row = average_share.iloc[0]

    return SummaryResult(
        latest_month=latest_month,
        leader_by_share=str(leader_row["language"]),
        leader_share_value=float(leader_row["share_pct"]),
        fastest_growth_language=str(growth_row["language"]),
        fastest_growth_value=float(growth_row["yearly_trend_pp"]),
        highest_average_share_language=str(average_row["language"]),
        highest_average_share_value=float(round(average_row["share_pct"], 4)),
    )


def print_summary(summary: SummaryResult) -> None:
    print("\nPYPL-like summary based on Yandex Wordstat:")
    print(f"- Latest month in the dataset: {summary.latest_month.date()}")
    print(
        f"- Leader by latest search share: {summary.leader_by_share} "
        f"({summary.leader_share_value:.2f}%)"
    )
    print(
        f"- Fastest growth by smoothed yearly trend: {summary.fastest_growth_language} "
        f"({summary.fastest_growth_value:.2f} percentage points per year)"
    )
    print(
        f"- Highest average share over the whole period: {summary.highest_average_share_language} "
        f"({summary.highest_average_share_value:.2f}%)"
    )
    print("- Limitations:")
    print("  1. The source is Yandex Wordstat, not Google Trends.")
    print("  2. The method is PYPL-like, not the official PYPL index.")
    print("  3. Historical monthly data in Wordstat starts from 2018.")
    print("  4. Results depend on the chosen tutorial phrases.")
    print("  5. Search interest is a leading indicator, not direct language usage.")


def main() -> None:
    ensure_directories()
    raw_df = load_raw_data()
    monthly_index_df = build_monthly_index(raw_df)
    latest_ranking_df = build_latest_ranking(monthly_index_df)

    monthly_index_df.to_csv(MONTHLY_INDEX_PATH, index=False, encoding="utf-8")
    latest_ranking_df.to_csv(LATEST_RANKING_PATH, index=False, encoding="utf-8")

    create_visualizations(monthly_index_df, latest_ranking_df)
    summary = summarize_results(monthly_index_df, latest_ranking_df)
    print_summary(summary)

    print(f"\nSaved processed monthly index to: {MONTHLY_INDEX_PATH}")
    print(f"Saved latest ranking to: {LATEST_RANKING_PATH}")
    print(f"Saved charts to: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
