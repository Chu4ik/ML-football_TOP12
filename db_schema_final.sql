-- ============================================================
-- Football ML Database — фінальна схема
-- Джерело: football-data.co.uk
-- 14 ліг × 4 сезони = ~21k матчів + щотижневе поповнення
-- ============================================================

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

CREATE TABLE countries (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE leagues (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) UNIQUE NOT NULL,
    name        VARCHAR(200) NOT NULL,
    country_id  INTEGER REFERENCES countries(id),
    level       SMALLINT DEFAULT 1
);

CREATE TABLE teams (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(200) UNIQUE NOT NULL
);

CREATE TABLE matches (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(50) DEFAULT 'football-data.co.uk',
    league_id       INTEGER REFERENCES leagues(id),
    season          VARCHAR(10) NOT NULL,
    home_team_id    INTEGER REFERENCES teams(id),
    away_team_id    INTEGER REFERENCES teams(id),
    match_time      TIMESTAMP,
    score_home      SMALLINT,
    score_away      SMALLINT,
    score_ht_home   SMALLINT,
    score_ht_away   SMALLINT,
    result          CHAR(1),
    total_goals     SMALLINT GENERATED ALWAYS AS (
                        COALESCE(score_home, 0) + COALESCE(score_away, 0)
                    ) STORED,
    over_25         BOOLEAN GENERATED ALWAYS AS (
                        (COALESCE(score_home, 0) + COALESCE(score_away, 0)) > 2
                    ) STORED,
    btts            BOOLEAN GENERATED ALWAYS AS (
                        score_home > 0 AND score_away > 0
                    ) STORED,
    home_shots      SMALLINT,
    away_shots      SMALLINT,
    home_shots_ot   SMALLINT,
    away_shots_ot   SMALLINT,
    home_corners    SMALLINT,
    away_corners    SMALLINT,
    home_fouls      SMALLINT,
    away_fouls      SMALLINT,
    home_yellow     SMALLINT,
    away_yellow     SMALLINT,
    home_red        SMALLINT,
    away_red        SMALLINT,
    referee         VARCHAR(100),
    pinnacle_home   NUMERIC(6,3),
    pinnacle_draw   NUMERIC(6,3),
    pinnacle_away   NUMERIC(6,3),
    pinnacle_over25 NUMERIC(6,3),
    pinnacle_under25 NUMERIC(6,3),
    pinnacle_ahh    NUMERIC(6,3),
    pinnacle_aha    NUMERIC(6,3),
    prob_home       NUMERIC(5,4) GENERATED ALWAYS AS (
                        CASE WHEN pinnacle_home > 0
                        THEN ROUND((1.0 / pinnacle_home)::NUMERIC, 4) END
                    ) STORED,
    prob_draw       NUMERIC(5,4) GENERATED ALWAYS AS (
                        CASE WHEN pinnacle_draw > 0
                        THEN ROUND((1.0 / pinnacle_draw)::NUMERIC, 4) END
                    ) STORED,
    prob_away       NUMERIC(5,4) GENERATED ALWAYS AS (
                        CASE WHEN pinnacle_away > 0
                        THEN ROUND((1.0 / pinnacle_away)::NUMERIC, 4) END
                    ) STORED,
    b365_home       NUMERIC(6,3),
    b365_draw       NUMERIC(6,3),
    b365_away       NUMERIC(6,3),
    max_home        NUMERIC(6,3),
    max_draw        NUMERIC(6,3),
    max_away        NUMERIC(6,3),
    max_over25      NUMERIC(6,3),
    max_under25     NUMERIC(6,3),
    UNIQUE(league_id, season, home_team_id, away_team_id, match_time)
);

CREATE INDEX idx_matches_time    ON matches(match_time DESC);
CREATE INDEX idx_matches_league  ON matches(league_id, season);
CREATE INDEX idx_matches_home    ON matches(home_team_id, match_time DESC);
CREATE INDEX idx_matches_away    ON matches(away_team_id, match_time DESC);
CREATE INDEX idx_matches_result  ON matches(result) WHERE result IS NOT NULL;
CREATE INDEX idx_matches_season  ON matches(season, league_id);

CREATE TABLE ml_features (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER UNIQUE REFERENCES matches(id) ON DELETE CASCADE,
    home_pts_5      NUMERIC(4,1),
    away_pts_5      NUMERIC(4,1),
    home_pts_10     NUMERIC(4,1),
    away_pts_10     NUMERIC(4,1),
    home_scored_5   NUMERIC(4,2),
    home_conceded_5 NUMERIC(4,2),
    away_scored_5   NUMERIC(4,2),
    away_conceded_5 NUMERIC(4,2),
    home_shots_5    NUMERIC(4,2),
    away_shots_5    NUMERIC(4,2),
    home_shots_ot_5 NUMERIC(4,2),
    away_shots_ot_5 NUMERIC(4,2),
    home_position   SMALLINT,
    away_position   SMALLINT,
    home_points     SMALLINT,
    away_points     SMALLINT,
    h2h_home_wins   SMALLINT,
    h2h_draws       SMALLINT,
    h2h_away_wins   SMALLINT,
    h2h_avg_goals   NUMERIC(4,2),
    pin_prob_home   NUMERIC(5,4),
    pin_prob_draw   NUMERIC(5,4),
    pin_prob_away   NUMERIC(5,4),
    pin_prob_over25 NUMERIC(5,4),
    target_result   CHAR(1),
    target_over25   BOOLEAN,
    target_btts     BOOLEAN,
    computed_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE update_log (
    id              SERIAL PRIMARY KEY,
    league_code     VARCHAR(10),
    season          VARCHAR(10),
    matches_added   INTEGER DEFAULT 0,
    matches_updated INTEGER DEFAULT 0,
    source_file     VARCHAR(200),
    created_at      TIMESTAMP DEFAULT NOW()
);

INSERT INTO countries(name) VALUES
    ('АНГЛІЯ'), ('ІСПАНІЯ'), ('НІМЕЧЧИНА'),
    ('ІТАЛІЯ'), ('ФРАНЦІЯ'), ('НІДЕРЛАНДИ'),
    ('БЕЛЬГІЯ'), ('ПОРТУГАЛІЯ');

INSERT INTO leagues(code, name, country_id, level) VALUES
    ('E0',  'Прем''єр-ліга',      (SELECT id FROM countries WHERE name='АНГЛІЯ'),     1),
    ('E1',  'Чемпіонат',           (SELECT id FROM countries WHERE name='АНГЛІЯ'),     2),
    ('SP1', 'Ла Ліга',             (SELECT id FROM countries WHERE name='ІСПАНІЯ'),    1),
    ('SP2', 'Сегунда',             (SELECT id FROM countries WHERE name='ІСПАНІЯ'),    2),
    ('D1',  'Бундесліга',          (SELECT id FROM countries WHERE name='НІМЕЧЧИНА'),  1),
    ('D2',  '2. Бундесліга',       (SELECT id FROM countries WHERE name='НІМЕЧЧИНА'),  2),
    ('I1',  'Серія А',             (SELECT id FROM countries WHERE name='ІТАЛІЯ'),     1),
    ('I2',  'Серія Б',             (SELECT id FROM countries WHERE name='ІТАЛІЯ'),     2),
    ('F1',  'Ліга 1',              (SELECT id FROM countries WHERE name='ФРАНЦІЯ'),    1),
    ('F2',  'Ліга 2',              (SELECT id FROM countries WHERE name='ФРАНЦІЯ'),    2),
    ('N1',  'Ередивізі',           (SELECT id FROM countries WHERE name='НІДЕРЛАНДИ'), 1),
    ('B1',  'Ліга A',              (SELECT id FROM countries WHERE name='БЕЛЬГІЯ'),    1),
    ('P1',  'Ліга Португалії',     (SELECT id FROM countries WHERE name='ПОРТУГАЛІЯ'), 1),
    ('P2',  'Ліга Португалії 2',   (SELECT id FROM countries WHERE name='ПОРТУГАЛІЯ'), 2);

CREATE VIEW v_matches AS
SELECT
    m.id, m.season, m.match_time,
    c.name AS country, l.name AS league, l.code AS league_code, l.level,
    ht.name AS home_team, at.name AS away_team,
    m.score_home, m.score_away, m.score_ht_home, m.score_ht_away,
    m.result, m.total_goals, m.over_25, m.btts,
    m.home_shots, m.away_shots, m.home_shots_ot, m.away_shots_ot,
    m.home_corners, m.away_corners, m.home_yellow, m.away_yellow,
    m.home_red, m.away_red,
    m.pinnacle_home, m.pinnacle_draw, m.pinnacle_away,
    m.pinnacle_over25, m.pinnacle_under25,
    m.prob_home, m.prob_draw, m.prob_away,
    m.b365_home, m.b365_draw, m.b365_away,
    m.max_home, m.max_draw, m.max_away
FROM matches m
JOIN leagues  l  ON l.id = m.league_id
JOIN countries c ON c.id = l.country_id
JOIN teams    ht ON ht.id = m.home_team_id
JOIN teams    at ON at.id = m.away_team_id;

CREATE VIEW v_league_stats AS
SELECT
    l.code, l.name AS league, c.name AS country, m.season,
    COUNT(*) AS matches,
    ROUND(AVG(m.total_goals)::NUMERIC, 2) AS avg_goals,
    ROUND(AVG(CASE WHEN m.btts    THEN 1.0 ELSE 0 END)::NUMERIC, 3) AS btts_rate,
    ROUND(AVG(CASE WHEN m.over_25 THEN 1.0 ELSE 0 END)::NUMERIC, 3) AS over25_rate
FROM matches m
JOIN leagues  l ON l.id = m.league_id
JOIN countries c ON c.id = l.country_id
WHERE m.result IS NOT NULL
GROUP BY l.code, l.name, c.name, m.season
ORDER BY c.name, l.level, m.season DESC;

SELECT 'countries' AS tbl, COUNT(*) FROM countries UNION ALL
SELECT 'leagues',           COUNT(*) FROM leagues;
