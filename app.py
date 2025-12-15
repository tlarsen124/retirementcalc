import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Cash Flow & Net Worth", layout="wide")

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Personal Information")

start_age = st.sidebar.number_input("Current Age", min_value=50, max_value=85, value=65)
end_age = 95

st.sidebar.header("Income & Expenses")
annual_income = st.sidebar.number_input("Annual Income ($)", value=60000, step=5000)
annual_expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=50000, step=5000)

st.sidebar.header("Assets & Liabilities")
cash = st.sidebar.number_input("Cash ($)", value=100000, step=10000)
investments = st.sidebar.number_input("Investments ($)", value=600000, step=25000)
home_value = st.sidebar.number_input("Home Value ($)", value=500000, step=25000)
debt = st.sidebar.number_input("Total Debt ($)", value=0, step=5000)

st.sidebar.header("Care Planning")
care_type = st.sidebar.selectbox(
    "Select Care Type (if needed later):",
    ["None", "Independent Living", "Assisted Living", "Memory Care"]
)

care_start_age = st.sidebar.number_input(
    "Care Start Age (if applicable)", min_value=start_age, max_value=end_age, value=start_age
)

st.sidebar.header("Assumptions")
investment_return = st.sidebar.slider("Investment Return (%)", 2.0, 8.0, 5.0) / 100
expense_inflation = st.sidebar.slider("Expense Inflation (%)", 0.0, 5.0, 2.5) / 100
care_inflation = st.sidebar.slider("Care Cost Inflation (%)", 0.0, 7.0, 3.0) / 100

# =========================
# CARE COST DEFAULTS
# =========================
care_costs = {
    "None": 0,
    "Independent Living": 50000,
    "Assisted Living": 60000,
    "Memory Care": 90000
}
base_care_cost = care_costs.get(care_type, 0)

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
    # base living expenses
    current_expense = expenses

    # if in care years, add care cost
    if care_type != "None" and age >= care_start_age:
        current_expense += base_care_cost

    # investment return
    investment_return_amount = investment_balance * investment_return

    # cash flow
    cash_flow = annual_income + investment_return_amount - current_expense

    # update balances
    cash_balance += cash_flow
    investment_balance += investment_return_amount

    # net worth
    total_assets = cash_balance + investment_balance + home_value
    net_worth.append(total_assets - debt)

    # record series
    cash_flow_series.append(cash_flow)
    expense_series.append(current_expense)

    # inflation adjustments
    expenses *= (1 + expense_inflation)
    base_care_cost *= (1 + care_inflation)

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
    <h1 style="text-align:center;">Retirement Cash Flow & Net Worth</h1>
    <p style="text-align:center; font-size:18px; color:#555;">
    See how income, expenses, and net worth evolve with care cost planning
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
# VISUALIZATION (Fixed Axis + Visually Pleasing)
# =========================
fig = go.Figure()

# Net Worth (right axis)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#1a5276", width=4, shape="spline"),
    yaxis="y2"
))

# Cash Flow
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Cash Flow"],
    name="Cash Flow",
    line=dict(color="#27ae60", width=3, dash="solid")
))

# Expenses (absolute)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Expenses"],
    name="Expenses",
    line=dict(color="#cb4335", width=3, dash="dot")
))

# ====================
# FIXED AXIS RANGES
# ====================
net_w_min = min(df["Net Worth"]) * 0.9
net_w_max = max(df["Net Worth"]) * 1.1

cashflow_min = min(df["Cash Flow"]) * 1.1
cashflow_max = max(df["Cash Flow"]) * 1.1

expense_min = min(df["Expenses"]) * 0.9
expense_max = max(df["Expenses"]) * 1.1

fig.update_layout(
    height=700,
    legend=dict(orientation="h", y=1.1),
    xaxis=dict(
        title="Age",
        tickmode="linear",
        dtick=5
    ),
    yaxis=dict(
        title="Cash Flow & Expenses",
        range=[min(cashflow_min, expense_min), max(cashflow_max, expense_max)],
        tickprefix="$",
        showgrid=True,
        gridcolor="rgba(200,200,200,0.3)"
    ),
    yaxis2=dict(
        title="Net Worth",
        overlaying="y",
        side="right",
        range=[net_w_min, net_w_max],
        tickprefix="$",
        showgrid=False
    ),
    plot_bgcolor="white",
    margin=dict(l=60, r=60, t=90, b=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#666;'>This is a projection for illustrative purposes only.</p>",
    unsafe_allow_html=True
)
