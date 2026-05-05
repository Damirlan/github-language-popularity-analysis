from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INPUT_HTML_PATH = DATA_DIR / "pypl_table.html"
OUTPUT_CSV_PATH = DATA_DIR / "pypl_reference.csv"


def clean_percent(value: object) -> float:
    if value is None:
        return 0.0

    text = str(value).strip()
    if not text or text == "0":
        return 0.0

    if text.endswith("%"):
        text = text[:-1]

    return float(text)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if not INPUT_HTML_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_HTML_PATH}\n"
            "Save the copied PYPL HTML table into this file and run the script again."
        )

    tables = pd.read_html(INPUT_HTML_PATH)
    if not tables:
        raise ValueError("No HTML tables were found in the input file.")

    df = tables[0].copy()
    df.columns = [str(column).strip() for column in df.columns]

    expected_columns = ["Date", "Go", "Java", "JavaScript", "Kotlin", "Python", "Rust"]
    missing_columns = [column for column in expected_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "The imported table is missing expected columns: "
            + ", ".join(missing_columns)
        )

    df = df[expected_columns].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).reset_index(drop=True)

    for column in expected_columns[1:]:
        df[column] = df[column].apply(clean_percent)

    df = df.rename(columns={"Date": "date"})
    df = df.sort_values("date").reset_index(drop=True)

    # The copied PYPL table may contain duplicated month rows; keep the last one.
    df = df.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8")

    print(f"Saved PYPL reference data to: {OUTPUT_CSV_PATH}")
    print(f"Rows saved: {len(df)}")
    print(df.head())
    print(df.tail())


if __name__ == "__main__":
    main()
