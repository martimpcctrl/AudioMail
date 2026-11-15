"""Busca e cache local de feriados nacionais pelo endpoint publico Nager.Date."""
import json
import os
import urllib.request

from common import data_dir


API_URL = "https://nagerholidays.com/api/v4/Holidays/BR/%d"


def cached_holidays(year):
    path = os.path.join(data_dir(), "feriados_BR_%s.json" % int(year))
    try:
        with open(path, "r", encoding="utf-8") as cache_file:
            holidays = json.load(cache_file)
        return holidays if isinstance(holidays, list) else []
    except (OSError, ValueError):
        return []


def fetch_holidays(year):
    """Busca os feriados nacionais brasileiros e os conserva para uso sem internet."""
    request = urllib.request.Request(
        API_URL % int(year), headers={"User-Agent": "AudioMail/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("Resposta inesperada da API de feriados")
    holidays = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not item.get("nationalHoliday") and item.get("subdivisionCodes"):
            continue
        date, name = item.get("date"), item.get("localName") or item.get("name")
        if date and name:
            holidays.append({"date": date, "name": name,
                             "types": item.get("holidayTypes") or ["Public"]})
    path = os.path.join(data_dir(), "feriados_BR_%s.json" % int(year))
    with open(path, "w", encoding="utf-8") as cache_file:
        json.dump(holidays, cache_file, ensure_ascii=False, indent=2)
    return holidays
