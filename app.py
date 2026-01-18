import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Turkey–Poland Trade Explorer (2013–2024)")

@st.cache_data
def load_data():
    return pd.read_excel("Unified_Trade_With_Descriptions.xlsx")

df = load_data()

st.sidebar.header("Filters")

# Direction selector
direction = st.sidebar.selectbox(
    "Trade Direction",
    ["Turkey_to_Poland", "Poland_to_Turkey"]
)

data = df[df["Direction"] == direction]

# Level selector
level = st.sidebar.selectbox(
    "Aggregation Level",
    ["HS6", "HS4", "HS2"]
)

# Autocomplete dropdowns (type-safe)
if level == "HS6":
    options = data[["HS6", "HS_Description"]].drop_duplicates()
    display = options["HS6"].astype(str) + " – " + options["HS_Description"].astype(str)

elif level == "HS4":
    options = data[["HS4", "HS4_Description"]].drop_duplicates()
    display = options["HS4"].astype(str) + " – " + options["HS4_Description"].astype(str)

else:
    options = data[["HS2", "HS2_Description"]].drop_duplicates()
    display = options["HS2"].astype(str) + " – " + options["HS2_Description"].astype(str)

selected = st.sidebar.selectbox(
    "Search by Code or Description",
    ["All"] + list(display)
)

# Filter based on selection
if selected != "All":
    code = selected.split(" – ")[0]
    data = data[data[level] == code]

# Check if any data exists after filtering
if data.empty:
    st.warning("No trade data available for the selected filters.")
    st.stop()

latest_year = data["Year"].max()

# Show Top 10 ONLY when no specific code is selected
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
        title="Top 10 Products by FOB Value",
        text_auto=True
    )

    st.plotly_chart(fig_default, use_container_width=True)


# ----- TIME SERIES GRAPH -----

grouped = data.groupby(["Year", level], as_index=False)["Final_FOB_Value"].sum()

st.subheader("Trade Over Time")

fig = px.line(
    grouped,
    x="Year",
    y="Final_FOB_Value",
    color=level,
    title="Time Series of Trade Value"
)

st.plotly_chart(fig, use_container_width=True)


# ----- SHOW DESCRIPTION ONLY IF A CODE IS CHOSEN -----

if selected != "All":

    st.subheader("Selected Code Description")

    try:
        if level == "HS6":
            desc = options[options["HS6"] == code]["HS_Description"].values[0]
        elif level == "HS4":
            desc = options[options["HS4"] == code]["HS4_Description"].values[0]
        else:
            desc = options[options["HS2"] == code]["HS2_Description"].values[0]

        st.write(f"**{code}** – {desc}")

    except IndexError:
        st.warning("Description not available for the selected code.")


# ----- SUMMARY -----

st.sidebar.write("Total Value Displayed:")
st.sidebar.write(f"{data['Final_FOB_Value'].sum():,.0f}")


