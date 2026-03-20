"""
db_loader.py — завантаження даних football-data.co.uk в PostgreSQL

Запуск:
    pip install psycopg2-binary
    python db_loader.py                          # завантажує fd_all.json
    python db_loader.py --file fd_E0_2023_2024.json  # один файл
    python db_loader.py --host X.X.X.X --dbname football  # з параметрами
"""

import json
import argparse
import os
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ Встанови: pip install psycopg2-binary")
    exit(1)

# ──────────────────────────────────────────────────────────────
# Конфіг підключення
# ──────────────────────────────────────────────────────────────

DB = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "football"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def get_or_create_team(cur, name: str) -> int:
    cur.execute("SELECT id FROM teams WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO teams(name) VALUES(%s) RETURNING id", (name,))
    return cur.fetchone()[0]

def get_league_id(cur, code: str) -> int | None:
    cur.execute("SELECT id FROM leagues WHERE code=%s", (code,))
    row = cur.fetchone()
    return row[0] if row else None

def parse_time(time_str: str):
    if not time_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None

# ──────────────────────────────────────────────────────────────
# Завантаження
# ──────────────────────────────────────────────────────────────

def load_file(path: str, conn):
    print(f"\n📂 Завантажуємо: {path}")

    with open(path, encoding="utf-8") as f:
        matches = json.load(f)

    print(f"   Матчів у файлі: {len(matches)}")

    added = 0
    skipped = 0
    errors = 0

    with conn.cursor() as cur:
        for m in matches:
            try:
                league_id = get_league_id(cur, m["league_code"])
                if not league_id:
                    skipped += 1
                    continue

                home_id = get_or_create_team(cur, m["home_team"])
                away_id = get_or_create_team(cur, m["away_team"])
                match_time = parse_time(m.get("time_utc", ""))

                cur.execute("""
                    INSERT INTO matches (
                        source, league_id, season,
                        home_team_id, away_team_id, match_time,
                        score_home, score_away, score_ht_home, score_ht_away,
                        result,
                        home_shots, away_shots, home_shots_ot, away_shots_ot,
                        home_corners, away_corners,
                        home_fouls, away_fouls,
                        home_yellow, away_yellow,
                        home_red, away_red,
                        referee,
                        pinnacle_home, pinnacle_draw, pinnacle_away,
                        pinnacle_over25, pinnacle_under25,
                        pinnacle_ahh, pinnacle_aha,
                        b365_home, b365_draw, b365_away,
                        max_home, max_draw, max_away,
                        max_over25, max_under25
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                    ON CONFLICT (league_id, season, home_team_id, away_team_id, match_time)
                    DO NOTHING
                """, (
                    m.get("source", "football-data.co.uk"),
                    league_id, m["season"],
                    home_id, away_id, match_time,
                    m.get("score_home"), m.get("score_away"),
                    m.get("score_ht_home"), m.get("score_ht_away"),
                    m.get("result"),
                    m.get("home_shots"), m.get("away_shots"),
                    m.get("home_shots_ot"), m.get("away_shots_ot"),
                    m.get("home_corners"), m.get("away_corners"),
                    m.get("home_fouls"), m.get("away_fouls"),
                    m.get("home_yellow"), m.get("away_yellow"),
                    m.get("home_red"), m.get("away_red"),
                    m.get("referee"),
                    m.get("pinnacle_home"), m.get("pinnacle_draw"), m.get("pinnacle_away"),
                    m.get("pinnacle_over25"), m.get("pinnacle_under25"),
                    m.get("pinnacle_ahh"), m.get("pinnacle_aha"),
                    m.get("b365_home"), m.get("b365_draw"), m.get("b365_away"),
                    m.get("max_home"), m.get("max_draw"), m.get("max_away"),
                    m.get("max_over25"), m.get("max_under25"),
                ))

                if cur.rowcount > 0:
                    added += 1
                else:
                    skipped += 1

            except Exception as e:
                errors += 1
                conn.rollback()
                print(f"   ⚠️  Помилка: {e} | {m.get('home_team')} vs {m.get('away_team')}")
                continue

        conn.commit()

        # Лог
        cur.execute("""
            INSERT INTO update_log(league_code, season, matches_added, source_file)
            VALUES (%s, %s, %s, %s)
        """, ("ALL", "mixed", added, str(path)))
        conn.commit()

    print(f"   ✅ Додано: {added} | Пропущено: {skipped} | Помилок: {errors}")
    return added


# ──────────────────────────────────────────────────────────────
# Перевірка БД після завантаження
# ──────────────────────────────────────────────────────────────

def print_stats(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                l.code, l.name, COUNT(*) AS cnt,
                MIN(m.match_time)::date AS from_date,
                MAX(m.match_time)::date AS to_date
            FROM matches m
            JOIN leagues l ON l.id = m.league_id
            GROUP BY l.code, l.name
            ORDER BY l.code
        """)
        rows = cur.fetchall()

        print(f"\n{'='*65}")
        print(f"  {'Код':5} {'Ліга':25} {'Матчів':8} {'Від':12} {'До'}")
        print(f"{'='*65}")
        total = 0
        for code, name, cnt, from_d, to_d in rows:
            print(f"  {code:5} {name:25} {cnt:8} {str(from_d):12} {str(to_d)}")
            total += cnt
        print(f"{'='*65}")
        print(f"  {'ВСЬОГО':31} {total:8}")

        cur.execute("SELECT COUNT(*) FROM teams")
        teams = cur.fetchone()[0]
        print(f"\n  Команд у БД: {teams}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file",   default="football_data/fd_all.json")
    parser.add_argument("--host",   default=DB["host"])
    parser.add_argument("--port",   default=DB["port"], type=int)
    parser.add_argument("--dbname", default=DB["dbname"])
    parser.add_argument("--user",   default=DB["user"])
    parser.add_argument("--password", default=DB["password"])
    args = parser.parse_args()

    print(f"🔌 Підключення до {args.host}:{args.port}/{args.dbname}...")
    conn = psycopg2.connect(
        host=args.host, port=args.port,
        dbname=args.dbname, user=args.user,
        password=args.password
    )
    print("✅ Підключено")

    try:
        load_file(args.file, conn)
        print_stats(conn)
    finally:
        conn.close()
        print("\n🔌 З'єднання закрито")


if __name__ == "__main__":
    main()
