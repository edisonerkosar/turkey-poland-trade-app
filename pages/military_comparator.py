import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title("Turkey → EU Military Trade Comparator (HS4, 2013–2024)")

# ---------- LOAD ----------
@st.cache_data
def load_military_data():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "EURMTR_Final.xlsx")

    df = pd.read_excel(path)

    df["refYear"] = df["refYear"].astype(int)
    df["cmdCode"] = df["cmdCode"].astype(str).str.zfill(4)
    df["Importer"] = df["Importer"].astype(str)
    df["primaryValue"] = pd.to_numeric(df["primaryValue"], errors="coerce").fillna(0)

    return df

df = load_military_data()

# ---------- HS4 MAP ----------
hs4_map = {
    "8701": "Tanks & Armoured Vehicles",
    "8802": "Military Aircraft & Helicopters",
    "8803": "Aircraft Parts",
    "8906": "Warships & Naval Vessels",
    "9301": "Military Weapons",
    "9302": "Revolvers & Pistols",
    "9306": "Ammunition"
}

# ---------- SIDEBAR ----------
st.sidebar.header("View")

view_mode = st.sidebar.radio(
    "View Mode",
    ["Home (EU Comparison)", "Country Focus"]
)

hs4_selected = st.sidebar.multiselect(
    "Select Military HS4 Codes",
    options=list(hs4_map.keys()),
    default=list(hs4_map.keys()),
    format_func=lambda x: f"{x} – {hs4_map[x]}"
)

df = df[df["cmdCode"].isin(hs4_selected)]

if df.empty:
    st.warning("No data for selected HS4 codes.")
    st.stop()

# ================= HOME =================
if view_mode == "Home (EU Comparison)":

    st.subheader("EU Comparison – Total Military Imports from Turkey")

    home = (
        df.groupby(["refYear", "Importer"], as_index=False)["primaryValue"]
        .sum()
    )

    fig = px.line(
        home,
        x="refYear",
        y="primaryValue",
        color="Importer",
        labels={"primaryValue": "Trade Value (USD)", "refYear": "Year"}
    )

    for trace in fig.data:
        if trace.name == "Poland":
            trace.update(line=dict(width=5))
        else:
            trace.update(line=dict(width=1, dash="dot"))

    fig.update_layout(
        legend_title_text="EU Country",
        yaxis_title="Trade Value (USD)"
    )

    st.plotly_chart(fig, width="stretch")

    # ----- RANKING -----
    rank_year = st.selectbox(
        "Ranking Year",
        sorted(df["refYear"].unique()),
        index=len(sorted(df["refYear"].unique())) - 1
    )

    st.subheader(f"EU Ranking by Military Imports from Turkey ({rank_year})")

    ranking = (
        df[df["refYear"] == rank_year]
        .groupby("Importer", as_index=False)["primaryValue"]
        .sum()
        .sort_values("primaryValue", ascending=False)
    )

    fig_rank = px.bar(
        ranking,
        x="Importer",
        y="primaryValue",
        labels={"primaryValue": "Trade Value (USD)"}
    )

    st.plotly_chart(fig_rank, width="stretch")

# ================= COUNTRY =================
else:
    st.sidebar.header("Country View")

    countries = sorted(df["Importer"].unique())
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

    st.subheader(f"{focus_country} – Total Military Imports from Turkey")

    # -------- TIME SERIES (SUM OF SELECTED HS4) --------
    country_sum = (
        df[df["Importer"] == focus_country]
        .groupby("refYear", as_index=False)["primaryValue"]
        .sum()
    )

    fig = px.line(
        country_sum,
        x="refYear",
        y="primaryValue",
        labels={"primaryValue": "Trade Value (USD)", "refYear": "Year"},
        title=f"{focus_country} – Military Imports from Turkey"
    )

    if compare_poland and focus_country != "Poland":
        poland = (
            df[df["Importer"] == "Poland"]
            .groupby("refYear", as_index=False)["primaryValue"]
            .sum()
        )

        fig.add_scatter(
            x=poland["refYear"],
            y=poland["primaryValue"],
            mode="lines",
            name="Poland",
            line=dict(width=4, dash="dash")
        )

    st.plotly_chart(fig, width="stretch")

    # -------- PIE COMPOSITION --------
    st.subheader("Military Import Structure by Product")

    pie_year = st.selectbox(
        "Select Year for Composition",
        sorted(df["refYear"].unique()),
        index=len(sorted(df["refYear"].unique())) - 1
    )

    col1, col2 = st.columns(2)

    # ---- FOCUS COUNTRY PIE ----
    pie_focus = (
        df[(df["Importer"] == focus_country) & (df["refYear"] == pie_year)]
        .groupby("cmdCode", as_index=False)["primaryValue"]
        .sum()
    )

    with col1:
        st.markdown(f"### {focus_country} ({pie_year})")
        fig_pie = px.pie(
            pie_focus,
            names="cmdCode",
            values="primaryValue",
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---- POLAND PIE (OPTIONAL) ----
    if compare_poland and focus_country != "Poland":
        pie_poland = (
            df[(df["Importer"] == "Poland") & (df["refYear"] == pie_year)]
            .groupby("cmdCode", as_index=False)["primaryValue"]
            .sum()
        )

        with col2:
            st.markdown(f"### Poland ({pie_year})")
            fig_pie_pl = px.pie(
                pie_poland,
                names="cmdCode",
                values="primaryValue",
                hole=0.4
            )
            st.plotly_chart(fig_pie_pl, use_container_width=True)

    # -------- HS4 LEGEND --------
st.markdown("#### HS4 Code Descriptions (Color Matched)")

# --- safely extract colors from the actual pie ---
# --- extract colors from the ACTUAL rendered pie ---
color_map = {}

if not pie_focus.empty:
    real_trace = fig_pie.data[0]

    labels = list(real_trace.labels)

    if real_trace.marker.colors is None:
        colors = px.colors.qualitative.Plotly
        colors = (colors * (len(labels) // len(colors) + 1))[:len(labels)]
    else:
        colors = list(real_trace.marker.colors)

    for lbl, col in zip(labels, colors):
        color_map[lbl] = col

# --- render legend text ---
for code in pie_focus["cmdCode"]:
    color = color_map.get(code, "#FFFFFF")
    desc = hs4_map.get(code, "Description not available")

    st.markdown(
        f"<span style='color:{color}; font-weight:600'>{code}</span> – {desc}",
        unsafe_allow_html=True
    )
# ---------- FOOTER ----------
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade (cross-checked EU import & Turkey export records)  
HS4 military categories only  
""")
