-- Эталонные SQL-определения основных витрин NEXUS (совместимо с SQLite).
WITH active_days AS (
  SELECT DATE(event_at) AS activity_date, user_id
  FROM events
  WHERE event_name IN ('project_created', 'task_created', 'meaningful_action')
  GROUP BY 1, 2
)
SELECT activity_date, COUNT(DISTINCT user_id) AS dau
FROM active_days
GROUP BY activity_date
ORDER BY activity_date;

-- Параметр :report_date передаётся безопасно через привязку, а не конкатенацию.
SELECT COUNT(DISTINCT user_id) AS mau
FROM active_days
WHERE activity_date BETWEEN DATE(:report_date, '-29 day') AND DATE(:report_date);
