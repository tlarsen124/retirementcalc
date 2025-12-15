import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Journey", layout="wide")

# ---------------------------
# Sidebar Inputs
# ---------------------------
st.sidebar.header("Your Financial Snapshot")

age = st.sidebar.number_input("Current Age", min_value=40, max_value=80, value=65)
retire_age = 67
end_age = 95

income = st.sidebar.number_input("Annual Income ($)", value=85000, step=5000)
expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=60000, step=5000)

cash = st.sidebar.number_input("Liquid Cash ($)", value=120000, step=10000)
investments = st.sidebar.number_input("Investments ($)", value=650000, step=25000)
debt = st.sidebar.number_input("Total Debt ($)", value=50000, step=5000)

home_value = st.sidebar.number_input("Home Value ($)", value=700000, step=25000)

sell_home_age = st.sidebar.selectbox(
    "When would you likely sell your home?",
    options=["Never"] + list(range(age + 1, end_age + 1)),
    index=0
)

# Assumptions
st.sidebar.markdown("---")
st.sidebar.subheader("Planning Assumptions")

growth_rate = st.sidebar.slider("Investment Growth Rate (%)", 2.0, 8.0, 5.0) / 100
expense_inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100
retirement_income_ratio = st.sidebar.slider("Income After Retirement (%)", 0, 100, 40) / 100

# ---------------------------
# Projection Logic
# ---------------------------
years = np.arange(age, end_age + 1)

net_worth = []
current_assets = cash + investments + home_value - debt
current_investments = investments
current_expenses = expenses

for yr in years:
    # Income logic
    if yr < retire_age:
        annual_income = income
    else:
        annual_income = income * retirement_income_ratio

    # Home sale
    if sell_home_age != "Never" and yr == int(sell_home_age):
        current_assets += home_value
        home_value = 0

    # Cashflow
    cashflow = annual_income - current_expenses
    current_assets += cashflow

    # Investment growth
    current_investments *= (1 + growth_rate)
    current_assets += current_investments * growth_rate

    net_worth.append(current_assets)

    current_expenses *= (1 + expense_inflation)

df = pd.DataFrame({
    "Age": years,
    "Net Worth": net_worth
})

# Key points
peak_idx = df["Net Worth"].idxmax()
peak_age = df.loc[peak_idx, "Age"]
peak_value = df.loc[peak_idx, "Net Worth"]

# ---------------------------
# Header
# ---------------------------
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Journey</h1>
    <p style="text-align:center; font-size:18px; color:#555;">
    A visual look at how your financial life may unfold over time
    </p>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Summary Cards
# ---------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
col2.metric("Peak Net Worth", f"${peak_value:,.0f}", f"Age {peak_age}")
col3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# ---------------------------
# Journey Graph
# ---------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    mode="lines",
    line=dict(width=5, color="#3a7d7c"),
    fill="tozeroy",
    fillcolor="rgba(58,125,124,0.25)",
    hovertemplate="Age %{x}<br>Net Worth: $%{y:,.0f}<extra></extra>"
))

# Milestones
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
    x=[peak_age + 5],
    y=[df.loc[df["Age"] == peak_age + 5, "Net Worth"].values[0] if peak_age + 5 <= end_age else peak_value],
    mode="markers+text",
    marker=dict(size=14, color="#c97c5d"),
    text=["Noticeable decline"],
    textposition="bottom center"
))

fig.add_trace(go.Scatter(
    x=[end_age],
    y=[df.iloc[-1]["Net Worth"]],
    mode="markers+text",
    marker=dict(size=14, color="#6c757d"),
    text=["Time to reassess"],
    textposition="top center"
))

fig.update_layout(
    height=650,
    showlegend=False,
    xaxis=dict(title="Age", tickmode="linear"),
    yaxis=dict(title="Net Worth ($)", showgrid=False),
    plot_bgcolor="white",
    margin=dict(t=40, b=40, l=60, r=60)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#777;'>This projection is illustrative, not a guarantee.</p>",
    unsafe_allow_html=True
)

