import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Cash Flow & Net Worth", layout="wide")

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Personal Information")

start_age = st.sidebar.number_input("Current Age", min_value=50, max_value=80, value=65)
end_age = 95

st.sidebar.header("Income & Expenses")
annual_income = st.sidebar.number_input("Annual Income ($)", value=60000, step=5000)
annual_expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=50000, step=5000)

st.sidebar.header("Assets & Liabilities")
cash = st.sidebar.number_input("Cash ($)", value=100000, step=10000)
investments = st.sidebar.number_input("Investments ($)", value=600000, step=25000)
home_value = st.sidebar.number_input("Home Value ($)", value=500000, step=25000)
debt = st.sidebar.number_input("Total Debt ($)", value=0, step=5000)

st.sidebar.header("Assumptions")
investment_return = st.sidebar.slider("Investment Return (%)", 2.0, 8.0, 5.0) / 100
expense_inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100

# =========================
# PROJECTION LOGIC
# =========================
ages = np.arange(start_age, end_age + 1)

cash_balance = cash
investment_balance = investments
expenses = annual_expenses

net_worth = []
cash_flow_series = []
expense_series = []

for age in ages:
    # Investment return
    investment_return_amount = investment_balance * investment_return

    # Cash flow calculation
    cash_flow = (
        annual_income
        + investment_return_amount
        - expenses
    )

    # Update balances
    cash_balance += cash_flow
    investment_balance += investment_return_amount

    # Net worth
    total_assets = cash_balance + investment_balance + home_value
    net_worth.append(total_assets - debt)

    # Store series
    cash_flow_series.append(cash_flow)
    expense_series.append(expenses)

    # Inflate expenses
    expenses *= (1 + expense_inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Cash Flow": cash_flow_series,
    "Expenses": expense_series
})

# =========================
# HEADER
# =========================
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Financial Overview</h1>
    <p style="text-align:center; font-size:18px; color:#555;">
    How cash flow and net worth evolve over time
    </p>
    """,
    unsafe_allow_html=True
)

# =========================
# SUMMARY METRICS
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
col2.metric("Peak Net Worth", f"${df['Net Worth'].max():,.0f}")
col3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# =========================
# VISUALIZATION
# =========================
fig = go.Figure()

# Net Worth (right axis)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#1f77b4", width=4, shape="spline"),
    yaxis="y2"
))

# Cash Flow
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Cash Flow"],
    name="Cash Flow",
    line=dict(color="#2ca02c", width=3)
))

# Expenses (negative for visual clarity)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=-df["Expenses"],
    name="Expenses",
    line=dict(color="#d62728", width=3)
))

fig.update_layout(
    height=650,
    legend=dict(orientation="h", y=1.1),
    xaxis=dict(title="Age"),
    yaxis=dict(
        title="Annual Cash Flow / Expenses",
        tickprefix="$",
        showgrid=True
    ),
    yaxis2=dict(
        title="Net Worth",
        overlaying="y",
        side="right",
        tickprefix="$",
        showgrid=False
    ),
    plot_bgcolor="white",
    margin=dict(l=60, r=60, t=80, b=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#666;'>All figures are projections for illustrative purposes only.</p>",
    unsafe_allow_html=True
)
