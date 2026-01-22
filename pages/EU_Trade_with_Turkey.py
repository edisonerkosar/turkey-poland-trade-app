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
TURKEY_NAMES = ["türkiye", "turkey"]
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
    df.loc[~df["Importer"].str.lower().isin(TURKEY_NAMES), "Importer"]
    .unique()
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
TURKEY_NAMES = ["türkiye", "turkey"]

is_tr_importer = df["Importer"].str.lower().isin(TURKEY_NAMES)
is_tr_exporter = df["Exporter"].str.lower().isin(TURKEY_NAMES)

if metric == "Exports to Turkey from EU":
    data = df[is_tr_importer & (~is_tr_exporter)].copy()
    data["Country"] = data["Exporter"]

elif metric == "Exports to EU from Turkey":
    data = df[is_tr_exporter & (~is_tr_importer)].copy()
    data["Country"] = data["Importer"]

else:  # Total Trade Volume
    eu_to_tr = df[is_tr_importer & (~is_tr_exporter)].copy()
    eu_to_tr["Country"] = eu_to_tr["Exporter"]

    tr_to_eu = df[is_tr_exporter & (~is_tr_importer)].copy()
    tr_to_eu["Country"] = tr_to_eu["Importer"]

    combined = pd.concat([eu_to_tr, tr_to_eu], ignore_index=True)

    data = (
        combined.groupby(["Year", "Country"], as_index=False)["Value"]
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
    data.groupby(["Year", "Country"], as_index=False)["Value"]
    .sum()
)

if ts.empty:
    st.warning("No data available for this selection.")
    st.stop()

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
    xaxis=dict(tickmode="array", tickvals=ALL_YEARS, showgrid=True),
    yaxis_title="Trade Value (USD)",
    legend_title_text="EU Country"
)

st.plotly_chart(fig, width="stretch")

# ---------- CAGR ----------
st.subheader(cagr_title)

cagr_list = []

for c in ts["Country"].unique():
    sub = ts[ts["Country"] == c].sort_values("Year")

    nonzero = sub[sub["Value"] > 0]
    if len(nonzero) < 2:
        continue

    start_row = nonzero.iloc[0]
    end_row = nonzero.iloc[-1]

    start = start_row["Value"]
    end = end_row["Value"]
    years = end_row["Year"] - start_row["Year"]

    if years > 0:
        cagr = ((end / start) ** (1 / years) - 1) * 100
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
    labels={"CAGR": "CAGR % (2013–2024)"}
)
    fig_cagr.update_layout(
    yaxis_tickformat=".1f"
)
    st.plotly_chart(fig_cagr, width="stretch")

# ================= GROWTH vs SIZE MATRIX =================
st.subheader("Growth vs Size Matrix (EU–Turkey Trade)")

latest_year = 2024

# ---- SIZE: latest trade volume ----
size_df = (
    ts[ts["Year"] == latest_year]
    .groupby("Country", as_index=False)["Value"]
    .sum()
    .rename(columns={"Value": "Size"})
)

# ---- MERGE with CAGR ----
matrix = pd.merge(size_df, cagr_df, on="Country", how="inner")

if matrix.empty:
    st.warning("Not enough data to build Growth vs Size matrix.")
else:
    fig_matrix = px.scatter(
        matrix,
        x="Size",
        y="CAGR",
        size=np.sqrt(matrix["Size"]),
        color="Country",
        hover_name="Country",
        labels={
            "Size": f"Trade Volume in {latest_year} (USD)",
            "CAGR": "CAGR % (2013–2024)"
        },
        size_max=45
    )

    # Highlight Poland
    for trace in fig_matrix.data:
        if trace.name == "Poland":
            trace.update(marker=dict(size=20, line=dict(width=3, color="black")))
        else:
            trace.update(marker=dict(opacity=0.6))

    fig_matrix.update_layout(
        xaxis_title=f"Trade Volume in {latest_year} (USD)",
        yaxis_title="CAGR % (2013–2024)",
        legend_title_text="EU Country"
    )

    fig_matrix.update_xaxes(type="log")
    st.plotly_chart(fig_matrix, width="stretch")

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
