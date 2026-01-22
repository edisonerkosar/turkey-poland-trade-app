import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np

st.set_page_config(layout="wide")
st.title("Turkey ↔ EU Total Trade (2013–2024)")

# ---------- LOAD ----------
@st.cache_data
def load_trade():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "EU-TR_trade.xlsx")
    df = pd.read_excel(path)

    # EU → Turkey (A–E)
    eu_tr = df.iloc[:, 0:5]
    eu_tr.columns = ["Year", "Country", "Flow", "Partner", "Value"]

    # Turkey → EU (G–K)
    tr_eu = df.iloc[:, 6:11]
    tr_eu.columns = ["Year", "Country", "Flow", "Partner", "Value"]

    eu_tr["Direction"] = "EU_to_TR"
    tr_eu["Direction"] = "TR_to_EU"

    full = pd.concat([eu_tr, tr_eu], ignore_index=True)
    full = full[full["Country"].str.lower() != "turkey"]
    full = full[full["Country"].str.lower() != "türkiye"]

    full["Year"] = full["Year"].astype(int)
    full["Value"] = pd.to_numeric(full["Value"], errors="coerce").fillna(0)

    return full

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

countries = sorted(df["Country"].unique())
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
    data = df[df["Direction"] == "EU_to_TR"]

    elif metric == "Exports to EU from Turkey":
    data = df[df["Direction"] == "TR_to_EU"]

    else:  # Total Trade Volume
    pivot = (
        df.groupby(["Year", "Country", "Direction"])["Value"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Ensure both columns always exist
    if "EU_to_TR" not in pivot.columns:
        pivot["EU_to_TR"] = 0
    if "TR_to_EU" not in pivot.columns:
        pivot["TR_to_EU"] = 0

    pivot["Value"] = pivot["EU_to_TR"] + pivot["TR_to_EU"]
    data = pivot[["Year", "Country", "Value"]]

    # Ensure both columns always exist
    if "EU_to_TR" not in pivot.columns:
        pivot["EU_to_TR"] = 0
    if "TR_to_EU" not in pivot.columns:
        pivot["TR_to_EU"] = 0

    pivot["Value"] = pivot["EU_to_TR"] + pivot["TR_to_EU"]

    data = pivot[["Year", "Country", "Value"]]


# ---------- TIME SERIES (ALL COUNTRIES) ----------
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


ts = (
    data.groupby(["Year", "Country"], as_index=False)["Value"]
    .sum()
    .sort_values(["Country", "Year"])
)


fig = px.line(
    ts,
    x="Year",
    y="Value",
    color="Country",
    labels={"Value": "Trade Value (USD)", "Year": "Year"}
)

for trace in fig.data:
    if trace.name == "Poland":
        trace.update(line=dict(width=5))
    else:
        trace.update(line=dict(width=1, dash="dot"))

fig.update_layout(
    xaxis=dict(
        tickmode="array",
        tickvals=ALL_YEARS,
        showgrid=True
    ),
    yaxis_title="Trade Value (USD)",
    legend_title_text="EU Country"
)

st.plotly_chart(fig, width="stretch")

# ---------- CAGR ----------
st.subheader(cagr_title)

cagr_list = []

for c in ts["Country"].unique():
    sub = ts[ts["Country"] == c].sort_values("Year")

    start = sub[sub["Year"] == 2013]["Value"].sum()
    end = sub[sub["Year"] == 2024]["Value"].sum()

    if start > 0:
        years = 2024 - 2013
        cagr = (end / start) ** (1 / years) - 1
    else:
        cagr = np.nan

    cagr_list.append({"Country": c, "CAGR": cagr})

cagr_df = pd.DataFrame(cagr_list)

if cagr_df.empty or "CAGR" not in cagr_df.columns:
    st.warning("Not enough data to calculate CAGR for this selection.")
    st.stop()

cagr_df = (
    cagr_df
    .dropna(subset=["CAGR"])
    .sort_values("CAGR", ascending=False)
)

if cagr_df.empty:
    st.warning("Not enough data to calculate CAGR for this selection.")
    st.stop()


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
    data[data["Country"] == focus_country]
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
        data[data["Country"] == "Poland"]
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

fig.update_layout(
    legend_title_text="EU Country",
    legend=dict(
        itemclick="toggle",        # click to hide/show
        itemdoubleclick="toggleothers",
        orientation="v",
        x=1.02,
        y=1
    ),
    xaxis=dict(
        tickmode="array",
        tickvals=ALL_YEARS,
        showgrid=True
    )
)

st.plotly_chart(fig2, width="stretch")

# ---------- FOOTER ----------
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade (EU–Turkey bilateral trade, total imports)  
Cross-checked EU & Turkey reported flows  
""")
