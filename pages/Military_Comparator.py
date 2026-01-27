import streamlit as st
import pandas as pd
import plotly.express as px
import os
import itertools

EXPORT_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToAdd": ["toImage"],
    "toImageButtonOptions": {
        "format": "svg",
        "filename": "military_trade_chart",
        "height": 800,
        "width": 1200,
        "scale": 3
    }
}

st.set_page_config(layout="wide")
st.title("Turkey → EU Military Trade Comparator (HS Codes, 2013–2024)")

# ---------- LOAD ----------
@st.cache_data
def load_military_data():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "..", "data", "EURMTR_Final.xlsx")

    df = pd.read_excel(path)
    df["refYear"] = df["refYear"].astype(int)
    df["cmdCode"] = df["cmdCode"].astype(str).str.strip()
    df["Importer"] = df["Importer"].astype(str)
    df["primaryValue"] = pd.to_numeric(df["primaryValue"], errors="coerce").fillna(0)
    return df

df = load_military_data()
# ---------- DYNAMIC COLOR MAP FOR ALL HS CODES ----------
base_palette = px.colors.qualitative.Set2
unique_codes = sorted(df["cmdCode"].unique())

HS_COLORS = {
    code: base_palette[i % len(base_palette)]
    for i, code in enumerate(unique_codes)
}
ALL_YEARS = list(range(2013, 2025))

# ---------- HS4 MAP ----------
hs_map = {
    "8710": "Tanks and other armoured fighting vehicles",
    "8802": "Aircraft & Helicopters",
    "880699": "UAV, with mass > 150 kg",
    "9301": "Military Weapons",
    "9302": "Revolvers & Pistols",
    "9306": "Bombs, grenades, torpedoes, mines, missiles and similar munitions of war",
    "8906": "Warships & Naval Vessels"
}

# ---------- SIDEBAR ----------
st.sidebar.header("View")

view_mode = st.sidebar.radio(
    "View Mode",
    ["Home (EU Comparison)", "Country Focus"]
)

hs_selected = st.sidebar.multiselect(
    "Select Military HS Codes",
    options=sorted(df["cmdCode"].unique()),
    default=sorted(df["cmdCode"].unique()),
    format_func=lambda x: f"{x} – {hs_map.get(x, 'Other military equipment')}"
)

df = df[df["cmdCode"].isin(hs_selected)]

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
    fig.update_layout(
        title=dict(
            text="EU Comparison – Total Military Imports from Turkey",
            x=0.5,
            xanchor="center",
            font=dict(size=20)
        )
    )

    for trace in fig.data:
        if trace.name == "Poland":
            trace.update(line=dict(width=5))
        else:
            trace.update(line=dict(width=1, dash="dot"))

    fig.update_layout(
        legend_title_text="EU Country",
        yaxis_title="Trade Value (USD)",
        xaxis=dict(
            tickmode="array",
            tickvals=ALL_YEARS,
            ticktext=[str(y) for y in ALL_YEARS],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)"
        ),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=EXPORT_CONFIG
    )
    # ----- RANKING -----
    rank_year = st.selectbox(
        "Ranking Year",
        ALL_YEARS,
        index=len(ALL_YEARS) - 1
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
    fig_rank.update_layout(
        title=dict(
            text=f"EU Ranking by Military Imports from Turkey ({rank_year})",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        )
    )
    st.plotly_chart(
        fig_rank,
        use_container_width=True,
        config=EXPORT_CONFIG
    )
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

    # -------- TIME SERIES --------
    country_sum = (
        df[df["Importer"] == focus_country]
        .groupby("refYear", as_index=False)["primaryValue"]
        .sum()
    )

    fig = px.line(
        country_sum,
        x="refYear",
        y="primaryValue",
        labels={"primaryValue": "Trade Value (USD)", "refYear": "Year"}
    )

    fig.update_layout(
        title=dict(
            text=f"{focus_country} – Military Imports from Turkey",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        )
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

    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=ALL_YEARS,
            ticktext=[str(y) for y in ALL_YEARS],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)"
        ),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=EXPORT_CONFIG
    )

    # -------- PIE COMPOSITION --------
    st.subheader("Military Import Structure by Product")

    pie_year = st.selectbox(
        "Select Year for Composition",
        ALL_YEARS,
        index=len(ALL_YEARS) - 1
    )

    col1, col2 = st.columns(2)

    pie_focus = (
        df[(df["Importer"] == focus_country) & (df["refYear"] == pie_year)]
        .groupby("cmdCode", as_index=False)["primaryValue"]
        .sum()
    )

    with col1:
        st.markdown(f"### {focus_country} ({pie_year})")
        if pie_focus.empty:
            st.info(f"No data for {focus_country} in {pie_year}.")
        else:
            fig_pie = px.pie(
                pie_focus,
                names="cmdCode",
                values="primaryValue",
                hole=0.4,
                color="cmdCode",
                color_discrete_map=HS_COLORS
            )
            fig_pie.update_layout(
                title=dict(
                    text=f"{focus_country} – Structure ({pie_year})",
                    x=0.5,
                    xanchor="center",
                    font=dict(size=16)
                )
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    if compare_poland and focus_country != "Poland":
        pie_poland = (
            df[(df["Importer"] == "Poland") & (df["refYear"] == pie_year)]
            .groupby("cmdCode", as_index=False)["primaryValue"]
            .sum()
        )

        with col2:
            st.markdown(f"### Poland ({pie_year})")
            if pie_poland.empty:
                st.info(f"No data for Poland in {pie_year}.")
            else:
                fig_pie_pl = px.pie(
                    pie_poland,
                    names="cmdCode",
                    values="primaryValue",
                    hole=0.4,
                    color="cmdCode",
                    color_discrete_map=HS_COLORS
                )
                fig_pie_pl.update_layout(
                    title=dict(
                        text=f"Poland – Structure ({pie_year})",
                        x=0.5,
                        xanchor="center",
                        font=dict(size=16)
                    )
                )
                st.plotly_chart(fig_pie_pl, use_container_width=True)

    # -------- HS4 LEGEND --------
    st.markdown("#### HS Code Descriptions")

    active_codes = set(pie_focus["cmdCode"])
    if compare_poland and focus_country != "Poland" and not pie_poland.empty:
        active_codes = active_codes.union(set(pie_poland["cmdCode"]))

    for code, desc in hs_map.items():
        if code in active_codes:
            color = HS_COLORS.get(code, "#FFFFFF")
            st.markdown(
                f"<span style='color:{color}; font-weight:600'>{code}</span> – {desc}",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<span style='color:#666666'>{code}</span> – {desc}",
                unsafe_allow_html=True
            )

# ---------- FOOTER ----------
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Data Source:**  
UN Comtrade (cross-checked EU import & Turkey export records)  
HS4 military categories only  
""")
