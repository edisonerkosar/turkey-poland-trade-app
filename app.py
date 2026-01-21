import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Turkey–Poland Trade Explorer (2013–2024)")


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_excel("Unified_Trade_CLEAN_v2.xlsx")

    df["HS6"] = df["HS6"].astype(str).str.zfill(6)
    df["HS4"] = df["HS4"].astype(str).str.zfill(4)
    df["HS2"] = df["HS2"].astype(str).str.zfill(2)

    return df


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

if level == "HS6":
    options = data[["HS6", "HS_Description"]].drop_duplicates()
    display = options["HS6"].astype(str) + " – " + options["HS_Description"].astype(str)
elif level == "HS4":
    options = data[["HS4", "HS4_Description"]].drop_duplicates()
    display = options["HS4"] + " – " + options["HS4_Description"]
else:
    options = data[["HS2", "HS2_Description"]].drop_duplicates()
    display = options["HS2"] + " – " + options["HS2_Description"]

selected = st.sidebar.selectbox(
    "Search by Code or Description",
    ["Home"] + list(display)
)
if st.sidebar.button("Reset to Home"):
    selected = "Home"

if selected == "Home":
    
    st.markdown("""
    **About this tool:**  
    This application was developed as part of research on Turkey–Poland trade relations.  
    Data reflects officially reported trade flows from UN Comtrade.
    """)
st.sidebar.page_link("pages/military_comparator.py", label="Military Trade Comparator")
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

    st.subheader(f"Top 10 {level} Categories in {latest_year}")

    fig_default = px.bar(
        top10,
        x=level,
        y="Final_FOB_Value",
        text_auto=True,
        labels={"Final_FOB_Value": "Trade Value (USD)"}
    )

    fig_default.update_layout(
        xaxis_title="HS Code",
        yaxis_title="Trade Value (USD)",
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=list(top10[level]),
            ticktext=list(top10[level])
        ),
        yaxis=dict(showgrid=True)
    )

    st.plotly_chart(fig_default, width="stretch")


# ---- TIME SERIES GRAPH ----
st.subheader("Trade Over Time")

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

fig = px.line(
    chart_data,
    x="Year",
    y="Final_FOB_Value",
    color=level,
    line_dash="Segment",
    labels={"Final_FOB_Value": "Trade Value (USD)"}
)

fig.update_layout(
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

st.plotly_chart(fig, width="stretch")

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


















