# Словарь данных

Все идентификаторы — синтетические UUID. Пустое значение допустимо только там, где это указано.

| Таблица | Ключевые поля | Ограничения и смысл |
|---|---|---|
| `users` | `user_id` UUID, `registered_at` date, `channel`, `segment`, `country` | `user_id` — первичный ключ; канал и сегмент из белого списка; поля обязательны. |
| `events` | `event_id` UUID, `user_id` UUID, `event_name`, `event_at` datetime, `feature_name` | Внешний ключ на пользователя; имя события из перечисления; функция может быть пустой. |
| `subscriptions` | `subscription_id`, `user_id`, `plan`, `started_at`, `ended_at`, `monthly_amount`, `status` | Дата окончания nullable; сумма неотрицательна; статус «Активна» или «Отменена». |
| `payments` | `payment_id`, `subscription_id`, `user_id`, `paid_at`, `gross_amount`, `refund_amount`, `currency`, `status` | Возврат от 0 до суммы платежа; валюта RUB; внешние ключи обязательны. |
| `marketing_spend` | `spend_id`, `month`, `channel`, `amount`, `currency` | Расход неотрицателен; месяц `YYYY-MM`; канал из белого списка. |
| `experiment_assignments` | `experiment_id`, `user_id`, `variant`, `assigned_at` | Один пользователь относится к одной группе эксперимента; варианты — контрольная или тестовая группа. |
