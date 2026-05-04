# PYPL-like анализ популярности языков программирования через Yandex Wordstat

## Цель
Провести исследование динамики популярности языков программирования по методологии, максимально близкой к PYPL, но на основе данных Yandex Wordstat.

## Идея исследования
Официальный индекс PYPL оценивает популярность языков программирования по тому, как часто пользователи ищут запросы вида `"<language> tutorial"` в Google Trends. В этом проекте используется аналогичный подход, но вместо Google Trends применяется Yandex Wordstat.

Для каждого языка берется единая обучающая поисковая фраза. Затем рассчитывается:
- помесячное число запросов;
- относительный интерес к каждому языку по сравнению с Java;
- доля интереса среди выбранных языков;
- сглаженная доля интереса по 6-месячному окну;
- оценка годового тренда по последним 12 месяцам.

## Языки исследования
- Python
- JavaScript
- Java
- Go
- Rust
- Kotlin

## Используемые запросы
- `python tutorial`
- `javascript tutorial`
- `java tutorial`
- `golang tutorial`
- `rust tutorial`
- `kotlin tutorial`

Для Go используется `golang tutorial`, чтобы уменьшить неоднозначность слова `go`.

## Методология
Исследование повторяет ключевую идею PYPL:
1. Для каждого языка берется tutorial-запрос.
2. Для каждого месяца собирается частота запросов.
3. Для каждого месяца считается отношение частоты языка к частоте `java tutorial`.
4. Эти относительные значения нормализуются до 100%.
5. Полученная доля интереса сглаживается 6-месячным средним.
6. Тренд оценивается по сглаженному ряду за последние 12 месяцев.

## Источник данных
Используется официальный Wordstat API в составе Yandex Cloud Search API:

- `https://searchapi.api.cloud.yandex.net/v2/wordstat/dynamics`

Данные собираются с периодом `PERIOD_MONTHLY`.

## Ограничения
1. Это не официальный индекс PYPL, а PYPL-like исследование.
2. Источник данных отличается: используется Yandex Wordstat, а не Google Trends.
3. По документации Wordstat API месячные данные доступны с `2018-01-01`.
4. Итог зависит от выбора поисковой фразы.
5. Поисковый интерес не равен реальному использованию языка в production.
6. Для доступа нужны `folderId`, роль `search-api.webSearch.user` и IAM token или API key Yandex Cloud.

## Структура проекта
```text
github-language-popularity-analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── .env
├── load_wordstat.py
├── main.py
├── program.ipynb
├── teacher_email.txt
├── data/
│   ├── .gitkeep
│   ├── wordstat_dynamics_raw.csv
│   ├── wordstat_monthly_index.csv
│   └── wordstat_latest_ranking.csv
└── images/
    ├── .gitkeep
    ├── wordstat_raw_counts_by_month.png
    ├── wordstat_share_by_month.png
    ├── wordstat_smoothed_share_by_month.png
    ├── wordstat_latest_share.png
    └── wordstat_yearly_trend.png
```

## Как запустить проект
1. Установить зависимости:

```bash
pip install -r requirements.txt
```

2. Заполнить `.env`:

```env
YANDEX_SEARCH_API_TOKEN=your_iam_token_or_api_key
YANDEX_SEARCH_API_AUTH_TYPE=bearer
YANDEX_SEARCH_API_FOLDER_ID=your_folder_id
```

Где:
- `YANDEX_SEARCH_API_TOKEN` - IAM token или API key Yandex Cloud Search API;
- `YANDEX_SEARCH_API_AUTH_TYPE` - `bearer` для IAM token или `api-key` для API key;
- `YANDEX_SEARCH_API_FOLDER_ID` - идентификатор папки Yandex Cloud, в которой подключен Search API.

3. Загрузить сырые данные:

```bash
python load_wordstat.py
```

4. Рассчитать индекс и построить графики:

```bash
python main.py
```

5. Открыть `program.ipynb` и выполнить ячейки анализа.

## Какие файлы создаются
После запуска `load_wordstat.py`:
- `data/wordstat_dynamics_raw.csv`

После запуска `main.py`:
- `data/wordstat_monthly_index.csv`
- `data/wordstat_latest_ranking.csv`
- графики в папке `images/`

## Что показывает анализ
- динамику абсолютного числа tutorial-запросов по языкам;
- долю языка в общем интересе к выбранным языкам;
- сглаженную динамику долей;
- распределение долей в последнем месяце;
- оценку годового тренда.

## Вывод
Проект показывает, как можно воспроизвести логику PYPL на другом источнике данных. Результат не заменяет официальный PYPL, но позволяет получить сопоставимое учебное исследование о динамике интереса к языкам программирования в поисковой системе Yandex.
