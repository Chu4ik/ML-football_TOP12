"""
football_data_collector.py — збір архіву з football-data.co.uk

Джерело: https://www.football-data.co.uk
Дані: результати + Pinnacle odds + базова статистика
Покриття: АПЛ, Чемпіонат, Ла Ліга, Сегунда, Бундесліга, 2.Бундесліга,
          Серія А/Б, Ліга 1/2, Ередивізі, Ліга A, Португалія 1/2

Запуск:
    pip install requests
    python football_data_collector.py              # всі ліги, 5 сезонів
    python football_data_collector.py --test       # тест: АПЛ 2023-24
    python football_data_collector.py --league E0  # тільки АПЛ
"""

import csv
import json
import time
import argparse
import requests
from io import StringIO
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────
# Конфіг
# ──────────────────────────────────────────────────────────────

BASE_URL = "https://www.football-data.co.uk/mmz4281"

# Сезони у форматі football-data.co.uk (останні 5 + поточний)
SEASONS = [
    ("2021-2022", "2122"),
    ("2022-2023", "2223"),
    ("2023-2024", "2324"),
    ("2024-2025", "2425"),
]

# Ліги: код → (назва, країна)
LEAGUES = {
    "E0":  ("Прем'єр-ліга",     "АНГЛІЯ"),
    "E1":  ("Чемпіонат",         "АНГЛІЯ"),
    "SP1": ("Ла Ліга",           "ІСПАНІЯ"),
    "SP2": ("Сегунда",           "ІСПАНІЯ"),
    "D1":  ("Бундесліга",        "НІМЕЧЧИНА"),
    "D2":  ("2. Бундесліга",     "НІМЕЧЧИНА"),
    "I1":  ("Серія А",           "ІТАЛІЯ"),
    "I2":  ("Серія Б",           "ІТАЛІЯ"),
    "F1":  ("Ліга 1",            "ФРАНЦІЯ"),
    "F2":  ("Ліга 2",            "ФРАНЦІЯ"),
    "N1":  ("Ередивізі",         "НІДЕРЛАНДИ"),
    "B1":  ("Ліга A",            "БЕЛЬГІЯ"),
    "P1":  ("Ліга Португалії",   "ПОРТУГАЛІЯ"),
    "P2":  ("Ліга Португалії 2", "ПОРТУГАЛІЯ"),
}

# ──────────────────────────────────────────────────────────────
# Маппінг колонок
# ──────────────────────────────────────────────────────────────

def parse_row(row: dict, league_code: str, season: str) -> dict | None:
    """
    Перетворює рядок CSV у стандартний формат.

    Ключові колонки football-data.co.uk:
      Date/Time   — дата і час матчу
      HomeTeam    — хазяї
      AwayTeam    — гості
      FTHG/FTAG   — рахунок (Full Time Home/Away Goals)
      HTHG/HTAG   — рахунок 1-го тайму
      FTR         — результат (H/D/A)
      HS/AS       — удари
      HST/AST     — удари в площину
      HC/AC       — кутові
      HY/AY       — жовті картки
      HR/AR       — червоні картки
      PSH/PSD/PSA — Pinnacle closing 1X2
      P>2.5/P<2.5 — Pinnacle тотал 2.5
      PCAHH/PCAHA — Pinnacle азіатський гандикап
      B365H/D/A   — Bet365 1X2 (додатково)
    """
    home = row.get("HomeTeam", "").strip()
    away = row.get("AwayTeam", "").strip()
    if not home or not away:
        return None

    # Парсимо дату
    date_str = row.get("Date", "").strip()
    time_str = row.get("Time", "").strip()
    match_time = ""
    if date_str:
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                if time_str:
                    try:
                        t = datetime.strptime(time_str, "%H:%M")
                        dt = dt.replace(hour=t.hour, minute=t.minute)
                    except ValueError:
                        pass
                match_time = dt.strftime("%Y-%m-%d %H:%M")
                break
            except ValueError:
                continue

    def safe_float(val):
        try:
            v = float(str(val).strip())
            return v if v > 0 else None
        except (ValueError, TypeError):
            return None

    def safe_int(val):
        try:
            v = int(str(val).strip())
            return v
        except (ValueError, TypeError):
            return None

    league_name, country = LEAGUES.get(league_code, (league_code, "Unknown"))

    return {
        # Ідентифікатори
        "source":          "football-data.co.uk",
        "league_code":     league_code,
        "league":          league_name,
        "country":         country,
        "season":          season,

        # Матч
        "time_utc":        match_time,
        "home_team":       home,
        "away_team":       away,

        # Рахунок
        "score_home":      safe_int(row.get("FTHG")),
        "score_away":      safe_int(row.get("FTAG")),
        "score_ht_home":   safe_int(row.get("HTHG")),
        "score_ht_away":   safe_int(row.get("HTAG")),
        "result":          row.get("FTR", "").strip(),  # H/D/A

        # Статистика матчу
        "home_shots":      safe_int(row.get("HS")),
        "away_shots":      safe_int(row.get("AS")),
        "home_shots_ot":   safe_int(row.get("HST")),
        "away_shots_ot":   safe_int(row.get("AST")),
        "home_corners":    safe_int(row.get("HC")),
        "away_corners":    safe_int(row.get("AC")),
        "home_fouls":      safe_int(row.get("HF")),
        "away_fouls":      safe_int(row.get("AF")),
        "home_yellow":     safe_int(row.get("HY")),
        "away_yellow":     safe_int(row.get("AY")),
        "home_red":        safe_int(row.get("HR")),
        "away_red":        safe_int(row.get("AR")),
        "referee":         row.get("Referee", "").strip(),

        # Pinnacle closing 1X2
        "pinnacle_home":   safe_float(row.get("PSH") or row.get("PSCH")),
        "pinnacle_draw":   safe_float(row.get("PSD") or row.get("PSCD")),
        "pinnacle_away":   safe_float(row.get("PSA") or row.get("PSCA")),

        # Pinnacle тотал 2.5
        "pinnacle_over25": safe_float(row.get("P>2.5") or row.get("PC>2.5")),
        "pinnacle_under25":safe_float(row.get("P<2.5") or row.get("PC<2.5")),

        # Pinnacle АГ
        "pinnacle_ahh":    safe_float(row.get("PCAHH") or row.get("PAHH")),
        "pinnacle_aha":    safe_float(row.get("PCAHA") or row.get("PAHA")),

        # Bet365 closing 1X2 (додатково)
        "b365_home":       safe_float(row.get("B365CH") or row.get("B365H")),
        "b365_draw":       safe_float(row.get("B365CD") or row.get("B365D")),
        "b365_away":       safe_float(row.get("B365CA") or row.get("B365A")),

        # Max odds (найвища лінія серед букмекерів)
        "max_home":        safe_float(row.get("MaxCH") or row.get("MaxH")),
        "max_draw":        safe_float(row.get("MaxCD") or row.get("MaxD")),
        "max_away":        safe_float(row.get("MaxCA") or row.get("MaxA")),
        "max_over25":      safe_float(row.get("MaxC>2.5") or row.get("Max>2.5")),
        "max_under25":     safe_float(row.get("MaxC<2.5") or row.get("Max<2.5")),
    }


# ──────────────────────────────────────────────────────────────
# Завантаження
# ──────────────────────────────────────────────────────────────

def download_csv(league_code: str, season_code: str) -> list[dict] | None:
    url = f"{BASE_URL}/{season_code}/{league_code}.csv"
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        # Декодуємо
        try:
            text = resp.content.decode("utf-8")
        except UnicodeDecodeError:
            text = resp.content.decode("latin-1")

        reader = csv.DictReader(StringIO(text))
        rows = [row for row in reader if row.get("HomeTeam")]
        return rows

    except requests.RequestException as e:
        print(f"      ❌ {url}: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# Збереження
# ──────────────────────────────────────────────────────────────

def save(matches: list[dict], path: Path):
    if not matches:
        return

    # JSON
    json_path = path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    # CSV
    csv_path = path.with_suffix(".csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=matches[0].keys())
        w.writeheader()
        w.writerows(matches)

    print(f"      💾 {json_path.name} ({len(matches)} матчів)")


# ──────────────────────────────────────────────────────────────
# Головна логіка
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league",  help="Код ліги (E0, D1, SP1...)")
    parser.add_argument("--season",  help="Сезон (2023-2024)")
    parser.add_argument("--test",    action="store_true",
                        help="Тест: АПЛ 2023-24")
    parser.add_argument("--output",  default="football_data",
                        help="Папка для збереження")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    if args.test:
        leagues = [("E0", "2324", "2023-2024")]
    else:
        season_filter = args.season
        league_filter = args.league
        leagues = []
        for season_full, season_code in SEASONS:
            if season_filter and season_full != season_filter:
                continue
            for league_code in LEAGUES:
                if league_filter and league_code != league_filter:
                    continue
                leagues.append((league_code, season_code, season_full))

    print(f"📋 Завдань: {len(leagues)}")
    print(f"📁 Вивід: {output_dir}/\n")

    all_matches = []
    total = 0
    errors = 0

    for league_code, season_code, season_full in leagues:
        league_name = LEAGUES.get(league_code, (league_code,))[0]
        print(f"  [{league_code}] {league_name} {season_full}...")

        rows = download_csv(league_code, season_code)
        if rows is None:
            print(f"      ⚠️  Не знайдено (404)")
            errors += 1
            continue

        matches = []
        for row in rows:
            m = parse_row(row, league_code, season_full)
            if m:
                matches.append(m)

        if not matches:
            print(f"      ⚠️  Порожньо")
            continue

        # Pinnacle coverage
        pin_count = sum(1 for m in matches if m.get("pinnacle_home"))
        print(f"      ✅ {len(matches)} матчів, Pinnacle: {pin_count}/{len(matches)}")

        # Зберігаємо
        fname = f"fd_{league_code}_{season_full.replace('-', '_')}"
        save(matches, output_dir / fname)
        all_matches.extend(matches)
        total += len(matches)

        time.sleep(0.5)  # ввічлива пауза

    # Загальний файл
    if all_matches:
        all_path = output_dir / "fd_all"
        save(all_matches, all_path)

    print(f"\n{'='*50}")
    print(f"✅ Зібрано: {total} матчів")
    print(f"❌ Помилок: {errors}")
    print(f"📁 Файли в: {output_dir}/")


if __name__ == "__main__":
    main()
