import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Journey", layout="wide")

# ---------------------------
# SIDEBAR INPUTS
# ---------------------------
st.sidebar.header("Your Financial Snapshot")

start_age = st.sidebar.number_input("Current Age", 60, 80, 75)
end_age = 95

annual_income = st.sidebar.number_input("Annual Income ($)", value=0)
annual_expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=65000)

cash = st.sidebar.number_input("Liquid Cash ($)", value=200000)
investments = st.sidebar.number_input("Investments ($)", value=650000)
home_value = st.sidebar.number_input("Home Value ($)", value=700000)
debt = st.sidebar.number_input("Debt ($)", value=0)

st.sidebar.markdown("---")
growth = st.sidebar.slider("Investment Growth (%)", 2.0, 7.0, 5.0) / 100
inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100

# ---------------------------
# PROJECTION LOGIC
# ---------------------------
ages = np.arange(start_age, end_age + 1)

assets = cash + investments
expenses = annual_expenses

net_worth = []

for age in ages:
    cashflow = annual_income - expenses
    assets = (assets + cashflow) * (1 + growth)
    net_worth.append(assets + home_value - debt)
    expenses *= (1 + inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth
})

# Key milestones
peak_idx = df["Net Worth"].idxmax()
peak_age = df.loc[peak_idx, "Age"]
peak_value = df.loc[peak_idx, "Net Worth"]

decline_age = min(peak_age + 7, end_age)
decline_value = df.loc[df["Age"] == decline_age, "Net Worth"].values[0]

# ---------------------------
# HEADER
# ---------------------------
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Journey</h1>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# JOURNEY GRAPH
# ---------------------------
fig = go.Figure()

# Background image INSIDE chart
fig.update_layout(
    images=[
        dict(
            source="https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91",
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            opacity=0.35,
            layer="below"
        )
    ]
)

# Journey path (net worth)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    mode="lines",
    line=dict(color="#4f6f73", width=6, shape="spline"),
    fill="tozeroy",
    fillcolor="rgba(79,111,115,0.30)",
    hovertemplate="Age %{x}<br>Net Worth: $%{y:,.0f}<extra></extra>"
))

# Milestone points
milestones = [
    (start_age, df.iloc[0]["Net Worth"], "Start:\nstrong position", "#1f7a63"),
    (peak_age, peak_value, "Peak:\nhighest net worth", "#d4a017"),
    (decline_age, decline_value, "Noticeable\ndecline", "#8f9779"),
    (end_age, df.iloc[-1]["Net Worth"], "Time to\nreassess", "#c2a24d"),
]

for age, value, label, color
