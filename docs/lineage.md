# Происхождение данных

| Метрика | Источник | Преобразование | Витрина | Раздел |
|---|---|---|---|---|
| DAU/WAU/MAU | `events.csv` | Белый список содержательных событий, уникальные пользователи, календарные окна | `overview.json` | Обзор |
| Активация | `users.csv`, `events.csv` | Проект → задача не позже 7 дней | `overview.json`, `funnel.json` | Обзор, Воронка |
| Удержание | `users.csv`, `events.csv` | Когорта регистрации и активность ровно в день N | `overview.json` | Удержание |
| Выручка | `payments.csv`, `subscriptions.csv` | Сумма платежей, возвратов и активных месячных сумм | `overview.json` | Выручка |
| CAC | `marketing_spend.csv`, `payments.csv` | Расходы / новые платящие | `overview.json` | Выручка |
| Эксперимент | `experiment_assignments.csv`, `events.csv` | Конверсии групп, z-тест, интервал | `experiment.json` | Эксперименты |
