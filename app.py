"""
Streamlit dashboard for Simply Wall St App Store ranking trends.
Professional UI with hero chart, executive summary, and country deep-dive.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rankings_history.csv")

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
    /* Tighten top padding */
    .block-container { padding-top: 1.5rem; }

    /* Style metric cards */
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

    /* Unranked styling */
    .unranked-badge {
        display: inline-block;
        background: #3a3a5c;
        color: #808098;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data loading ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    raw = pd.read_csv(CSV_FILE)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["keyword_rank"] = pd.to_numeric(raw["keyword_rank"], errors="coerce")
    raw["category_rank"] = pd.to_numeric(raw["category_rank"], errors="coerce")
    # Deduplicate: keep last entry per date/country/keyword
    raw = raw.drop_duplicates(subset=["date", "country", "keyword"], keep="last")
    return raw


if not os.path.exists(CSV_FILE):
    st.error("No data file found. Run `python tracker.py` first.")
    st.stop()

df = load_data()

if df.empty:
    st.warning("No ranking data yet. Run `python tracker.py` to collect the first batch.")
    st.stop()


# ── Helper: compute delta between latest and previous day ───────────────────
def _compute_delta(data: pd.DataFrame, country: str, keyword: str, col: str = "keyword_rank"):
    """Return (current_rank, delta_str, delta_color) for a given country+keyword."""
    subset = data[(data["country"] == country) & (data["keyword"] == keyword)].sort_values("date")
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


def _rank_display(val) -> str:
    """Format a rank value: integer or styled 'Unranked'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return str(int(val))


# ── Constants ───────────────────────────────────────────────────────────────
ALL_COUNTRIES = sorted(df["country"].unique().tolist())
ALL_KEYWORDS = sorted(df["keyword"].unique().tolist())
LATEST_DATE = df["date"].max()
latest_df = df[df["date"] == LATEST_DATE]


# ═══════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.title("📊 Simply Wall St — App Store Rankings")
st.caption(
    f"Tracking keyword & category positions across {len(ALL_COUNTRIES)} markets  ·  "
    f"Last updated **{LATEST_DATE.strftime('%B %d, %Y')}**"
)


# ═══════════════════════════════════════════════════════════════════════════
#  HERO SECTION — Trend Chart
# ═══════════════════════════════════════════════════════════════════════════
with st.container(border=True):
    # Default selections
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

    # Filter data for chart
    chart_data = df.copy()
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
            labels={
                "keyword_rank": "Rank Position",
                "date": "",
                "label": "",
            },
            color_discrete_sequence=px.colors.qualitative.Set2,
        )

        fig.update_yaxes(
            autorange="reversed",
            range=[200, 1],
            title="Rank Position",
            gridcolor="rgba(128,128,160,0.15)",
            showgrid=True,
        )
        fig.update_xaxes(
            gridcolor="rgba(128,128,160,0.1)",
            showgrid=True,
        )
        fig.update_layout(
            height=480,
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

        # Add rank=1 annotation line
        fig.add_hline(y=1, line_dash="dot", line_color="gold", opacity=0.4, annotation_text="#1")

        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TABBED SECTIONS
# ═══════════════════════════════════════════════════════════════════════════
tab_summary, tab_country = st.tabs(["🏆 Executive Summary", "🌍 Country Deep-Dive"])


# ── TAB 1: Executive Summary ───────────────────────────────────────────────
with tab_summary:
    st.markdown("#### Top 5 Best Keyword Rankings")
    st.caption("Highest-ranking keyword positions across all countries today.")

    ranked = latest_df.dropna(subset=["keyword_rank"]).copy()
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

    dates = sorted(df["date"].unique())
    if len(dates) < 2:
        st.info("Need at least 2 days of data to show movers. Check back tomorrow!")
    else:
        prev_date = dates[-2]
        prev_df = df[df["date"] == prev_date]

        movers = []
        for _, row in latest_df.iterrows():
            cur_rank = row["keyword_rank"]
            if pd.isna(cur_rank):
                continue
            match = prev_df[
                (prev_df["country"] == row["country"]) & (prev_df["keyword"] == row["keyword"])
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
                        "previous": int(prev_rank),
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

    cat_data = latest_df.drop_duplicates(subset=["country"])[["country", "category_rank"]].copy()
    cat_cols = st.columns(min(len(cat_data), 5))
    for i, (_, row) in enumerate(cat_data.iterrows()):
        cat_val = row["category_rank"]
        display = f"#{int(cat_val)}" if pd.notna(cat_val) else "—"
        with cat_cols[i % len(cat_cols)]:
            st.metric(label=f"{row['country']} — Finance", value=display)


# ── TAB 2: Country Deep-Dive ──────────────────────────────────────────────
with tab_country:
    selected_country = st.selectbox(
        "Select a country",
        options=ALL_COUNTRIES,
        format_func=lambda c: {"US": "🇺🇸 United States", "AU": "🇦🇺 Australia", "CA": "🇨🇦 Canada", "DE": "🇩🇪 Germany", "IN": "🇮🇳 India"}.get(c, c),
        key="deep_dive_country",
    )

    country_latest = latest_df[latest_df["country"] == selected_country]

    if country_latest.empty:
        st.info(f"No data available for {selected_country}.")
    else:
        # Category rank header
        cat_row = country_latest.iloc[0]
        cat_val = cat_row["category_rank"]
        cat_display = f"#{int(cat_val)}" if pd.notna(cat_val) else "—  Unranked"

        st.markdown(f"##### Finance Category: **{cat_display}**")
        st.divider()

        # Keyword grid — 3 columns
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
                    st.metric(
                        label=kw.title(),
                        value=display_val,
                        delta=delta,
                        delta_color=d_color,
                    )

        st.divider()

        # Mini trend chart for the selected country
        st.markdown(f"##### Trend — {selected_country}")
        country_hist = df[df["country"] == selected_country].dropna(subset=["keyword_rank"]).copy()

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
            fig3.update_yaxes(autorange="reversed", range=[200, 1], title="Rank", gridcolor="rgba(128,128,160,0.15)")
            fig3.update_xaxes(gridcolor="rgba(128,128,160,0.1)")
            fig3.update_layout(
                height=380,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            )
            st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
#  RAW DATA EXPANDER
# ═══════════════════════════════════════════════════════════════════════════
with st.expander("📋 Raw Data"):
    st.dataframe(
        df.sort_values(["date", "country", "keyword"], ascending=[False, True, True]),
        use_container_width=True,
        hide_index=True,
    )
