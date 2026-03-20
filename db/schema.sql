-- NFL Skill Position Aging Curves — Database Schema

-- Players table: one row per player, static info
CREATE TABLE IF NOT EXISTS players (
    player_id       TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    position        TEXT NOT NULL,
    college_name    TEXT,
    draft_year      INTEGER,
    draft_round     INTEGER,
    height          TEXT,
    weight          REAL
);

-- Season stats table: one row per player per season
-- Position-specific columns will be NULL where not applicable
CREATE TABLE IF NOT EXISTS season_stats (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id             TEXT NOT NULL,
    season                INTEGER NOT NULL,
    age                   INTEGER,
    games                 INTEGER,
    position              TEXT NOT NULL,

    -- RB metrics
    carries               REAL,
    rushing_yards         REAL,
    rushing_tds           REAL,
    rushing_first_downs   REAL,
    rushing_epa           REAL,
    rushing_fumbles       REAL,

    -- WR/TE metrics
    targets               REAL,
    receptions            REAL,
    receiving_yards       REAL,
    receiving_tds         REAL,
    receiving_first_downs REAL,
    receiving_epa         REAL,
    receiving_fumbles_lost REAL,

    -- QB metrics
    attempts              REAL,
    completions           REAL,
    passing_yards         REAL,
    passing_tds           REAL,
    interceptions         REAL,
    passing_epa           REAL,
    passing_first_downs   REAL,

    -- Shared
    fantasy_points        REAL,
    fantasy_points_ppr    REAL,

    FOREIGN KEY (player_id) REFERENCES players (player_id),
    UNIQUE (player_id, season)
);