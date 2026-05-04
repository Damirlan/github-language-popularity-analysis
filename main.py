from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"
RAW_DATA_PATH = DATA_DIR / "github_repositories.csv"
STATS_DATA_PATH = DATA_DIR / "github_language_stats.csv"

GITHUB_API_URL = "https://api.github.com/search/repositories"
DEFAULT_LANGUAGES = ["Python", "JavaScript", "Java", "Go", "Rust", "Kotlin"]
DEFAULT_YEARS = list(range(2015, 2026))
REQUEST_TIMEOUT = 30
REQUEST_PAUSE_SECONDS = 2
RESULTS_PER_PAGE = 100


def ensure_directories() -> None:
    """Create folders for data and charts if they do not exist yet."""
    DATA_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def create_session(token: str | None) -> requests.Session:
    """Create a configured session for GitHub API requests."""
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-language-popularity-analysis",
        }
    )

    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    else:
        print("Warning: GITHUB_TOKEN not found. Requests will use lower rate limits.")

    return session


def wait_for_rate_limit(response: requests.Response) -> None:
    """Pause execution until the GitHub API rate limit resets."""
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset_timestamp = response.headers.get("X-RateLimit-Reset")

    if remaining != "0" or not reset_timestamp:
        return

    reset_time = datetime.fromtimestamp(int(reset_timestamp))
    wait_seconds = max(int(reset_timestamp) - int(time.time()) + 1, 1)
    print(
        "GitHub API rate limit reached. "
        f"Waiting {wait_seconds} seconds until {reset_time}."
    )
    time.sleep(wait_seconds)


def build_search_query(language: str, year: int) -> str:
    """Build GitHub Search API query for a single language and year."""
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    return f"language:{language} created:{start_date}..{end_date}"


def fetch_repositories_for_year(
    session: requests.Session, language: str, year: int
) -> list[dict]:
    """
    Fetch one page of repositories for a language and year.

    For a study project we intentionally limit the sample to the first page
    (up to 100 repositories) for each language-year pair.
    """
    params = {
        "q": build_search_query(language, year),
        "sort": "stars",
        "order": "desc",
        "per_page": RESULTS_PER_PAGE,
        "page": 1,
    }

    print(f"Requesting data for {language}, {year}...")

    try:
        response = session.get(GITHUB_API_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as error:
        print(f"Request failed for {language}, {year}: {error}")
        return []

    if response.status_code == 403:
        wait_for_rate_limit(response)
        try:
            response = session.get(GITHUB_API_URL, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            print(f"Retry failed for {language}, {year}: {error}")
            return []

    if response.status_code != 200:
        print(
            f"GitHub API returned status {response.status_code} "
            f"for {language}, {year}: {response.text}"
        )
        return []

    try:
        payload = response.json()
    except ValueError:
        print(f"Failed to parse JSON response for {language}, {year}.")
        return []

    return payload.get("items", [])


def transform_repositories(language: str, items: Iterable[dict]) -> list[dict]:
    """Convert GitHub API items into rows for a pandas DataFrame."""
    rows: list[dict] = []

    for item in items:
        created_at = item.get("created_at", "")
        year = created_at[:4] if created_at else None

        rows.append(
            {
                "repository_name": item.get("full_name"),
                "language": language,
                "created_at": created_at,
                "created_year": int(year) if year else None,
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "open_issues": item.get("open_issues_count", 0),
                "html_url": item.get("html_url"),
                "description": item.get("description") or "",
            }
        )

    return rows


def collect_data(
    languages: list[str], years: list[int], session: requests.Session
) -> pd.DataFrame:
    """Collect repository data for all requested languages and years."""
    all_rows: list[dict] = []

    for language in languages:
        for year in years:
            items = fetch_repositories_for_year(session, language, year)
            rows = transform_repositories(language, items)
            all_rows.extend(rows)
            print(f"Collected {len(rows)} repositories for {language}, {year}.")
            time.sleep(REQUEST_PAUSE_SECONDS)

    return pd.DataFrame(all_rows)


def aggregate_data(repositories_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate summary statistics by language and year."""
    if repositories_df.empty:
        return pd.DataFrame(
            columns=[
                "language",
                "created_year",
                "repositories_count",
                "total_stars",
                "average_stars",
                "average_forks",
            ]
        )

    stats_df = (
        repositories_df.groupby(["language", "created_year"], as_index=False)
        .agg(
            repositories_count=("repository_name", "count"),
            total_stars=("stars", "sum"),
            average_stars=("stars", "mean"),
            average_forks=("forks", "mean"),
        )
        .sort_values(["language", "created_year"])
    )

    stats_df["average_stars"] = stats_df["average_stars"].round(2)
    stats_df["average_forks"] = stats_df["average_forks"].round(2)
    return stats_df


def plot_metric_by_year(
    stats_df: pd.DataFrame,
    metric: str,
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    """Create a line chart for one metric over years."""
    if stats_df.empty:
        print(f"Skipping chart {output_path.name}: no data available.")
        return

    plt.figure(figsize=(12, 7))

    for language in stats_df["language"].unique():
        language_data = stats_df[stats_df["language"] == language]
        plt.plot(
            language_data["created_year"],
            language_data[metric],
            marker="o",
            linewidth=2,
            label=language,
        )

    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel(ylabel)
    plt.xticks(sorted(stats_df["created_year"].unique()), rotation=45)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_total_bar_chart(
    totals_df: pd.DataFrame,
    metric: str,
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    """Create a bar chart that compares languages by total metric."""
    if totals_df.empty:
        print(f"Skipping chart {output_path.name}: no data available.")
        return

    plt.figure(figsize=(10, 6))
    plt.bar(totals_df["language"], totals_df[metric], color="steelblue")
    plt.title(title)
    plt.xlabel("Programming language")
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def create_visualizations(stats_df: pd.DataFrame) -> None:
    """Build and save all required charts."""
    plot_metric_by_year(
        stats_df,
        metric="repositories_count",
        title="Repositories by Year",
        ylabel="Number of repositories",
        output_path=IMAGES_DIR / "repositories_by_year.png",
    )
    plot_metric_by_year(
        stats_df,
        metric="total_stars",
        title="Total Stars by Year",
        ylabel="Total stars",
        output_path=IMAGES_DIR / "stars_by_year.png",
    )
    plot_metric_by_year(
        stats_df,
        metric="average_stars",
        title="Average Stars by Year",
        ylabel="Average stars",
        output_path=IMAGES_DIR / "average_stars_by_year.png",
    )

    totals_df = (
        stats_df.groupby("language", as_index=False)
        .agg(
            total_repositories=("repositories_count", "sum"),
            total_stars=("total_stars", "sum"),
        )
        .sort_values("total_repositories", ascending=False)
    )

    plot_total_bar_chart(
        totals_df,
        metric="total_repositories",
        title="Total Repositories by Language",
        ylabel="Repositories",
        output_path=IMAGES_DIR / "total_repositories_by_language.png",
    )
    plot_total_bar_chart(
        totals_df.sort_values("total_stars", ascending=False),
        metric="total_stars",
        title="Total Stars by Language",
        ylabel="Stars",
        output_path=IMAGES_DIR / "total_stars_by_language.png",
    )


def print_conclusions(stats_df: pd.DataFrame) -> None:
    """Print short text conclusions based on aggregated data."""
    print("\nConclusions:")

    if stats_df.empty:
        print("No data was collected, so conclusions cannot be generated.")
        print("- Possible reasons: API errors, rate limits, or network problems.")
        return

    totals_df = (
        stats_df.groupby("language", as_index=False)
        .agg(
            total_repositories=("repositories_count", "sum"),
            total_stars=("total_stars", "sum"),
            mean_average_stars=("average_stars", "mean"),
        )
    )

    most_common_language = totals_df.loc[
        totals_df["total_repositories"].idxmax(), "language"
    ]
    most_starred_language = totals_df.loc[totals_df["total_stars"].idxmax(), "language"]
    highest_average_stars_language = totals_df.loc[
        totals_df["mean_average_stars"].idxmax(), "language"
    ]

    print(f"- Most frequent language in the sample: {most_common_language}.")
    print(f"- Language with the highest total stars: {most_starred_language}.")
    print(
        "- Language with the highest average stars per repository: "
        f"{highest_average_stars_language}."
    )

    growth_languages: list[str] = []
    for language in stats_df["language"].unique():
        language_data = stats_df[stats_df["language"] == language].sort_values(
            "created_year"
        )
        if len(language_data) >= 2:
            first_value = language_data.iloc[0]["repositories_count"]
            last_value = language_data.iloc[-1]["repositories_count"]
            if last_value > first_value:
                growth_languages.append(language)

    if growth_languages:
        print(
            "- Languages that show growth in repository count in the sample: "
            + ", ".join(growth_languages)
            + "."
        )
    else:
        print("- Clear growth by repository count was not detected in the sample.")

    print("- Analysis limitations:")
    print("  1. The study uses a sample, not the entire GitHub platform.")
    print("  2. Only the first page of Search API results is used for each language and year.")
    print("  3. Only public repositories are included.")
    print("  4. Stars reflect attention, but not necessarily real usage.")
    print("  5. Older repositories had more time to accumulate stars.")


def main() -> None:
    """Run the full data collection and analysis pipeline."""
    load_dotenv()
    ensure_directories()

    token = os.getenv("GITHUB_TOKEN")
    session = create_session(token)

    repositories_df = collect_data(DEFAULT_LANGUAGES, DEFAULT_YEARS, session)
    repositories_df.to_csv(RAW_DATA_PATH, index=False, encoding="utf-8")
    print(f"Raw data saved to: {RAW_DATA_PATH}")

    stats_df = aggregate_data(repositories_df)
    stats_df.to_csv(STATS_DATA_PATH, index=False, encoding="utf-8")
    print(f"Aggregated data saved to: {STATS_DATA_PATH}")

    create_visualizations(stats_df)
    print(f"Charts saved to: {IMAGES_DIR}")

    print_conclusions(stats_df)


if __name__ == "__main__":
    main()
