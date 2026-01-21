import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")

st.title("Turkey – EU Military Trade Comparator (2013–2024)")

@st.cache_data
def load_military_data():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "Rebuilt_Military_Trade_EU.xlsx")

    df = pd.read_excel(path, engine="openpyxl")

    st.write("DEBUG – Columns in raw file:")
    st.write(df.columns)

    # Try to auto-detect trade value column
    value_col = None

    for col in df.columns:
        if "Trade" in col and "Value" in col:
            value_col = col

    if value_col is None:
        st.error("Could not detect trade value column in dataset")
        st.stop()

    df = df.rename(columns={
        "Reporter": "Country",
        "Commodity Code": "HS6",
        value_col: "Final_Value"
    })

    # Create HS levels
    df["HS6"] = df["HS6"].astype(str).str.zfill(6)
    df["HS4"] = df["HS6"].str[:4]
    df["HS2"] = df["HS6"].str[:2]

    # Create compatibility columns
    df["Turkey_Reported_Value"] = df["Final_Value"]
    df["EU_Reported_Value"] = df["Final_Value"]
    df["Discrepancy"] = 0

    return df

st.write(df.columns)
df = load_military_data()
st.write("DEBUG – Actual dataset columns:")
st.write(df.columns)

st.write("DEBUG – First rows:")
st.write(df.head())
st.sidebar.header("Filters")

country = st.sidebar.selectbox(
    "Select EU Country",
    sorted(df["Country"].unique())
)

level = st.sidebar.selectbox(
    "Aggregation Level",
    ["HS6", "HS4", "HS2"]
)

metric = st.sidebar.selectbox(
    "Value Source",
    ["Final_Value", "Turkey_Reported_Value", "EU_Reported_Value"]
)

data = df[df["Country"] == country]

if data.empty:
    st.warning("No data available for selected country.")
    st.stop()

st.subheader(f"Military-Related Trade: Turkey ↔ {country}")

# ---- TOP CATEGORIES ----
latest_year = data["Year"].max()

st.subheader(f"Top {level} Categories in {latest_year}")

top = (
    data[data["Year"] == latest_year]
    .groupby(level, as_index=False)[metric]
    .sum()
    .sort_values(metric, ascending=False)
    .head(10)
)

fig_top = px.bar(
    top,
    x=level,
    y=metric,
    text_auto=True,
    labels={metric: "Trade Value (USD)"}
)

fig_top.update_layout(
    xaxis_title="HS Code",
    yaxis_title="Trade Value (USD)",
    xaxis=dict(type="category")
)

st.plotly_chart(fig_top, width="stretch")


# ---- TIME SERIES ----

st.subheader("Trade Over Time")

grouped = data.groupby(["Year", level], as_index=False)[metric].sum()

all_years = list(range(2013, 2025))

complete = []

for c in grouped[level].unique():

    subset = grouped[grouped[level] == c]

    full = pd.DataFrame({
        "Year": all_years,
        level: c
    })

    merged = full.merge(subset, on=["Year", level], how="left")
    merged[metric] = merged[metric].fillna(0)

    complete.append(merged)

chart_data = pd.concat(complete, ignore_index=True)

fig = px.line(
    chart_data,
    x="Year",
    y=metric,
    color=level,
    labels={metric: "Trade Value (USD)"}
)

fig.update_layout(
    yaxis_title="Trade Value (USD)",
    xaxis=dict(
        tickmode="array",
        tickvals=all_years,
        ticktext=[str(y) for y in all_years]
    )
)

st.plotly_chart(fig, width="stretch")


# ---- RANKING COMPARISON ----

st.subheader("EU Country Ranking – Military Trade with Turkey")

rank = (
    df[df["Year"] == latest_year]
    .groupby("Country", as_index=False)[metric]
    .sum()
    .sort_values(metric, ascending=False)
)

fig_rank = px.bar(
    rank,
    x="Country",
    y=metric,
    labels={metric: "Trade Value (USD)"}
)

fig_rank.update_layout(
    xaxis_title="EU Country",
    yaxis_title="Trade Value (USD)"
)

st.plotly_chart(fig_rank, width="stretch")


# ---- DISCREPANCY ANALYSIS ----

st.subheader("Reporting Discrepancies")

disc = data.groupby("Year", as_index=False)["Discrepancy"].sum()

fig_disc = px.bar(
    disc,
    x="Year",
    y="Discrepancy",
    labels={"Discrepancy": "Turkey – EU Reporting Gap (USD)"}
)

fig_disc.update_layout(
    xaxis=dict(
        tickmode="array",
        tickvals=all_years,
        ticktext=[str(y) for y in all_years]
    )
)

st.plotly_chart(fig_disc, width="stretch")


st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade Database  
Processed military-related HS codes  
https://comtradeplus.un.org/
""")
