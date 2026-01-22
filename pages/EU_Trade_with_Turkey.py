import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np

st.write(df.head())
st.write(df.columns)

st.set_page_config(layout="wide")
st.title("Turkey ↔ EU Total Trade (2013–2024)")

# ---------- LOAD ----------
@st.cache_data
def load_trade():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "EU-TR_trade.xlsx")

    df = pd.read_excel(path)

    df = df.rename(columns={
        "refYear": "Year",
        "Importer": "Importer",
        "Exporter": "Exporter",
        "primaryValue": "Value"
    })

    df["Year"] = df["Year"].astype(int)
    df["Importer"] = df["Importer"].astype(str)
    df["Exporter"] = df["Exporter"].astype(str)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

    return df

df = load_trade()

ALL_YEARS = list(range(2013, 2025))

# ---------- SIDEBAR ----------
st.sidebar.header("Filters")

metric = st.sidebar.selectbox(
    "Trade Measure",
    [
        "Total Trade Volume",
        "Exports to Turkey from EU",
        "Exports to EU from Turkey",
    ]
)

countries = sorted(
    pd.concat([df["Importer"], df["Exporter"]]).unique()
)

focus_country = st.sidebar.selectbox(
    "Focus Country",
    countries,
    index=countries.index("Poland") if "Poland" in countries else 0
)

compare_poland = st.sidebar.toggle(
    "Compare with Poland",
    value=False,
    disabled=(focus_country == "Poland")
)

# ---------- SELECT MEASURE ----------
if metric == "Exports to Turkey from EU":
    data = df[df["Importer"].str.lower() == "turkey"]

elif metric == "Exports to EU from Turkey":
    data = df[df["Exporter"].str.lower() == "turkey"]

else:  # Total Trade Volume
    eu_to_tr = df[df["Importer"].str.lower() == "turkey"]
    tr_to_eu = df[df["Exporter"].str.lower() == "turkey"]

    merged = pd.concat([eu_to_tr, tr_to_eu], ignore_index=True)

    data = (
        merged.groupby(["Year", "Importer"], as_index=False)["Value"]
        .sum()
    )

# ---------- TITLES ----------
if metric == "Total Trade Volume":
    main_title = "Trade Volume of Turkey with EU Countries Over Time"
    cagr_title = "CAGR of Total Trade with Turkey (2013–2024)"
elif metric == "Exports to Turkey from EU":
    main_title = "EU Exports to Turkey Over Time"
    cagr_title = "CAGR of Exports to Turkey by Country (2013–2024)"
else:
    main_title = "Turkey’s Exports to the EU Over Time"
    cagr_title = "CAGR of Turkey’s Exports to EU Countries (2013–2024)"

st.subheader(main_title)

# ---------- TIME SERIES ----------
ts = (
    data.groupby(["Year", "Importer"], as_index=False)["Value"]
    .sum()
)

if ts.empty:
    st.warning("No data available for this selection.")
    st.stop()

fig = px.line(
    ts,
    x="Year",
    y="Value",
    color="Importer",
    labels={"Value": "Trade Value (USD)", "Year": "Year"}
)

for trace in fig.data:
    if trace.name == "Poland":
        trace.update(line=dict(width=5))
    else:
        trace.update(line=dict(width=1, dash="dot"))

fig.update_layout(
    xaxis=dict(tickmode="array", tickvals=ALL_YEARS, showgrid=True),
    yaxis_title="Trade Value (USD)",
    legend_title_text="EU Country"
)

st.plotly_chart(fig, width="stretch")

# ---------- CAGR ----------
st.subheader(cagr_title)

cagr_list = []

for c in ts["Importer"].unique():
    sub = ts[ts["Importer"] == c].sort_values("Year")

    nonzero = sub[sub["Value"] > 0]
    if len(nonzero) < 2:
        continue

    start_row = nonzero.iloc[0]
    end_row = nonzero.iloc[-1]

    start = start_row["Value"]
    end = end_row["Value"]
    years = end_row["Year"] - start_row["Year"]

    if years > 0:
        cagr = (end / start) ** (1 / years) - 1
        cagr_list.append({"Country": c, "CAGR": cagr})

cagr_df = pd.DataFrame(cagr_list)

if cagr_df.empty:
    st.warning("Not enough data to calculate CAGR.")
else:
    cagr_df = cagr_df.sort_values("CAGR", ascending=False)

    fig_cagr = px.bar(
        cagr_df,
        x="Country",
        y="CAGR",
        labels={"CAGR": "CAGR (2013–2024)"}
    )
    st.plotly_chart(fig_cagr, width="stretch")

# ---------- FOCUS COUNTRY ----------
st.subheader(f"{focus_country} – Trade Over Time")

focus_ts = (
    data[data["Importer"] == focus_country]
    .groupby("Year", as_index=False)["Value"]
    .sum()
)

fig2 = px.line(
    focus_ts,
    x="Year",
    y="Value",
    labels={"Value": "Trade Value (USD)", "Year": "Year"},
    title=focus_country
)

if compare_poland and focus_country != "Poland":
    poland_ts = (
        data[data["Importer"] == "Poland"]
        .groupby("Year", as_index=False)["Value"]
        .sum()
    )

    fig2.add_scatter(
        x=poland_ts["Year"],
        y=poland_ts["Value"],
        mode="lines",
        name="Poland",
        line=dict(width=4, dash="dash")
    )

fig2.update_layout(
    xaxis=dict(tickmode="array", tickvals=ALL_YEARS, showgrid=True),
    yaxis_title="Trade Value (USD)"
)

st.plotly_chart(fig2, width="stretch")

# ---------- FOOTER ----------
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade – EU ↔ Turkey total trade  
""")
