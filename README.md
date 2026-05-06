# PYPL-like анализ популярности языков программирования через Yandex Wordstat

## Цель
Провести исследование динамики популярности языков программирования по методологии, максимально близкой к проекту `PYPL`, но на основе данных `Yandex Wordstat`.

## Идея исследования
Проект `PYPL` оценивает популярность языков программирования по тому, как часто пользователи ищут запросы вида `"<language> tutorial"` в `Google Trends`. В этой работе используется аналогичный подход, но вместо `Google Trends` применяется `Yandex Wordstat`.

На основе этих данных рассчитываются:
- помесячное число tutorial-запросов;
- относительный интерес к каждому языку по сравнению с `Java`;
- доля интереса среди всех рассматриваемых языков;
- сглаженная доля интереса по 6-месячному окну;
- годовой тренд по последним 12 месяцам.

## Языки исследования
В итоговой версии исследования используются все языки, которые были импортированы из таблицы проекта `PYPL`.

На момент подготовки проекта в список входят:
- `Abap`
- `Ada`
- `C/C++`
- `C#`
- `Cobol`
- `Dart`
- `Delphi/Pascal`
- `Go`
- `Groovy`
- `Haskell`
- `Java`
- `JavaScript`
- `Julia`
- `Kotlin`
- `Lua`
- `Matlab`
- `Objective-C`
- `Perl`
- `PHP`
- `Powershell`
- `Python`
- `R`
- `Ruby`
- `Rust`
- `Scala`
- `Swift`
- `TypeScript`
- `VBA`
- `Visual Basic`
- `Zig`

## Используемые запросы
Для каждого языка формируется tutorial-запрос. Для неоднозначных названий используются специальные фразы, например:
- `golang tutorial` для `Go`
- `c++ tutorial` для `C/C++`
- `c# tutorial` для `C#`
- `objective-c tutorial` для `Objective-C`
- `r language tutorial` для `R`
- `visual basic tutorial` для `Visual Basic`

Фразы задаются в [load_wordstat.py](/Users/damirhanov/PycharmProjects/github-language-trends-analyzer/load_wordstat.py:1).

## Методология
Исследование повторяет ключевую идею проекта `PYPL`:
1. Для каждого языка берется tutorial-запрос.
2. Для каждого месяца собирается частота запросов.
3. Для каждого месяца считается отношение частоты языка к частоте `java tutorial`.
4. Эти относительные значения нормализуются до 100%.
5. Полученная доля интереса сглаживается 6-месячным средним.
6. Тренд оценивается по сглаженному ряду за последние 12 месяцев.

## Источник данных
Используется официальный `Wordstat API` в составе `Yandex Cloud Search API`:

- `https://searchapi.api.cloud.yandex.net/v2/wordstat/dynamics`

Данные собираются с периодом `PERIOD_MONTHLY`.

## Ограничения
1. Это не индекс `PYPL`, а отдельное `PYPL-like` исследование по аналогичной методологии.
2. Источник данных отличается: используется `Yandex Wordstat`, а не `Google Trends`.
3. По документации `Wordstat API` месячные данные доступны с `2018-01-01`.
4. Итог зависит от выбора поисковой фразы.
5. Поисковый интерес не равен реальному использованию языка в production.
6. Для доступа нужны `folderId`, роль `search-api.webSearch.user` и `IAM token` или `API key` Yandex Cloud.

## Структура проекта
```text
github-language-popularity-analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── .env
├── import_pypl_table.py
├── load_wordstat.py
├── main.py
├── program.ipynb
├── teacher_email.txt
├── data/
│   ├── pypl_table.html
│   ├── pypl_reference.csv
│   ├── wordstat_dynamics_raw.csv
│   ├── wordstat_monthly_index.csv
│   ├── wordstat_latest_ranking.csv
│   ├── wordstat_top10_promising_languages.csv
│   └── wordstat_pypl_style_table.csv
└── images/
    ├── wordstat_raw_counts_top_1_5.png
    ├── wordstat_raw_counts_top_6_10.png
    ├── wordstat_smoothed_share_top_1_5.png
    ├── wordstat_smoothed_share_top_6_10.png
    ├── wordstat_latest_share_top10.png
    ├── wordstat_yearly_trend_top10.png
    ├── wordstat_pypl_style_table.png
    └── wordstat_vs_pypl_top10.png
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
- `YANDEX_SEARCH_API_TOKEN` — `IAM token` или `API key` `Yandex Cloud Search API`;
- `YANDEX_SEARCH_API_AUTH_TYPE` — `bearer` для `IAM token` или `api-key` для `API key`;
- `YANDEX_SEARCH_API_FOLDER_ID` — идентификатор папки `Yandex Cloud`, в которой подключен `Search API`.

3. Сохранить HTML-таблицу проекта `PYPL` в файл:

```text
data/pypl_table.html
```

4. Импортировать таблицу `PYPL` в CSV:

```bash
python import_pypl_table.py
```

5. Загрузить сырые данные `Wordstat`:

```bash
python load_wordstat.py
```

6. Рассчитать индекс и построить графики:

```bash
python main.py
```

7. Открыть `program.ipynb` и выполнить ячейки анализа.

## Какие файлы создаются
После запуска `import_pypl_table.py`:
- `data/pypl_reference.csv`

После запуска `load_wordstat.py`:
- `data/wordstat_dynamics_raw.csv`

После запуска `main.py`:
- `data/wordstat_monthly_index.csv`
- `data/wordstat_latest_ranking.csv`
- `data/wordstat_top10_promising_languages.csv`
- `data/wordstat_pypl_style_table.csv`
- графики в папке `images/`

## Принцип отбора языков для графиков
Все расчеты в исследовании выполняются по полному набору языков, импортированных из таблицы проекта `PYPL`.

Однако для визуализации используется только `top-10` наиболее перспективных языков. Перспективность определяется по показателю:

- `yearly_trend_pp`

Это годовой тренд сглаженной доли интереса. Чем выше этот показатель, тем более перспективным считается язык.

Чтобы графики не были перегружены, на одном графике отображается не более 5 языков:
- график 1: места `1–5`;
- график 2: места `6–10`.

## Что показывает анализ
Исследование позволяет:
- оценить динамику абсолютного числа tutorial-запросов по всем языкам;
- рассчитать относительную долю интереса по всем языкам;
- определить языки с самым сильным положительным трендом;
- построить итоговую таблицу в формате, близком к таблице проекта `PYPL`;
- сравнить полученный `PYPL-like` индекс с данными проекта `PYPL`;
- сопоставить не только графики, но и численные метрики сходства.

## PYPL-подобная итоговая таблица
В проекте дополнительно строится таблица в стиле `PYPL`, которая сохраняется в двух видах:
- `data/wordstat_pypl_style_table.csv`
- `images/wordstat_pypl_style_table.png`

Эта таблица содержит:
- `Rank` — текущее место языка по доле интереса;
- `Change` — изменение места языка по сравнению с той же точкой год назад;
- `Language` — название языка;
- `Share` — доля интереса в последнем месяце;
- `1-year trend` — изменение доли интереса за год в процентных пунктах.

Таким образом, помимо графиков, проект предоставляет компактную итоговую таблицу, напрямую сопоставимую по структуре с таблицей проекта `PYPL`.

Текущая PYPL-подобная таблица по данным Wordstat:

| Rank | Change | Language | Share | 1-year trend |
|---:|---:|---|---:|---:|
| 1 | 0 | Python | 29.48 % | -22.5 % |
| 2 | 0 | C/C++ | 27.51 % | +9.5 % |
| 3 | 0 | Java | 13.01 % | +5.4 % |
| 4 | 0 | PHP | 8.21 % | +3.0 % |
| 5 | 5 | Go | 5.20 % | +3.8 % |
| 6 | -1 | Rust | 4.51 % | -0.1 % |
| 7 | 7 | Ruby | 3.53 % | +3.0 % |
| 8 | 1 | JavaScript | 2.14 % | +0.7 % |
| 9 | -2 | Kotlin | 2.02 % | +0.4 % |
| 10 | -4 | Lua | 1.68 % | -0.6 % |
| 11 | -3 | Swift | 1.04 % | -0.6 % |
| 12 | 3 | VBA | 0.64 % | +0.2 % |
| 13 | 3 | Powershell | 0.58 % | +0.3 % |
| 14 | -3 | TypeScript | 0.46 % | -0.4 % |
| 15 | 3 | Scala | 0.00 % | -0.2 % |
| 16 | 5 | R | 0.00 % | +0.0 % |
| 17 | 2 | Visual Basic | 0.00 % | -0.1 % |
| 18 | 4 | Abap | 0.00 % | +0.0 % |
| 19 | -6 | Matlab | 0.00 % | -0.6 % |
| 20 | 3 | Perl | 0.00 % | +0.0 % |
| 21 | 3 | Objective-C | 0.00 % | +0.0 % |
| 22 | 3 | Ada | 0.00 % | +0.0 % |
| 23 | -3 | Julia | 0.00 % | -0.1 % |
| 24 | 2 | Haskell | 0.00 % | +0.0 % |
| 25 | -8 | Groovy | 0.00 % | -0.3 % |
| 26 | 1 | Delphi/Pascal | 0.00 % | +0.0 % |
| 27 | -15 | Dart | 0.00 % | -0.7 % |
| 28 | 0 | Cobol | 0.00 % | +0.0 % |
| 29 | 0 | C# | 0.00 % | +0.0 % |
| 30 | 0 | Zig | 0.00 % | +0.0 % |

Версия этой же таблицы как изображение:

![PYPL-style table](images/wordstat_pypl_style_table.png)

## Сравнение с проектом PYPL
Для сравнения с проектом `PYPL` в проект был добавлен эталонный файл `data/pypl_reference.csv`, а в ноутбуке реализовано:
- сопоставление графиков `Wordstat` и `PYPL` рядом;
- сравнение в логарифмической шкале;
- численные метрики сходства по языкам;
- сравнение рангов языков по месяцам.

Сравнение выполняется по всему пересечению языков между:
- `wordstat_monthly_index.csv`
- `pypl_reference.csv`

При этом визуализация ограничивается только `top-10` наиболее перспективных языков, чтобы графики оставались читаемыми.

Сравнительный график из 9 пункта ноутбука:

![Wordstat vs PYPL top-10 comparison](images/wordstat_vs_pypl_top10.png)

## Вывод
Проект показывает, как можно воспроизвести логику проекта `PYPL` на другом источнике данных. Полученный результат не является самим `PYPL`, но позволяет провести сопоставимое учебное исследование о динамике интереса к языкам программирования в поисковой системе `Yandex`. В итоговой версии исследования все расчеты выполняются по полному набору языков из таблицы `PYPL`, а графики строятся только для `top-10` наиболее перспективных языков по годовому тренду.
