from pathlib import Path


def test_interface_is_declared_as_russian():
    html = Path("site/index.html").read_text(encoding="utf-8")
    assert '<html lang="ru">' in html
    assert "Демонстрационный режим" in html
    assert "синтетических данных" in html


def test_all_required_sections_are_present():
    html = Path("site/index.html").read_text(encoding="utf-8")
    required = ("Обзор", "Привлечение", "Воронка", "Удержание", "Когорты", "Выручка", "Функции", "Эксперименты", "Качество данных", "Методология", "Безопасность")
    assert all(section in html for section in required)


def test_safe_user_states_are_russian():
    source = Path("site/assets/app.js").read_text(encoding="utf-8")
    required = ("Нет данных", "Загрузка аналитики", "Повторите попытку позже", "причинно-следственную связь")
    assert all(text in source for text in required)
