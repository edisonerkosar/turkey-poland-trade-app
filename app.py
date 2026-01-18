import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Turkey–Poland Trade Explorer (2013–2024)")

@st.cache_data
def load_data():
    df = pd.read_excel("Unified_Trade_CLEAN_v2.xlsx")

    df["HS6"] = df["HS6"].astype(str).str.zfill(6)
    df["HS4"] = df["HS4"].astype(str).str.zfill(4)
    df["HS2"] = df["HS2"].astype(str).str.zfill(2)

    return df

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

if level == "HS6":
    options = data[["HS6", "HS_Description"]].drop_duplicates()
    display = options["HS6"] + " – " + options["HS_Description"]
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

if selected == "Home":
    
    st.markdown("""
    **About this tool:**  
    This application was developed as part of research on Turkey–Poland trade relations.  
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

    st.plotly_chart(fig_default, use_container_width=True)


# ---- TIME SERIES GRAPH ----
# Build a complete year range
all_years = list(range(2013, 2025))

grouped = data.groupby(["Year", level], as_index=False)["Final_FOB_Value"].sum()

# Ensure all years appear even with zero values
codes = grouped[level].unique()

complete = []

for c in codes:
    subset = grouped[grouped[level] == c]

    full = pd.DataFrame({
        "Year": all_years,
        level: c
    })

    merged = full.merge(subset, on=["Year", level], how="left")
    merged["Final_FOB_Value"] = merged["Final_FOB_Value"].fillna(0)

    complete.append(merged)

grouped = pd.concat(complete, ignore_index=True)
grouped = grouped.sort_values("Year")

st.subheader("Trade Over Time")

fig = px.line(
    grouped,
    x="Year",
    y="Final_FOB_Value",
    color=level,
    labels={"Final_FOB_Value": "Trade Value (USD)"}
)

fig.update_layout(
    yaxis_title="Trade Value (USD)",
    yaxis=dict(showgrid=True),
    xaxis=dict(
        showgrid=True,
        tickmode="array",
        tickvals=all_years,
        ticktext=[str(y) for y in all_years]
    )
)

st.plotly_chart(fig, use_container_width=True)


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





