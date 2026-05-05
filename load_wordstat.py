from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "wordstat_dynamics_raw.csv"
PYPL_REFERENCE_PATH = DATA_DIR / "pypl_reference.csv"

WORDSTAT_DYNAMICS_URL = "https://searchapi.api.cloud.yandex.net/v2/wordstat/dynamics"
REQUEST_TIMEOUT = 30
REQUEST_PAUSE_SECONDS = 1
START_DATE = "2018-01-01"

# Phrases are aligned to the language names imported from the PYPL table.
PHRASE_OVERRIDES = {
    "Abap": "abap tutorial",
    "Ada": "ada tutorial",
    "C/C++": "c++ tutorial",
    "C#": "c# tutorial",
    "Cobol": "cobol tutorial",
    "Dart": "dart tutorial",
    "Delphi/Pascal": "delphi tutorial",
    "Go": "golang tutorial",
    "Groovy": "groovy tutorial",
    "Haskell": "haskell tutorial",
    "Java": "java tutorial",
    "JavaScript": "javascript tutorial",
    "Julia": "julia tutorial",
    "Kotlin": "kotlin tutorial",
    "Lua": "lua tutorial",
    "Matlab": "matlab tutorial",
    "Objective-C": "objective-c tutorial",
    "Perl": "perl tutorial",
    "PHP": "php tutorial",
    "Powershell": "powershell tutorial",
    "Python": "python tutorial",
    "R": "r language tutorial",
    "Ruby": "ruby tutorial",
    "Rust": "rust tutorial",
    "Scala": "scala tutorial",
    "Swift": "swift tutorial",
    "TypeScript": "typescript tutorial",
    "VBA": "vba tutorial",
    "Visual Basic": "visual basic tutorial",
    "Zig": "zig tutorial",
}


def last_day_of_previous_month() -> str:
    today = date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_previous_month = first_day_of_current_month - pd.Timedelta(days=1)
    return last_day_previous_month.strftime("%Y-%m-%d")


def to_rfc3339(date_string: str, end_of_day: bool = False) -> str:
    suffix = "T23:59:59Z" if end_of_day else "T00:00:00Z"
    return f"{date_string}{suffix}"


def build_phrase(language: str) -> str:
    if language in PHRASE_OVERRIDES:
        return PHRASE_OVERRIDES[language]
    return f"{language.lower()} tutorial"


def load_languages_from_pypl() -> list[str]:
    if not PYPL_REFERENCE_PATH.exists():
        raise FileNotFoundError(
            f"PYPL reference file not found: {PYPL_REFERENCE_PATH}. "
            "Run `python import_pypl_table.py` first."
        )

    pypl_df = pd.read_csv(PYPL_REFERENCE_PATH)
    languages = [column for column in pypl_df.columns if column != "date"]
    if not languages:
        raise ValueError("No languages were found in pypl_reference.csv.")
    return languages


def create_session(token: str, auth_type: str) -> requests.Session:
    session = requests.Session()
    authorization_value = f"Api-Key {token}" if auth_type == "api-key" else f"Bearer {token}"
    session.headers.update(
        {
            "Authorization": authorization_value,
            "Content-Type": "application/json;charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "wordstat-pypl-like-analysis",
        }
    )
    return session


def fetch_phrase_dynamics(
    session: requests.Session,
    language: str,
    phrase: str,
    from_date: str,
    to_date: str,
    folder_id: str,
) -> list[dict]:
    payload = {
        "phrase": phrase,
        "period": "PERIOD_MONTHLY",
        "fromDate": to_rfc3339(from_date),
        "toDate": to_rfc3339(to_date, end_of_day=True),
        "devices": ["DEVICE_ALL"],
        "folderId": folder_id,
    }

    print(f"Requesting monthly dynamics for {language}: {phrase}")

    try:
        response = session.post(
            WORDSTAT_DYNAMICS_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        print(f"Request failed for {language}: {error}")
        return []

    if response.status_code == 429:
        print(f"Quota limit exceeded for {language}: {response.text}")
        return []

    if response.status_code == 503:
        print("Service quota exceeded temporarily. Try again later.")
        return []

    if response.status_code != 200:
        print(f"Wordstat API error for {language}: {response.status_code}")
        print("Response headers:", dict(response.headers))
        print("Response body:", response.text[:2000])
        return []

    try:
        payload = response.json()
    except ValueError:
        print(f"Invalid JSON for {language}.")
        return []

    rows: list[dict] = []
    for item in payload.get("results", []):
        rows.append(
            {
                "language": language,
                "phrase": phrase,
                "date": item.get("date"),
                "count": item.get("count", 0),
                "share": item.get("share", 0),
                "period": "monthly",
                "from_date": from_date,
                "to_date": to_date,
                "devices": "all",
            }
        )

    return rows


def main() -> None:
    load_dotenv()
    DATA_DIR.mkdir(exist_ok=True)

    token = os.getenv("YANDEX_SEARCH_API_TOKEN") or os.getenv("YANDEX_WORDSTAT_TOKEN")
    auth_type = (os.getenv("YANDEX_SEARCH_API_AUTH_TYPE") or "bearer").strip().lower()
    folder_id = os.getenv("YANDEX_SEARCH_API_FOLDER_ID")

    if not token:
        raise ValueError(
            "Missing token in .env. Use YANDEX_SEARCH_API_TOKEN or YANDEX_WORDSTAT_TOKEN."
        )

    if auth_type not in {"bearer", "api-key"}:
        raise ValueError("YANDEX_SEARCH_API_AUTH_TYPE must be 'bearer' or 'api-key'.")

    if not folder_id:
        raise ValueError("YANDEX_SEARCH_API_FOLDER_ID is missing in .env")

    languages = load_languages_from_pypl()
    phrases = {language: build_phrase(language) for language in languages}

    session = create_session(token, auth_type)
    to_date = last_day_of_previous_month()

    all_rows: list[dict] = []
    for language, phrase in phrases.items():
        rows = fetch_phrase_dynamics(session, language, phrase, START_DATE, to_date, folder_id)
        all_rows.extend(rows)
        print(f"Collected {len(rows)} monthly points for {language}.")
        time.sleep(REQUEST_PAUSE_SECONDS)

    raw_df = pd.DataFrame(all_rows)
    raw_df.to_csv(RAW_DATA_PATH, index=False, encoding="utf-8")

    print(f"\nSaved raw Wordstat dynamics to: {RAW_DATA_PATH}")
    print(f"Languages requested: {len(languages)}")
    print(f"Total rows collected: {len(raw_df)}")


if __name__ == "__main__":
    main()
