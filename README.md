# Football ML — парсер і база даних для ставок

Інструмент для збору, зберігання та аналізу футбольних даних з метою побудови ML-моделей прогнозування результатів матчів.

---

## Що збирається

| Дані | Джерело | Покриття |
|------|---------|----------|
| Результати матчів | football-data.co.uk | 100% |
| Pinnacle closing odds (1X2, тотал, АГ) | football-data.co.uk | 100% |
| Bet365, Max odds | football-data.co.uk | 100% |
| Удари, кутові, картки, фоли | football-data.co.uk | 100% |
| Live дані поточного сезону | Flashscore | щоденно |

## Ліги

14 ліг за 4 сезони (2021-2025), ~21 000 матчів:

| Країна | Ліга 1 | Ліга 2 |
|--------|--------|--------|
| Англія | АПЛ (E0) | Чемпіонат (E1) |
| Іспанія | Ла Ліга (SP1) | Сегунда (SP2) |
| Німеччина | Бундесліга (D1) | 2. Бундесліга (D2) |
| Італія | Серія А (I1) | Серія Б (I2) |
| Франція | Ліга 1 (F1) | Ліга 2 (F2) |
| Нідерланди | Ередивізі (N1) | — |
| Бельгія | Ліга A (B1) | — |
| Португалія | Ліга Португалії (P1) | Ліга Португалії 2 (P2) |

---

## Структура проекту

```
├── football_data_collector.py   # збір архіву з football-data.co.uk
├── flashscore_parser_v3.py      # парсер поточних даних з Flashscore
├── archive_collector.py         # збір архіву через Flashscore (допоміжний)
├── db_schema_final.sql          # схема PostgreSQL
├── requirements.txt
├── setup_venv.sh
└── football_data/               # зібрані CSV/JSON файли (не в репо)
```

---

## Швидкий старт

### 1. Встановлення

```bash
git clone https://github.com/Chu4ik/ML-football_TOP12
cd ML-football_TOP12

bash setup_venv.sh
source venv/bin/activate
```

### 2. База даних (PostgreSQL)

```bash
# Створення бази
sudo -u postgres psql -c "CREATE DATABASE football;"

# Застосування схеми
sudo -u postgres psql -d football -f db_schema_final.sql
```

### 3. Збір архіву (football-data.co.uk)

```bash
# Всі ліги, всі сезони (~21k матчів, ~1 хвилина)
python football_data_collector.py

# Тільки АПЛ
python football_data_collector.py --league E0

# Конкретний сезон
python football_data_collector.py --season 2023-2024
```

### 4. Поточний сезон (Flashscore)

```bash
# Результати сьогодні
python flashscore_parser_v3.py

# Деталі конкретного матчу
python flashscore_parser_v3.py --match MATCH_ID

# Останні 7 днів
python flashscore_parser_v3.py --days 7
```

---

## Схема бази даних

```
countries   — країни
leagues     — ліги (код, назва, рівень)
teams       — команди
matches     — матчі (результат, статистика, odds)
ml_features — фічі для ML (заповнюються окремим скриптом)
update_log  — лог оновлень
```

**Ключові поля `matches`:**

```sql
-- Результат
score_home, score_away, score_ht_home, score_ht_away
result          -- 'H' / 'D' / 'A'
total_goals     -- авто
over_25, btts   -- авто

-- Статистика
home_shots, away_shots, home_shots_ot, away_shots_ot
home_corners, away_corners, home_yellow, away_yellow

-- Pinnacle closing odds
pinnacle_home, pinnacle_draw, pinnacle_away
pinnacle_over25, pinnacle_under25
prob_home, prob_draw, prob_away  -- implied probability (авто)

-- Bet365 + Max
b365_home, b365_draw, b365_away
max_home, max_draw, max_away, max_over25
```

---

## Приклад запиту для ML

```sql
SELECT
    v.season, v.league, v.home_team, v.away_team,
    v.pinnacle_home, v.pinnacle_draw, v.pinnacle_away,
    v.prob_home, v.prob_draw, v.prob_away,
    v.pinnacle_over25, v.pinnacle_under25,
    v.home_shots, v.away_shots,
    v.home_corners, v.away_corners,
    v.result,     -- target: H/D/A
    v.over_25,    -- target: тотал
    v.btts        -- target: обидві забили
FROM v_matches v
WHERE v.result IS NOT NULL
ORDER BY v.match_time;
```

---

## Щотижневе оновлення

```bash
# cron: кожного понеділка о 8:00
0 8 * * 1 cd /path/to/project && python football_data_collector.py --season 2024-2025
```

---

## Залежності

- Python 3.10+
- PostgreSQL 14+
- `requests` — завантаження CSV
- `playwright` — Flashscore парсер (потребує Chromium)

---

## Ліцензія

MIT
