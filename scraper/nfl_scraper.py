import nfl_data_py as nfl
import pandas as pd
import os

def scrape_skill_position_stats(start_year, end_year):
    """
    Scrapes seasonal stats for all offensive skill positions
    (RB, WR, TE, QB) and merges with player info for age calculation.
    """
    years = list(range(start_year, end_year + 1))

    # Step 1: Get seasonal stats
    print("Getting seasonal stats...")
    stats_df = nfl.import_seasonal_data(years)
    print(f"  Got {len(stats_df)} rows")

    # Step 2: Get player info
    print("Getting player info...")
    players_df = nfl.import_players()
    print(f"  Got {len(players_df)} players")

    # Step 3: Keep useful player info columns
    players_slim = players_df[[
        "gsis_id", "display_name", "position",
        "birth_date", "height", "weight",
        "college_name", "draft_year", "draft_round"
    ]].copy()

    # Step 4: Merge
    print("Merging datasets...")
    merged_df = stats_df.merge(
        players_slim,
        left_on="player_id",
        right_on="gsis_id",
        how="inner"
    )
    print(f"  Merged dataset has {len(merged_df)} rows")

    # Step 5: Filter to skill positions only
    skill_positions = ["RB", "WR", "TE", "QB"]
    skill_df = merged_df[merged_df["position"].isin(skill_positions)].copy()
    print(f"  Filtered to skill positions — {len(skill_df)} rows")

    # Step 6: Calculate age
    skill_df["birth_date"] = pd.to_datetime(skill_df["birth_date"])
    skill_df["age"] = skill_df["season"] - skill_df["birth_date"].dt.year
    print(f"  Age column calculated")

    # Step 7: Apply position-specific qualifying thresholds
    rb_mask  = (skill_df["position"] == "RB") & (skill_df["carries"] >= 50)
    wr_mask  = (skill_df["position"] == "WR") & (skill_df["targets"] >= 40)
    te_mask  = (skill_df["position"] == "TE") & (skill_df["targets"] >= 25)
    qb_mask  = (skill_df["position"] == "QB") & (skill_df["attempts"] >= 200)

    qualified_df = skill_df[rb_mask | wr_mask | te_mask | qb_mask].copy()
    print(f"  After qualifying thresholds — {len(qualified_df)} rows")

    # Step 8: Print breakdown by position
    print("\n  Breakdown by position:")
    for pos in skill_positions:
        count = len(qualified_df[qualified_df["position"] == pos])
        print(f"    {pos}: {count} qualified seasons")

    # Step 9: Keep relevant columns
    cols = [
        "player_id", "display_name", "position", "season", "age",
        "college_name", "draft_year", "draft_round",
        "height", "weight", "games",
        # RB metrics
        "carries", "rushing_yards", "rushing_tds",
        "rushing_first_downs", "rushing_epa", "rushing_fumbles",
        # WR/TE metrics
        "targets", "receptions", "receiving_yards", "receiving_tds",
        "receiving_first_downs", "receiving_epa", "receiving_fumbles_lost",
        # QB metrics
        "attempts", "completions", "passing_yards", "passing_tds",
        "interceptions", "passing_epa", "passing_first_downs",
        # Shared
        "fantasy_points", "fantasy_points_ppr"
    ]

    available_cols = [c for c in cols if c in qualified_df.columns]
    qualified_df = qualified_df[available_cols]

    return qualified_df


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    df = scrape_skill_position_stats(2000, 2023)

    output_path = "data/raw/skill_position_stats.csv"
    df.to_csv(output_path, index=False)

    print(f"\nDone! Saved {len(df)} rows to {output_path}")
    print("\nFirst 5 rows:")
    print(df.head())