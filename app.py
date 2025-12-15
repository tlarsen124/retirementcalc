import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Overview", layout="wide")

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Personal Information")

start_age = st.sidebar.number_input("Current Age", 50, 85, 65)
end_age = 95

st.sidebar.header("Income & Expenses")
annual_income = st.sidebar.number_input("Annual Income ($)", value=60000, step=5000)
base_expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=50000, step=5000)

st.sidebar.header("Assets & Liabilities")
cash = st.sidebar.number_input("Cash ($)", value=100000, step=10000)
investments = st.sidebar.number_input("Investments ($)", value=600000, step=25000)
home_value = st.sidebar.number_input("Home Value ($)", value=500000, step=25000)
debt = st.sidebar.number_input("Debt ($)", value=0, step=5000)

st.sidebar.header("Care Planning")
care_type = st.sidebar.selectbox(
    "Later-Life Care",
    ["None", "Independent Living", "Assisted Living", "Memory Care"]
)

care_start_age = st.sidebar.number_input(
    "Care Start Age", min_value=start_age, max_value=end_age, value=end_age
)

st.sidebar.header("Assumptions")
investment_return = st.sidebar.slider("Investment Return (%)", 2.0, 8.0, 5.0) / 100
expense_inflation = st.sidebar.slider("Expense Inflation (%)", 0.0, 5.0, 2.5) / 100
care_inflation = st.sidebar.slider("Care Cost Inflation (%)", 0.0, 7.0, 3.0) / 100

# =========================
# CARE COST ASSUMPTIONS (ANNUAL)
# =========================
care_cost_map = {
    "None": 0,
    "Independent Living": 50000,
    "Assisted Living": 60000,
    "Memory Care": 90000
}

base_care_cost = care_cost_map[care_type]

# =========================
# PROJECTION LOGIC
# =========================
ages = np.arange(start_age, end_age + 1)

cash_balance = cash
investment_balance = investments
expenses = base_expenses
care_cost = base_care_cost

net_worth = []
expenses_series = []
cash_flow_series = []

for age in ages:
    total_expenses = expenses
    if care_type != "None" and age >= care_start_age:
        total_expenses += care_cost

    investment_return_amount = investment_balance * investment_return
    cash_flow = annual_income + investment_return_amount - total_expenses

    cash_balance += cash_flow
    investment_balance += investment_return_amount

    total_assets = cash_balance + investment_balance + home_value
    net_worth.append(total_assets - debt)

    expenses_series.append(total_expenses)
    cash_flow_series.append(cash_flow)

    expenses *= (1 + expense_inflation)
    care_cost *= (1 + care_inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Expenses": expenses_series,
    "Cash Flow": cash_flow_series
})

# =========================
# HEADER
# =========================
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Financial Overview</h1>
    <p style="text-align:center; font-size:18px; color:#666;">
    A simple view of how your finances may evolve over time
    </p>
    """,
    unsafe_allow_html=True
)

# =========================
# SUMMARY METRICS
# =========================
c1, c2, c3 = st.columns(3)
c1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
c2.metric("Peak Net Worth", f"${df['Net Worth'].max():,.0f}")
c3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# =========================
# CLEAN, MINIMAL VISUAL
# =========================
fig = go.Figure()

# Net Worth (primary story)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#1f3d4c", width=5, shape="spline"),
    fill="tozeroy",
    fillcolor="rgba(31,61,76,0.15)",
    hovertemplate="Age %{x}<br>Net Worth: $%{y:,.0f}<extra></extra>"
))

# Expenses (secondary)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Expenses"],
    name="Expenses",
    line=dict(color="#c0392b", width=2, dash="dot"),
    opacity=0.65
))

# Cash Flow (secondary)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Cash Flow"],
    name="Cash Flow",
    line=dict(color="#27ae60", width=2),
    opacity=0.65
))

# Locked axis ranges
y_min = min(df["Net Worth"].min(), df["Expenses"].min(), df["Cash Flow"].min()) * 0.9
y_max = max(df["Net Worth"].max(), df["Expenses"].max(), df["Cash Flow"].max()) * 1.1

fig.update_layout(
    height=600,
    legend=dict(
        orientation="h",
        y=1.05,
        font=dict(size=13)
    ),
    xaxis=dict(
        title="Age",
        tickmode="linear",
        dtick=5,
        showgrid=False,
        fixedrange=True,
        color="#777"
    ),
    yaxis=dict(
        title="Dollars",
        range=[y_min, y_max],
        tickprefix="$",
        showgrid=False,
        fixedrange=True,
        color="#777"
    ),
    plot_bgcolor="white",
    margin=dict(t=40, b=40, l=40, r=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#777;'>Illustrative projections only.</p>",
    unsafe_allow_html=True
)
