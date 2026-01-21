import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")

st.title("Turkey → EU Military Trade Comparator (HS4, 2013–2024)")

@st.cache_data
def load_military_data():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "EURMTR_Final.xlsx")

    df = pd.read_excel(path)

    # Standardize
    df["refYear"] = df["refYear"].astype(int)
    df["cmdCode"] = df["cmdCode"].astype(str).str.zfill(4)
    df["Importer"] = df["Importer"].astype(str)
    df["primaryValue"] = pd.to_numeric(df["primaryValue"], errors="coerce").fillna(0)

    return df

df = load_military_data()

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filters")

countries = sorted(df["Importer"].unique())
focus_country = st.sidebar.selectbox("Focus Country", countries, index=countries.index("Poland") if "Poland" in countries else 0)

codes = sorted(df["cmdCode"].unique())
selected_codes = st.sidebar.multiselect(
    "HS4 Military Codes",
    options=codes,
    default=codes
)

# ---------------- FILTER ----------------
data = df[df["cmdCode"].isin(selected_codes)]

if data.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ---------------- MAIN COMPARISON ----------------
st.subheader("EU Comparison – Total Military Imports from Turkey")

total_by_country_year = (
    data.groupby(["refYear", "Importer"], as_index=False)["primaryValue"].sum()
)

fig = px.line(
    total_by_country_year,
    x="refYear",
    y="primaryValue",
    color="Importer",
    labels={"primaryValue": "Trade Value (USD)", "refYear": "Year"},
)

# Make Poland bold
for trace in fig.data:
    if trace.name == focus_country:
        trace.update(line=dict(width=5))
    else:
        trace.update(line=dict(width=1, dash="dot"))

fig.update_layout(
    yaxis_title="Trade Value (USD)",
    xaxis=dict(
        tickmode="array",
        tickvals=sorted(total_by_country_year["refYear"].unique())
    ),
    legend_title_text="EU Country",
)

st.plotly_chart(fig, width="stretch")

# ---------------- RANKING ----------------
latest_year = data["refYear"].max()

st.subheader(f"EU Ranking by Military Imports from Turkey ({latest_year})")

ranking = (
    data[data["refYear"] == latest_year]
    .groupby("Importer", as_index=False)["primaryValue"].sum()
    .sort_values("primaryValue", ascending=False)
)

fig_rank = px.bar(
    ranking,
    x="Importer",
    y="primaryValue",
    labels={"primaryValue": "Trade Value (USD)"},
)

fig_rank.update_layout(
    xaxis_title="EU Country",
    yaxis_title="Trade Value (USD)",
)

st.plotly_chart(fig_rank, width="stretch")

# ---------------- COUNTRY DETAIL ----------------
st.subheader(f"{focus_country} – Military Imports from Turkey by Product")

country_data = data[data["Importer"] == focus_country]

by_product = (
    country_data
    .groupby(["refYear", "cmdCode"], as_index=False)["primaryValue"].sum()
)

fig_prod = px.line(
    by_product,
    x="refYear",
    y="primaryValue",
    color="cmdCode",
    labels={"primaryValue": "Trade Value (USD)", "refYear": "Year", "cmdCode": "HS4"},
)

fig_prod.update_layout(
    yaxis_title="Trade Value (USD)",
    xaxis=dict(
        tickmode="array",
        tickvals=sorted(by_product["refYear"].unique())
    ),
)

st.plotly_chart(fig_prod, width="stretch")

# ---------------- TOP PRODUCTS ----------------
st.subheader(f"Top Military HS4 Codes in {latest_year}")

top_products = (
    data[data["refYear"] == latest_year]
    .groupby("cmdCode", as_index=False)["primaryValue"].sum()
    .sort_values("primaryValue", ascending=False)
)

fig_top = px.bar(
    top_products,
    x="cmdCode",
    y="primaryValue",
    labels={"primaryValue": "Trade Value (USD)", "cmdCode": "HS4"},
)

fig_top.update_layout(
    xaxis_title="HS4 Code",
    yaxis_title="Trade Value (USD)",
)

st.plotly_chart(fig_top, width="stretch")

# ---------------- FOOTER ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade (cross-checked EU import & Turkey export records)  
HS4 military categories only  
""")
