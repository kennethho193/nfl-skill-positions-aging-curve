import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="NFL Skill Position Aging Curves",
    page_icon="🏈",
    layout="wide"
)

pos_order  = ["RB", "WR", "TE", "QB"]
pos_colors = {"RB": "#1D9E75", "WR": "#3B8BD4", "TE": "#E8593C", "QB": "#9B59B6"}

# ── Load and prep data ────────────────────────────────────────
@st.cache_data
def load_and_prep():
    conn = sqlite3.connect("db/nfl_skill_positions.db")
    df = pd.read_sql_query("""
        SELECT s.*, p.display_name
        FROM season_stats s
        JOIN players p ON s.player_id = p.player_id
    """, conn)
    conn.close()

    df = df[df["age"] <= 35].copy()

    def get_epa_col(position):
        if position == "QB":
            return "passing_epa"
        elif position == "RB":
            return "rushing_epa"
        else:
            return "receiving_epa"

    df["epa_raw"] = df.apply(lambda row: row[get_epa_col(row["position"])], axis=1)
    df["epa_z"]   = df.groupby("position")["epa_raw"].transform(
        lambda x: (x - x.mean()) / x.std()
    )

    def center_age(group):
        group["age_c"]  = group["age"] - group["age"].mean()
        group["age_c2"] = group["age_c"] ** 2
        return group

    df = df.groupby("position", group_keys=False).apply(center_age)
    return df

@st.cache_data
def fit_all_models():
    df = load_and_prep()
    results      = {}
    peak_ages    = {}
    pos_mean_age = df.groupby("position")["age"].mean()

    for pos in pos_order:
        pos_df = df[df["position"] == pos].copy()
        model  = smf.mixedlm(
            "epa_z ~ age_c + age_c2",
            data=pos_df,
            groups=pos_df["player_id"]
        )
        result       = model.fit(reml=True)
        results[pos] = result

        b1 = result.fe_params["age_c"]
        b2 = result.fe_params["age_c2"]

        if b2 < 0 and result.pvalues["age_c2"] < 0.05:
            peak_age_c     = -b1 / (2 * b2)
            peak_ages[pos] = round(peak_age_c + pos_mean_age[pos], 1)
        else:
            peak_ages[pos] = None

    return results, peak_ages, pos_mean_age

# ── Header ────────────────────────────────────────────────────
st.title("🏈 NFL Skill Position Aging Curves")
st.markdown(
    "Mixed-effects models fit to 24 seasons of NFL data (2000–2023). "
    "EPA standardized within position to enable cross-position comparison. "
    "Age capped at 35 to remove survivorship bias in the tail."
)

# ── Fit models ────────────────────────────────────────────────
with st.spinner("Fitting models — this takes about 30 seconds..."):
    results, peak_ages, pos_mean_age = fit_all_models()
    df = load_and_prep()

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("Settings")
view = st.sidebar.radio(
    "View",
    ["All positions — comparison", "Single position deep dive"]
)

selected_player = st.sidebar.text_input(
    "Highlight a player (optional)",
    placeholder="e.g. Tom Brady"
)

# ── Metric cards ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
findings = {
    "RB": "No clear peak",
    "WR": "Peak 27.0",
    "TE": "Peak 24.8",
    "QB": "Peak 29.9"
}
for col, pos in zip([col1, col2, col3, col4], pos_order):
    col.metric(pos, findings[pos])

st.divider()

# ── Comparison view ───────────────────────────────────────────
if view == "All positions — comparison":
    st.subheader("All positions — EPA z-score aging curves")

    age_range = np.linspace(21, 35, 200)
    fig, ax   = plt.subplots(figsize=(12, 7))

    for pos in pos_order:
        result    = results[pos]
        b1        = result.fe_params["age_c"]
        b2        = result.fe_params["age_c2"]
        intercept = result.fe_params["Intercept"]

        age_c     = age_range - pos_mean_age[pos]
        age_c2    = age_c ** 2
        predicted = intercept + b1 * age_c + b2 * age_c2

        se = np.sqrt(
            result.cov_params().loc["Intercept", "Intercept"] +
            age_c**2  * result.cov_params().loc["age_c",  "age_c"] +
            age_c2**2 * result.cov_params().loc["age_c2", "age_c2"]
        )

        ax.plot(age_range, predicted,
                color=pos_colors[pos], linewidth=2.5, label=pos)
        ax.fill_between(age_range,
                        predicted - 1.96 * se,
                        predicted + 1.96 * se,
                        alpha=0.12, color=pos_colors[pos])

        if peak_ages[pos]:
            ax.axvline(peak_ages[pos], color=pos_colors[pos],
                       linestyle="--", linewidth=1.5, alpha=0.7)
            ax.text(peak_ages[pos] + 0.1, 0.45,
                    f"{pos} peak\n{peak_ages[pos]}",
                    color=pos_colors[pos], fontsize=9)

    # Highlight player if entered
    if selected_player:
        player_df = df[df["display_name"].str.contains(
                       selected_player, case=False, na=False)]
        if not player_df.empty:
            for pos in player_df["position"].unique():
                pdf = player_df[player_df["position"] == pos].sort_values("age")
                ax.scatter(pdf["age"], pdf["epa_z"],
                           color=pos_colors[pos], s=60, zorder=5)
                ax.plot(pdf["age"], pdf["epa_z"],
                        color=pos_colors[pos], linewidth=1.5,
                        alpha=0.8, label=f"{selected_player} ({pos})")
        else:
            st.sidebar.warning("Player not found — check spelling")

    ax.axhline(0, color="black", linewidth=0.8, alpha=0.3,
               label="League average")
    ax.set_title("NFL skill position aging curves — EPA z-score (2000–2023)",
                 fontsize=14, pad=15)
    ax.set_xlabel("Age", fontsize=12)
    ax.set_ylabel("EPA z-score (within position)", fontsize=12)
    ax.legend(fontsize=11, loc="lower left")
    plt.tight_layout()
    st.pyplot(fig)

# ── Single position deep dive ─────────────────────────────────
else:
    pos = st.sidebar.selectbox("Select position", pos_order)
    pos_df    = df[df["position"] == pos]
    result    = results[pos]
    b1        = result.fe_params["age_c"]
    b2        = result.fe_params["age_c2"]
    intercept = result.fe_params["Intercept"]

    age_range = np.linspace(21, 35, 200)
    age_c     = age_range - pos_mean_age[pos]
    age_c2    = age_c ** 2
    predicted = intercept + b1 * age_c + b2 * age_c2

    se = np.sqrt(
        result.cov_params().loc["Intercept", "Intercept"] +
        age_c**2  * result.cov_params().loc["age_c",  "age_c"] +
        age_c2**2 * result.cov_params().loc["age_c2", "age_c2"]
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.scatter(pos_df["age"], pos_df["epa_z"],
               alpha=0.08, color=pos_colors[pos], s=20,
               label="Individual seasons")

    if selected_player:
        player_df = pos_df[pos_df["display_name"].str.contains(
                           selected_player, case=False, na=False)]
        if not player_df.empty:
            pdf = player_df.sort_values("age")
            ax.scatter(pdf["age"], pdf["epa_z"],
                       color="coral", s=60, zorder=5,
                       label=selected_player)
            ax.plot(pdf["age"], pdf["epa_z"],
                    color="coral", linewidth=1.5, alpha=0.8)
        else:
            st.sidebar.warning("Player not found — check spelling")

    ax.plot(age_range, predicted,
            color=pos_colors[pos], linewidth=3,
            label="Mixed-effects model fit")
    ax.fill_between(age_range,
                    predicted - 1.96 * se,
                    predicted + 1.96 * se,
                    alpha=0.2, color=pos_colors[pos],
                    label="95% CI")

    if peak_ages[pos]:
        ax.axvline(peak_ages[pos], color="coral", linestyle="--",
                   linewidth=2, label=f"Peak age: {peak_ages[pos]}")

    ax.axhline(0, color="black", linewidth=0.8, alpha=0.3)
    ax.set_title(f"{pos} aging curve — EPA z-score (2000–2023)",
                 fontsize=14, pad=15)
    ax.set_xlabel("Age", fontsize=12)
    ax.set_ylabel("EPA z-score (within position)", fontsize=12)
    ax.legend(fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# ── Summary findings table ────────────────────────────────────
st.subheader("Summary of findings")
summary_data = {
    "Position": pos_order,
    "Peak age": [str(peak_ages[p]) if peak_ages[p] else "No clear peak"
                 for p in pos_order],
    "Pattern": [
        "Monotonic decline from entry",
        "Rise then fall — develops with experience",
        "Early peak, sharp post-peak decline",
        "Longest development curve, latest peak"
    ],
    "Qualified seasons": [len(df[df["position"] == p]) for p in pos_order]
}
st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

# ── Model details ─────────────────────────────────────────────
with st.expander("Model details"):
    st.markdown("""
    **Model:** Linear mixed-effects (LME) per position  
    **Formula:** `epa_z ~ age_c + age_c²`  
    **Random effect:** Player intercept  
    **Method:** REML  
    **EPA metric:** Position-specific (rushing EPA for RB, receiving EPA for WR/TE, passing EPA for QB)  
    **Standardization:** Z-score within position to enable cross-position comparison  
    **Age cap:** 35 — removes survivorship bias in the tail  
    """)

    for pos in pos_order:
        result = results[pos]
        st.markdown(f"**{pos}** — {len(df[df['position']==pos])} seasons, "
                    f"Age (linear) coef: {result.fe_params['age_c']:.4f} "
                    f"(p={result.pvalues['age_c']:.3f}), "
                    f"Age² coef: {result.fe_params['age_c2']:.4f} "
                    f"(p={result.pvalues['age_c2']:.3f})")