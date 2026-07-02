import re

PRIORITY_CITIES = [
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск",
    "Казань", "Нижний Новгород", "Челябинск", "Самара", "Уфа",
    "Ростов-на-Дону", "Тюмень", "Краснодар", "Пермь", "Воронеж", "Омск",
]

def normalize_city(raw: str) -> str:
    raw = raw.strip()
    import re
    raw = re.sub(r"\s+", " ", raw)
    return raw.title()
