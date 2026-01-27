import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")

st.title("Turkey–Poland Trade Explorer (2013–2024)")


@st.cache_data(ttl=3600)
def load_data():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "data", "Unified_Trade_CLEAN_rebuilt.xlsx")

    df = pd.read_excel(path, engine="openpyxl")

    # --- normalize column names ---
    df.columns = df.columns.str.strip()

    # map possible variants to standard names
    rename_map = {
    "HS4 Desc": "HS4Desc",
    "HS4 description": "HS4Desc",
    "HS4Description": "HS4Desc",
    "HS4_desc": "HS4Desc",

    "HS2 Desc": "HS2Desc",
    "HS2 description": "HS2Desc",
    "HS2Description": "HS2Desc",
    "HS2_desc": "HS2Desc",
    }

    df = df.rename(columns=rename_map)
    for col in ["HS_Description", "HS4Desc", "HS2Desc"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("Unknown").str.strip()

    df["HS6"] = df["HS6"].astype(str).str.zfill(6)
    df["HS4"] = df["HS4"].astype(str).str.zfill(4)
    df["HS2"] = df["HS2"].astype(str).str.zfill(2)
    return df

DESC_MAP = {
    "HS6": ["HS6", "HS_Description"],
    "HS4": ["HS4", "HS4Desc"],
    "HS2": ["HS2", "HS2Desc"]
}

def project_series_cagr(df_series):
    df_series = df_series.sort_values("Year")

    recent = df_series[df_series["Year"] >= 2020]

    if len(recent) < 2:
        return None

    start = recent.iloc[0]["Final_FOB_Value"]
    end = recent.iloc[-1]["Final_FOB_Value"]

    if start <= 0:
        return None

    years = recent.iloc[-1]["Year"] - recent.iloc[0]["Year"]

    if years == 0:
        return None

    cagr = (end / start) ** (1 / years) - 1

    cagr = max(min(cagr, 0.35), -0.35)

    projections = []

    last_value = df_series.iloc[-1]["Final_FOB_Value"]
    last_year = int(df_series.iloc[-1]["Year"])

    for y in range(last_year + 1, 2031):
        last_value = last_value * (1 + cagr)
        projections.append({
            "Year": y,
            "Final_FOB_Value": max(last_value, 0)
        })

    return pd.DataFrame(projections)


df = load_data()

st.sidebar.header("Filters")

direction = st.sidebar.selectbox(
    "Trade Direction",
    ["Turkey to Poland", "Poland to Turkey"]
)

direction_key = direction.replace(" ", "_")
data = df[df["Direction"] == direction_key]

level = st.sidebar.selectbox(
    "Aggregation Level",
    ["HS6", "HS4", "HS2"]
)
show_projection = st.sidebar.checkbox("Show Trend Projections to 2030")

code_col, desc_col = DESC_MAP[level]

options = data[[code_col, desc_col]].drop_duplicates()
options[desc_col] = options[desc_col].fillna("Unknown").astype(str)

display = options[code_col].astype(str) + " – " + options[desc_col]


selected = st.sidebar.selectbox(
    "Search by Code or Description",
    ["Home"] + list(display)
)
if st.sidebar.button("Reset to Home"):
    selected = "Home"

if selected == "Home":
    
    st.markdown("""
    **About this tool:**  
    This application was developed as part of Master's thesis research on decision support systems, basing on the Turkey–Poland trade relations.  
    Data reflects officially reported trade flows from UN Comtrade.
    """)

# ---- Define code variable if something is selected ----
if selected != "Home":
    code = selected.split(" – ")[0]
    data = data[data[level] == code]

# ---- Safety check ----
if data.empty:
    st.warning("No trade data available for the selected filters.")
    st.stop()

# ---- Define latest_year BEFORE top-10 block ----
latest_year = data["Year"].max()

# ---- TOP 10 BLOCK ----
if selected == "Home":

    default = data[data["Year"] == latest_year]

    top10 = (
        default.groupby(level, as_index=False)["Final_FOB_Value"]
        .sum()
        .sort_values("Final_FOB_Value", ascending=False)
        .head(10)
    )

    top10[level] = top10[level].astype(str)   # 👈 force text

    fig_default = px.bar(
        top10,
        x=level,
        y="Final_FOB_Value",
        text_auto=True,
        labels={"Final_FOB_Value": "Trade Value (USD)"},
        category_orders={level: list(top10[level])}
    )

    fig_default.update_xaxes(type="category")

    fig_default.update_layout(
        title=dict(
            text=f"Top 10 {level} Categories in {latest_year}",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        )
    )
    st.plotly_chart(
        fig_default,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToAdd": ["toImage"],
            "toImageButtonOptions": {
                "format": "svg",      # or "png"
                "filename": "top10_trade" if selected == "Home" else f"{code}_{direction_key}_timeseries",
                "height": 800,
                "width": 1200,
                "scale": 3
        }
    }
)
# ---- HS6 DESCRIPTIONS ----
if selected == "Home":

    st.markdown("#### HS Code Descriptions")

    desc_source = options
    codes = top10[level]

    for c in codes:
        row = desc_source[desc_source[level] == c]
        if not row.empty:
            desc = row.iloc[0].iloc[1]
        else:
            desc = "Description not available"

        st.markdown(f"**{c}** – {desc}")

# ---- TIME SERIES GRAPH ----

all_years = list(range(2013, 2025))
proj_years = list(range(2025, 2031))

if selected == "Home":
    top_codes = list(top10[level])
    data_for_chart = data[data[level].isin(top_codes)]
else:
    data_for_chart = data

grouped = data_for_chart.groupby(["Year", level], as_index=False)["Final_FOB_Value"].sum()

# Check if we have enough data at all

complete = []

for c in grouped[level].unique():

    subset = grouped[grouped[level] == c]

    # Only warn about projections when they are requested
    if show_projection and subset[subset["Final_FOB_Value"] > 0].shape[0] < 2:
        st.info(f"Not enough data to create projections for code {c}. Showing historical data only.")

    # HISTORICAL PART – only up to 2024
    hist_full = pd.DataFrame({
        "Year": all_years,
        level: c
    })

    hist = hist_full.merge(subset, on=["Year", level], how="left")
    hist["Final_FOB_Value"] = hist["Final_FOB_Value"].fillna(0)
    hist["Segment"] = "Historical"

    if show_projection:
        proj = project_series_cagr(subset)

        if proj is not None and not proj.empty:

            last_hist = subset.sort_values("Year").iloc[-1:]
            last_hist = last_hist.copy()
            last_hist["Segment"] = "Projection"

            proj[level] = c
            proj["Segment"] = "Projection"

            merged_proj = pd.concat([last_hist, proj], ignore_index=True)

            merged = pd.concat([hist, merged_proj], ignore_index=True)
        else:
            merged = hist
    else:
        merged = hist

    complete.append(merged)


if not complete:
    st.warning("Not enough data available to generate chart for this selection.")
    st.stop()

chart_data = pd.concat(complete, ignore_index=True)
chart_data = chart_data.sort_values("Year")

if selected == "Home":
    title_text = f"Trade Value of Top 10 Best Performing {level} Categories Over Time"
else:
    if direction == "Turkey to Poland":
        flow = "from Turkey to Poland"
    else:
        flow = "from Poland to Turkey"

    title_text = f"Export of Good {code} {flow} Over Time"
    
fig = px.line(
    chart_data,
    x="Year",
    y="Final_FOB_Value",
    color=level,
    line_dash="Segment",
    labels={"Final_FOB_Value": "Trade Value (USD)"}
)

fig.update_layout(
    title=dict(
        text=title_text,
        x=0.5,
        xanchor="center",
        font=dict(size=20)
    ),
    yaxis_title="Trade Value (USD)",
    yaxis=dict(showgrid=True),
    xaxis=dict(
        showgrid=True,
        tickmode="array",
        tickvals=all_years + (proj_years if show_projection else []),
        ticktext=[str(y) for y in (all_years + (proj_years if show_projection else []))]
    ),
    legend_title_text=""
)

st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToAdd": ["toImage"],
            "toImageButtonOptions": {
                "format": "svg",      # or "png"
                "filename": "top10_trade" if selected == "Home" else f"{code}_{direction_key}_timeseries",
                "height": 800,
                "width": 1200,
                "scale": 3
        }
    }
)
# ================= SHARE STRUCTURE =================
if selected == "Home":
    st.markdown("---")
    st.subheader("Trade Structure – Category Shares")

    pie_year = st.selectbox(
        "Select year for structure",
        sorted(data["Year"].unique()),
        index=len(sorted(data["Year"].unique())) - 1
    )

    # ---- Aggregate for selected year ----
    pie_data = (
        data[data["Year"] == pie_year]
        .groupby(level, as_index=False)["Final_FOB_Value"]
        .sum()
    )

    if pie_data.empty:
        st.warning("No data available for this year.")
        st.stop()

    # ---- Compute shares ----
    total = pie_data["Final_FOB_Value"].sum()
    pie_data["Share_%"] = (pie_data["Final_FOB_Value"] / total) * 100

    # ---- Text only for >=1% ----
    pie_data["Display"] = pie_data.apply(
        lambda r: f"{r[level]} ({r['Share_%']:.1f}%)" if r["Share_%"] >= 1 else "",
        axis=1
    )

    fig_pie = px.pie(
        pie_data,
        names=level,
        values="Share_%",
        hole=0.4
    )

    fig_pie.update_traces(
        text=pie_data["Display"],
        textinfo="text",
        hovertemplate=f"{level}: %{{label}}<br>%{{value:.2f}}%"
    )
    fig_pie.update_layout(
    title=dict(
        text=f"Category Share Structure in {pie_year}",
        x=0.5,
        xanchor="center",
        font=dict(size=18)
    ),
    showlegend=False
)
    
    st.plotly_chart(
        fig_pie,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToAdd": ["toImage"],
            "toImageButtonOptions": {
                "format": "svg",      # or "png"
                "filename": "top10_trade" if selected == "Home" else f"{code}_{direction_key}_timeseries",
                "height": 800,
                "width": 1200,
                "scale": 3
            }
        }
    )
    # ---- Average share ----
    avg_share = pie_data["Share_%"].mean()
    st.markdown(f"**Average category share:** {avg_share:.2f}%")

    # ---- Merge correct descriptions for chosen level ----
    desc_cols = DESC_MAP[level]

    if not all(c in df.columns for c in desc_cols):
        st.error(f"Missing description columns for {level}: {desc_cols}")
        st.stop()

    desc_map = (
        df[desc_cols]
        .drop_duplicates()
        .groupby(desc_cols[0])[desc_cols[1]]
        .apply(lambda x: x.iloc[0])
        .reset_index()
    )

    desc_map.columns = [level, "Description"]

    # ---- attach descriptions ----
    pie_table = pie_data.merge(desc_map, on=level, how="left")

    # make sure numeric column exists
    if "Share_%" not in pie_table.columns:
        st.error("Internal error: Share_% column missing.")
        st.stop()

    pie_table = pie_table[[level, "Description", "Share_%"]]

    # ---- sort numerically first ----
    pie_table_sorted = pie_table.sort_values("Share_%", ascending=False).copy()

    # ---- format for display AFTER sorting ----
    def format_share(x):
        if x < 0.01:
            return "<0.01"
        else:
            return f"{x:.2f}"

    pie_table_sorted["Share_Display"] = pie_table_sorted["Share_%"].apply(format_share)

    # ---- move tiny values to bottom ----
    tiny = pie_table_sorted[pie_table_sorted["Share_%"] < 0.01]
    normal = pie_table_sorted[pie_table_sorted["Share_%"] >= 0.01]

    pie_table_sorted = pd.concat([normal, tiny], ignore_index=True)

    # ---- final table for display ----
    pie_table_sorted = pie_table_sorted[[level, "Description", "Share_Display"]]

    st.markdown("#### Category Share Table")
    st.dataframe(
        pie_table_sorted,
        use_container_width=True,
        hide_index=True
    )
# ---- DESCRIPTION DISPLAY ----
if selected != "Home":
    st.subheader("Selected Code Description")

    desc = options[options[level] == code].iloc[0].iloc[1]

    if desc == "Description not available":
        desc = "No official description available in dataset"

    st.write(f"**{code}** – {desc}")

st.sidebar.markdown("---")

st.sidebar.markdown("""
**Data Source:**  
UN Comtrade Database  
https://comtradeplus.un.org/
""")

st.markdown("---")

st.markdown("""
### Data Source

All trade data used in this application originates from the **United Nations Comtrade Database**.

Source: UN Comtrade – International Trade Statistics  
https://comtradeplus.un.org/

Data has been processed and harmonized by the author for analytical and visualization purposes.
""")





















































