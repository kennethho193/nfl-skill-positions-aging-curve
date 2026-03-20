import sqlite3
import pandas as pd
import os

def create_database(db_path, schema_path):
    """
    Creates the SQLite database from the schema file.
    """

    with open(schema_path, "r") as f:
        schema = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()

def load_players(conn, df):
    """
    Loads unique player records into the players table.
    """

    players_df = df[[
        "player_id", "display_name", "position",
        "college_name", "draft_year", "draft_round",
        "height", "weight"
    ]].drop_duplicates(subset=["player_id"])

    players_df.to_sql(
        "players",
        conn,
        if_exists="append",
        index=False
    )

    print(f"  Loaded {len(players_df)} unique players")

def load_season_stats(conn, df):
    """
    Loads season-level stats into the season_stats table.
    """

    cols = [
        "player_id", "season", "age", "games", "position",
        #RB
        "carries", "rushing_yards", "rushing_tds",
        "rushing_first_downs", "rushing_epa", "rushing_fumbles",
        #WR/TE
        "targets", "receptions", "receiving_yards", "receiving_tds",
        "receiving_first_downs", "receiving_epa", "receiving_fumbles_lost",
        #QB
        "attempts", "completions", "passing_yards", "passing_tds",
        "interceptions", "passing_epa", "passing_first_downs",
        #Shared
        "fantasy_points", "fantasy_points_ppr"
    ]

    available_cols = [c for c in cols if c in df.columns]
    stats_df = df[available_cols].copy()

    stats_df.to_sql(
        "season_stats",
        conn,
        if_exists="append",
        index=False
    )

    print(f"  Loaded {len(stats_df)} season records")

def verify_load(conn):
    """
    Runs sanity checks on the loaded data.
    """
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM players")
    player_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM season_stats")
    stats_count = cursor.fetchone()[0]

    print(f"\nVerification:")
    print(f"  Players in database: {player_count}")
    print(f"  Season records in database: {stats_count}")

    print(f"\n  Breakdown by position:")
    cursor.execute("""
        SELECT position, COUNT(*) as seasons
        FROM season_stats
        GROUP BY position
        ORDER BY seasons DESC
    """)
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]} seasons")

    print(f"\n  Top 5 passing EPA seasons:")
    cursor.execute("""
        SELECT p.display_name, s.season, s.passing_epa
        FROM season_stats s
        JOIN players p ON s.player_id = p.player_id
        WHERE s.passing_epa IS NOT NULL
        ORDER BY s.passing_epa DESC
        LIMIT 5
    """)
    for name, season, epa in cursor.fetchall():
        print(f"    {name} ({season}): {epa:.1f} EPA")

    print(f"\n  Top 5 receiving EPA seasons:")
    cursor.execute("""
        SELECT p.display_name, s.season, s.position, s.receiving_epa
        FROM season_stats s
        JOIN players p ON s.player_id = p.player_id
        WHERE s.receiving_epa IS NOT NULL
        ORDER BY s.receiving_epa DESC
        LIMIT 5
    """)
    for name, season, pos, epa in cursor.fetchall():
        print(f"    {name} ({season}, {pos}): {epa:.1f} EPA")

if __name__ == "__main__":
    db_path     = "db/nfl_skill_positions.db"
    schema_path = "db/schema.sql"
    csv_path    = "data/raw/skill_position_stats.csv"

    #Step 1: Create database
    create_database(db_path, schema_path)

    #Step 2: Load CSV
    print("\nLoading CSV...")
    df = pd.read_csv(csv_path)
    print(f"  Read {len(df)} rows from CSV")

    #Step 3: Connect and load
    conn = sqlite3.connect(db_path)

    print("\nPlayers table:")
    load_players(conn, df)

    print("\nSeason_stats table:")
    load_season_stats(conn, df)

    conn.commit()
    conn.close()

    #Step 4: Verify
    conn = sqlite3.connect(db_path)
    verify_load(conn)
    conn.close()

    print("\nDatabase saved to db/nfl_skill_positions.db")