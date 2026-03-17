"""
Streamlit dashboard for Simply Wall St App Store ranking trends.
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rankings_history.csv")

st.set_page_config(page_title="Simply Wall St - App Store Rankings", layout="wide")
st.title("Simply Wall St - App Store Ranking Tracker")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE)
    df["date"] = pd.to_datetime(df["date"])
    df["keyword_rank"] = pd.to_numeric(df["keyword_rank"], errors="coerce")
    df["category_rank"] = pd.to_numeric(df["category_rank"], errors="coerce")
    return df


# ---------- Load data ----------
if not os.path.exists(CSV_FILE):
    st.error("No data file found. Run `python tracker.py` first.")
    st.stop()

df = load_data()

if df.empty:
    st.warning("No ranking data yet. Run `python tracker.py` to collect the first batch.")
    st.stop()

# ---------- Filters ----------
col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    selected_country = st.selectbox("Country", options=["All"] + sorted(df["country"].unique().tolist()))

with col_filter2:
    selected_keyword = st.selectbox("Keyword", options=["All"] + sorted(df["keyword"].unique().tolist()))

filtered = df.copy()
if selected_country != "All":
    filtered = filtered[filtered["country"] == selected_country]
if selected_keyword != "All":
    filtered = filtered[filtered["keyword"] == selected_keyword]

# ---------- Finance Category Ranking ----------
st.subheader("Finance Category Ranking")

latest_date = filtered["date"].max()
latest = filtered[filtered["date"] == latest_date]

if latest.empty:
    st.info("No data for the selected filters.")
else:
    # Category rank is the same for all keywords in a country, so deduplicate
    cat_data = latest.drop_duplicates(subset=["country"])[["country", "category_rank"]].copy()
    cat_cols = st.columns(min(len(cat_data), 5))
    for i, (_, row) in enumerate(cat_data.iterrows()):
        cat_val = row["category_rank"]
        display = int(cat_val) if pd.notna(cat_val) else "N/A"

        # Delta from previous day
        prev_cat = filtered[
            (filtered["date"] < latest_date) & (filtered["country"] == row["country"])
        ].drop_duplicates(subset=["country", "date"]).sort_values("date")
        delta = None
        delta_color = "off"
        if not prev_cat.empty:
            prev_val = prev_cat.iloc[-1]["category_rank"]
            if pd.notna(prev_val) and pd.notna(cat_val):
                change = int(prev_val - cat_val)
                if change != 0:
                    delta = f"{'+' if change > 0 else ''}{change}"
                    delta_color = "normal"

        with cat_cols[i % len(cat_cols)]:
            st.metric(label=f"{row['country']} - Finance", value=display, delta=delta, delta_color=delta_color)

# ---------- Keyword Rankings ----------
st.subheader("Keyword Rankings")

if latest.empty:
    st.info("No data for the selected filters.")
else:
    metric_cols = st.columns(min(len(latest), 5))
    for i, (_, row) in enumerate(latest.iterrows()):
        rank_val = row["keyword_rank"]
        label = f"{row['country']} - {row['keyword']}"
        display = int(rank_val) if pd.notna(rank_val) else "N/A"

        # Calculate delta from previous day if available
        prev = filtered[
            (filtered["date"] < latest_date)
            & (filtered["country"] == row["country"])
            & (filtered["keyword"] == row["keyword"])
        ]
        delta = None
        delta_color = "off"
        if not prev.empty:
            prev_rank = prev.sort_values("date").iloc[-1]["keyword_rank"]
            if pd.notna(prev_rank) and pd.notna(rank_val):
                change = int(prev_rank - rank_val)  # positive = improved
                if change != 0:
                    delta = f"{'+' if change > 0 else ''}{change}"
                    delta_color = "normal"  # green for positive (rank improved)

        col_idx = i % len(metric_cols)
        with metric_cols[col_idx]:
            st.metric(label=label, value=display, delta=delta, delta_color=delta_color)

# ---------- Charts ----------
tab_keyword, tab_category = st.tabs(["Keyword Rank Trend", "Category Rank Trend"])

with tab_keyword:
    if filtered[filtered["keyword_rank"].notna()].empty:
        st.info("No keyword ranking data to chart for the selected filters.")
    else:
        chart_df = filtered.dropna(subset=["keyword_rank"]).copy()
        chart_df["label"] = chart_df["country"] + " | " + chart_df["keyword"]

        fig = px.line(
            chart_df,
            x="date",
            y="keyword_rank",
            color="label",
            markers=True,
            labels={"keyword_rank": "Rank", "date": "Date", "label": "Country | Keyword"},
        )
        fig.update_yaxes(autorange="reversed", title="Rank (lower is better)")
        fig.update_layout(height=500, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

with tab_category:
    cat_chart = filtered.drop_duplicates(subset=["date", "country"]).dropna(subset=["category_rank"]).copy()
    if cat_chart.empty:
        st.info("No category ranking data to chart for the selected filters.")
    else:
        fig2 = px.line(
            cat_chart,
            x="date",
            y="category_rank",
            color="country",
            markers=True,
            labels={"category_rank": "Finance Category Rank", "date": "Date", "country": "Country"},
        )
        fig2.update_yaxes(autorange="reversed", title="Rank (lower is better)")
        fig2.update_layout(height=500, hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

# ---------- Raw data ----------
with st.expander("Raw Data"):
    st.dataframe(filtered.sort_values(["date", "country", "keyword"], ascending=[False, True, True]))
