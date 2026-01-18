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
    ["All"] + list(display)
)

if selected == "All":

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


grouped = data.groupby(["Year", level], as_index=False)["Final_FOB_Value"].sum()
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
    xaxis=dict(showgrid=True)
)

st.plotly_chart(fig, use_container_width=True)

if selected != "All":
    st.subheader("Selected Code Description")

    desc = options[options[level] == code].iloc[0].iloc[1]

    if desc == "Description not available":
        desc = "No official description available in dataset"

    st.write(f"**{code}** – {desc}")

