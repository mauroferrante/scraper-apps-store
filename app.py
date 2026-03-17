"""
Streamlit dashboard for App Store ranking trends.
Tracks Simply Wall St + competitors across multiple markets.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rankings_history.csv")

OUR_APP = "Simply Wall St"

COUNTRY_LABELS = {
    "US": "🇺🇸 United States",
    "AU": "🇦🇺 Australia",
    "CA": "🇨🇦 Canada",
    "DE": "🇩🇪 Germany",
    "GB": "🇬🇧 United Kingdom",
}

# Consistent colors per competitor
APP_COLORS = {
    "Simply Wall St": "#22c55e",   # green — our app stands out
    "Sharesight": "#3b82f6",       # blue
    "Snowball Analytics": "#a855f7", # purple
    "Seeking Alpha": "#f97316",    # orange
    "Yahoo Finance": "#6366f1",    # indigo
    "MarketWatch": "#ef4444",      # red
}

st.set_page_config(
    page_title="Simply Wall St — App Store Rankings",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 1px solid #3a3a5c;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #a0a0c0 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data loading with backward compatibility ────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    raw = pd.read_csv(CSV_FILE)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["keyword_rank"] = pd.to_numeric(raw["keyword_rank"], errors="coerce")
    raw["category_rank"] = pd.to_numeric(raw["category_rank"], errors="coerce")

    # Backward compatibility: fill missing app_name with our app
    if "app_name" not in raw.columns:
        raw["app_name"] = OUR_APP
    else:
        raw["app_name"] = raw["app_name"].fillna(OUR_APP)
        raw.loc[raw["app_name"].str.strip() == "", "app_name"] = OUR_APP

    # Deduplicate: keep last entry per date/app/country/keyword
    raw = raw.drop_duplicates(subset=["date", "app_name", "country", "keyword"], keep="last")
    return raw


if not os.path.exists(CSV_FILE):
    st.error("No data file found. Run `python tracker.py` first.")
    st.stop()

df = load_data()

if df.empty:
    st.warning("No ranking data yet. Run `python tracker.py` to collect the first batch.")
    st.stop()

# ── Derived datasets ────────────────────────────────────────────────────────
sws_df = df[df["app_name"] == OUR_APP].copy()  # Simply Wall St only

ALL_COUNTRIES = sorted(df["country"].unique().tolist())

# Custom keyword sort: priority keywords first, then any legacy keywords alphabetically
_KEYWORD_PRIORITY = [
    "stock analysis",
    "stock research",
    "stock screener",
    "portfolio tracker",
    "dividend tracker",
]
_all_kw_set = set(df["keyword"].unique())
ALL_KEYWORDS = [k for k in _KEYWORD_PRIORITY if k in _all_kw_set] + sorted(
    _all_kw_set - set(_KEYWORD_PRIORITY)
)

ALL_APPS = sorted(df["app_name"].unique().tolist())
LATEST_DATE = df["date"].max()
latest_df = df[df["date"] == LATEST_DATE]
sws_latest = latest_df[latest_df["app_name"] == OUR_APP]


# ── Helpers ─────────────────────────────────────────────────────────────────
def _compute_delta(
    data: pd.DataFrame,
    country: str,
    keyword: str,
    col: str = "keyword_rank",
    app_name: str = OUR_APP,
):
    """Return (current_rank, delta_str, delta_color) for a given app/country/keyword."""
    subset = data[
        (data["app_name"] == app_name)
        & (data["country"] == country)
        & (data["keyword"] == keyword)
    ].sort_values("date")
    if subset.empty:
        return None, None, "off"

    current = subset.iloc[-1][col]
    if pd.isna(current):
        return None, None, "off"

    current = int(current)
    dates = subset["date"].unique()
    if len(dates) < 2:
        return current, None, "off"

    prev_day = sorted(dates)[-2]
    prev_row = subset[subset["date"] == prev_day]
    if prev_row.empty:
        return current, None, "off"

    prev_val = prev_row.iloc[-1][col]
    if pd.isna(prev_val):
        return current, None, "off"

    change = int(prev_val) - current  # positive = rank improved
    if change == 0:
        return current, None, "off"

    delta_str = f"{'+' if change > 0 else ''}{change}"
    return current, delta_str, "normal"


def _chart_layout(fig, height: int = 480):
    """Apply standard chart styling."""
    fig.update_yaxes(
        autorange="reversed",
        range=[200, 1],
        title="Rank Position",
        gridcolor="rgba(128,128,160,0.15)",
        showgrid=True,
    )
    fig.update_xaxes(gridcolor="rgba(128,128,160,0.1)", showgrid=True)
    fig.update_layout(
        height=height,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12),
        ),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.title("📊 Simply Wall St — App Store Rankings")
st.caption(
    f"Tracking keyword & category positions across {len(ALL_COUNTRIES)} markets  ·  "
    f"Last updated **{LATEST_DATE.strftime('%B %d, %Y')}**  ·  "
    f"**{len(ALL_APPS)}** apps tracked"
)


# ═══════════════════════════════════════════════════════════════════════════
#  HERO SECTION — Simply Wall St Trend Chart
# ═══════════════════════════════════════════════════════════════════════════
with st.container(border=True):
    default_countries = [c for c in ["US", "AU"] if c in ALL_COUNTRIES]
    default_keywords = [k for k in ["stock analysis"] if k in ALL_KEYWORDS]

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_countries = st.multiselect(
            "Countries",
            options=ALL_COUNTRIES,
            default=default_countries,
            key="hero_countries",
        )
    with col_f2:
        sel_keywords = st.multiselect(
            "Keywords",
            options=ALL_KEYWORDS,
            default=default_keywords,
            key="hero_keywords",
        )

    # Filter to Simply Wall St only
    chart_data = sws_df.copy()
    if sel_countries:
        chart_data = chart_data[chart_data["country"].isin(sel_countries)]
    if sel_keywords:
        chart_data = chart_data[chart_data["keyword"].isin(sel_keywords)]

    chart_data = chart_data.dropna(subset=["keyword_rank"])

    if chart_data.empty:
        st.info("Select at least one country and keyword to see the trend chart.")
    else:
        chart_data = chart_data.copy()
        chart_data["label"] = chart_data["country"] + " · " + chart_data["keyword"]

        fig = px.line(
            chart_data,
            x="date",
            y="keyword_rank",
            color="label",
            markers=True,
            labels={"keyword_rank": "Rank Position", "date": "", "label": ""},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig = _chart_layout(fig, height=480)
        fig.add_hline(y=1, line_dash="dot", line_color="gold", opacity=0.4, annotation_text="#1")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TABBED SECTIONS
# ═══════════════════════════════════════════════════════════════════════════
tab_summary, tab_country, tab_battle = st.tabs(
    ["🏆 Executive Summary", "🌍 Country Deep-Dive", "⚔️ Competitor Battleground"]
)


# ── TAB 1: Executive Summary (Simply Wall St only) ─────────────────────────
with tab_summary:
    st.markdown("#### Top 5 Best Keyword Rankings")
    st.caption(f"Highest-ranking keyword positions for {OUR_APP} across all countries today.")

    ranked = sws_latest.dropna(subset=["keyword_rank"]).copy()
    ranked["keyword_rank"] = ranked["keyword_rank"].astype(int)
    top5 = ranked.nsmallest(5, "keyword_rank")

    if top5.empty:
        st.info("No keyword ranking data available yet.")
    else:
        cols = st.columns(5)
        for i, (_, row) in enumerate(top5.iterrows()):
            cur, delta, d_color = _compute_delta(df, row["country"], row["keyword"])
            with cols[i]:
                st.metric(
                    label=f"{row['country']} · {row['keyword']}",
                    value=f"#{int(row['keyword_rank'])}",
                    delta=delta,
                    delta_color=d_color,
                )

    st.divider()

    # ── Biggest Movers ──
    st.markdown("#### Biggest Movers")
    st.caption("Largest rank changes compared to the previous day.")

    sws_dates = sorted(sws_df["date"].unique())
    if len(sws_dates) < 2:
        st.info("Need at least 2 days of data to show movers. Check back tomorrow!")
    else:
        prev_date = sws_dates[-2]
        prev_sws = sws_df[sws_df["date"] == prev_date]

        movers = []
        for _, row in sws_latest.iterrows():
            cur_rank = row["keyword_rank"]
            if pd.isna(cur_rank):
                continue
            match = prev_sws[
                (prev_sws["country"] == row["country"]) & (prev_sws["keyword"] == row["keyword"])
            ]
            if match.empty:
                continue
            prev_rank = match.iloc[0]["keyword_rank"]
            if pd.isna(prev_rank):
                continue
            change = int(prev_rank) - int(cur_rank)
            if change != 0:
                movers.append(
                    {
                        "country": row["country"],
                        "keyword": row["keyword"],
                        "current": int(cur_rank),
                        "change": change,
                        "abs_change": abs(change),
                    }
                )

        if not movers:
            st.info("No rank movements detected since yesterday.")
        else:
            movers_df = pd.DataFrame(movers).nlargest(5, "abs_change")
            cols = st.columns(min(len(movers_df), 5))
            for i, (_, m) in enumerate(movers_df.iterrows()):
                delta_str = f"{'+' if m['change'] > 0 else ''}{m['change']}"
                with cols[i]:
                    st.metric(
                        label=f"{m['country']} · {m['keyword']}",
                        value=f"#{m['current']}",
                        delta=delta_str,
                        delta_color="normal",
                    )

    st.divider()

    # ── Finance Category Rankings ──
    st.markdown("#### Finance Category Position")
    st.caption("Position in the App Store's Finance top-free chart per country.")

    cat_data = sws_latest.drop_duplicates(subset=["country"])[["country", "category_rank"]].copy()
    cat_cols = st.columns(min(len(cat_data), 5))
    for i, (_, row) in enumerate(cat_data.iterrows()):
        cat_val = row["category_rank"]
        display = f"#{int(cat_val)}" if pd.notna(cat_val) else "—"
        with cat_cols[i % len(cat_cols)]:
            st.metric(label=f"{row['country']} — Finance", value=display)


# ── TAB 2: Country Deep-Dive (Simply Wall St only) ─────────────────────────
with tab_country:
    selected_country = st.selectbox(
        "Select a country",
        options=ALL_COUNTRIES,
        format_func=lambda c: COUNTRY_LABELS.get(c, c),
        key="deep_dive_country",
    )

    country_latest = sws_latest[sws_latest["country"] == selected_country]

    if country_latest.empty:
        st.info(f"No data available for {selected_country}.")
    else:
        cat_row = country_latest.iloc[0]
        cat_val = cat_row["category_rank"]
        cat_display = f"#{int(cat_val)}" if pd.notna(cat_val) else "—  Unranked"

        st.markdown(f"##### Finance Category: **{cat_display}**")
        st.divider()

        keywords = country_latest["keyword"].tolist()
        rows_needed = (len(keywords) + 2) // 3

        for row_idx in range(rows_needed):
            cols = st.columns(3)
            for col_idx in range(3):
                kw_idx = row_idx * 3 + col_idx
                if kw_idx >= len(keywords):
                    break
                kw = keywords[kw_idx]
                cur, delta, d_color = _compute_delta(df, selected_country, kw)

                with cols[col_idx]:
                    display_val = f"#{cur}" if cur is not None else "—  Unranked"
                    st.metric(label=kw.title(), value=display_val, delta=delta, delta_color=d_color)

        st.divider()

        st.markdown(f"##### Trend — {COUNTRY_LABELS.get(selected_country, selected_country)}")
        country_hist = sws_df[sws_df["country"] == selected_country].dropna(subset=["keyword_rank"]).copy()

        if country_hist.empty:
            st.info("No historical keyword data for this country yet.")
        else:
            fig3 = px.line(
                country_hist,
                x="date",
                y="keyword_rank",
                color="keyword",
                markers=True,
                labels={"keyword_rank": "Rank", "date": "", "keyword": ""},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig3 = _chart_layout(fig3, height=380)
            st.plotly_chart(fig3, use_container_width=True)


# ── TAB 3: Competitor Battleground ──────────────────────────────────────────
with tab_battle:
    st.markdown("#### Head-to-Head Competitor Comparison")
    st.caption("See how Simply Wall St stacks up against competitors for any keyword in any market.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        battle_country = st.selectbox(
            "Country",
            options=ALL_COUNTRIES,
            format_func=lambda c: COUNTRY_LABELS.get(c, c),
            key="battle_country",
        )
    with col_b2:
        battle_keyword = st.selectbox(
            "Keyword",
            options=ALL_KEYWORDS,
            key="battle_keyword",
        )

    # ── Leaderboard ──
    st.markdown("##### Leaderboard")

    battle_latest = latest_df[
        (latest_df["country"] == battle_country) & (latest_df["keyword"] == battle_keyword)
    ].copy()

    if battle_latest.empty:
        st.info("No data for this country/keyword combination yet. Run the tracker first.")
    else:
        # Sort: ranked apps first (ascending), then unranked
        battle_latest["_sort"] = battle_latest["keyword_rank"].fillna(9999).astype(int)
        battle_latest = battle_latest.sort_values("_sort")

        # Build a clean display dataframe
        leaderboard_rows = []
        for pos, (_, row) in enumerate(battle_latest.iterrows(), start=1):
            kw_rank = row["keyword_rank"]
            is_ranked = pd.notna(kw_rank)
            app = row["app_name"]

            # Medal for top 3
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, "") if is_ranked else ""

            leaderboard_rows.append(
                {
                    "": medal,
                    "App": app,
                    "Rank": f"#{int(kw_rank)}" if is_ranked else "Unranked",
                    "is_ours": app == OUR_APP,
                    "raw_rank": int(kw_rank) if is_ranked else None,
                }
            )

        # Show as custom HTML cards (up to 6 apps)
        cards_html = '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1rem;">'
        for entry in leaderboard_rows:
            label = f"{entry['']} {entry['App']}" if entry[""] else entry["App"]
            val = entry["Rank"]
            is_ours = entry["is_ours"]

            # Compute delta
            cur, delta, d_color = _compute_delta(
                df, battle_country, battle_keyword, app_name=entry["App"]
            )

            # Delta badge
            delta_html = ""
            if delta:
                d_val = delta.replace(" ", "")
                if d_color == "normal":  # rank improved = green
                    d_style = "color:#22c55e;"
                elif d_color == "inverse":  # rank worsened = red
                    d_style = "color:#ef4444;"
                else:
                    d_style = "color:#9ca3af;"
                delta_html = f'<div style="font-size:0.78rem;margin-top:2px;{d_style}">{delta}</div>'

            if is_ours:
                border = "border:2px solid #3b82f6;"
                bg = "background:linear-gradient(135deg,#1e293b 0%,#1e3a5f 100%);"
                shadow = "box-shadow:0 0 12px rgba(59,130,246,0.25);"
                name_style = "color:#60a5fa;font-weight:700;"
            else:
                border = "border:1px solid #334155;"
                bg = "background:#1e1e2e;"
                shadow = ""
                name_style = "color:#cbd5e1;font-weight:500;"

            cards_html += (
                f'<div style="flex:1 1 140px;min-width:130px;max-width:220px;'
                f'border-radius:12px;padding:16px 14px;{border}{bg}{shadow}">'
                f'<div style="{name_style}font-size:0.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</div>'
                f'<div style="color:#f1f5f9;font-size:1.6rem;font-weight:800;margin-top:4px;">{val}</div>'
                f'{delta_html}'
                f'</div>'
            )
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

    st.divider()

    # ── Battle Chart ──
    st.markdown("##### Historical Trend")

    battle_hist = df[
        (df["country"] == battle_country) & (df["keyword"] == battle_keyword)
    ].dropna(subset=["keyword_rank"]).copy()

    if battle_hist.empty:
        st.info("No historical data for this combination yet.")
    else:
        # Use consistent app colors
        color_map = {app: APP_COLORS.get(app, "#888") for app in battle_hist["app_name"].unique()}

        fig_battle = px.line(
            battle_hist,
            x="date",
            y="keyword_rank",
            color="app_name",
            markers=True,
            labels={"keyword_rank": "Rank Position", "date": "", "app_name": ""},
            color_discrete_map=color_map,
        )

        # Make Simply Wall St line thicker
        for trace in fig_battle.data:
            if trace.name == OUR_APP:
                trace.update(line=dict(width=4))
            else:
                trace.update(line=dict(width=2, dash="dot"))

        fig_battle = _chart_layout(fig_battle, height=480)
        fig_battle.add_hline(
            y=1, line_dash="dot", line_color="gold", opacity=0.4, annotation_text="#1"
        )
        st.plotly_chart(fig_battle, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
#  RAW DATA EXPANDER
# ═══════════════════════════════════════════════════════════════════════════
with st.expander("📋 Raw Data"):
    display_df = df.sort_values(
        ["date", "app_name", "country", "keyword"],
        ascending=[False, True, True, True],
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)
