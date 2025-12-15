import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Journey", layout="wide")

# ---------------------------
# SIDEBAR INPUTS
# ---------------------------
st.sidebar.header("Your Financial Snapshot")

age = st.sidebar.number_input("Current Age", 60, 85, 75)
end_age = 95

income = st.sidebar.number_input("Annual Income ($)", value=0)
expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=65000)

cash = st.sidebar.number_input("Liquid Cash ($)", value=200000)
investments = st.sidebar.number_input("Investments ($)", value=650000)
home_value = st.sidebar.number_input("Home Value ($)", value=700000)
debt = st.sidebar.number_input("Debt ($)", value=0)

sell_home_age = st.sidebar.selectbox(
    "When would you likely sell your home?",
    ["Never"] + list(range(age + 1, end_age + 1))
)

st.sidebar.markdown("---")
growth = st.sidebar.slider("Investment Growth (%)", 2.0, 7.0, 5.0) / 100
inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100

# ---------------------------
# PROJECTION LOGIC (NO SPIKE)
# ---------------------------
ages = np.arange(age, end_age + 1)

liquid_assets = cash + investments
home_owned = True

net_worth = []
expenses_path = []
cashflow_path = []

current_expenses = expenses

for yr in ages:
    if sell_home_age != "Never" and yr == int(sell_home_age):
        home_owned = False  # reclassification only

    total_assets = liquid_assets + (home_value if home_owned else 0)
    net_worth.append(total_assets - debt)

    cashflow = income - current_expenses
    cashflow_path.append(cashflow)

    liquid_assets *= (1 + growth)
    expenses_path.append(current_expenses)
    current_expenses *= (1 + inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Expenses": expenses_path,
    "Cash Flow": cashflow_path
})

# ---------------------------
# HEADER
# ---------------------------
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Journey</h1>
    <p style="text-align:center; font-size:18px; color:#555;">
    A visual path of your financial life
    </p>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# CHART WITH IMAGE BACKGROUND (THIS WORKS)
# ---------------------------
fig = go.Figure()

# Background image INSIDE plotly
fig.update_layout(
    images=[
        dict(
            source="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
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

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#2f5d62", width=5, shape="spline"),
    fill="tozeroy",
    fillcolor="rgba(47,93,98,0.25)"
))

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=-df["Expenses"],
    name="Total Expenses",
    line=dict(color="#c94c4c", width=3)
))

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Cash Flow"],
    name="Cash Flow",
    line=dict(color="#f2b705", width=3)
))

# Milestones
peak_idx = df["Net Worth"].idxmax()
peak_age = df.loc[peak_idx, "Age"]
peak_value = df.loc[peak_idx, "Net Worth"]

fig.add_trace(go.Scatter(
    x=[age],
    y=[df.iloc[0]["Net Worth"]],
    mode="markers+text",
    marker=dict(size=14, color="white", line=dict(color="#2f5d62", width=3)),
    text=["Start: strong position"],
    textposition="bottom center"
))

fig.add_trace(go.Scatter(
    x=[peak_age],
    y=[peak_value],
    mode="markers+text",
    marker=dict(size=16, color="#f2b705"),
    text=["Peak: highest net worth"],
    textposition="top center"
))

fig.add_trace(go.Scatter(
    x=[end_age],
    y=[df.iloc[-1]["Net Worth"]],
    mode="markers+text",
    marker=dict(size=14, color="#777"),
    text=["Time to reassess"],
    textposition="top center"
))

fig.update_layout(
    height=650,
    legend=dict(orientation="h", y=1.08),
    xaxis=dict(title="Age"),
    yaxis=dict(title="Dollars ($)", showgrid=False),
    plot_bgcolor="rgba(255,255,255,0.85)",
    margin=dict(t=40, b=40, l=60, r=60)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#666;'>Illustrative projection for planning purposes only.</p>",
    unsafe_allow_html=True
)
