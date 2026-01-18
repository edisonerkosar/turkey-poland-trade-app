import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Turkey–Poland Bilateral Trade Explorer (2013–2024)")

@st.cache_data
def load_data():
    return pd.read_excel("Unified_Trade_Streamlit.xlsx")

df = load_data()

st.sidebar.header("Search Options")

direction = st.sidebar.selectbox(
    "Trade Direction",
    ["Turkey_to_Poland", "Poland_to_Turkey"]
)

level = st.sidebar.selectbox(
    "Aggregation Level",
    ["HS6", "HS4", "HS2"]
)

search = st.sidebar.text_input("Enter HS code (optional)")

data = df[df["Direction"] == direction]

if search:
    data = data[data[level].astype(str).str.startswith(search)]

grouped = data.groupby(["Year", level], as_index=False)["Final_FOB_Value"].sum()

st.write("Filtered Data Preview", grouped.head(20))

fig = px.line(
    grouped,
    x="Year",
    y="Final_FOB_Value",
    color=level,
    title=f"{direction.replace('_',' ')} – by {level}"
)

st.plotly_chart(fig)

st.write("Total Value Displayed:", grouped["Final_FOB_Value"].sum())
