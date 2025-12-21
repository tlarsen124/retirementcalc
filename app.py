import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Overview", layout="wide")

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Key Assumptions")

start_age = st.sidebar.number_input("Age", min_value=50, max_value=95, value=70)
end_age = 95

st.sidebar.subheader("Home (Owned Outright)")
home_value_now = st.sidebar.number_input("Home Value Today ($)", value=1_100_000, step=50_000)
home_growth = st.sidebar.slider("Home Value Growth (%)", 0.0, 8.0, 4.0) / 100

tax_deductions = st.sidebar.number_input(
    "Cost Basis + Improvements + 121 Deduction ($)",
    value=250_000.0,
    step=25_000.0
)

sell_home_years = st.sidebar.number_input("Sell Home In (Years)", min_value=0, max_value=40, value=5)
sale_cost_pct = st.sidebar.slider("Sale Cost (%)", 0.0, 10.0, 6.0) / 100

st.sidebar.subheader("Income (Annual)")
ssn_income = st.sidebar.number_input("SSN ($)", value=15_600, step=500)
pension_income = st.sidebar.number_input("Pension ($)", value=27_600, step=500)
employment_income = st.sidebar.number_input("Employment ($)", value=0, step=1_000)

st.sidebar.subheader("Investments")
cash_start = st.sidebar.number_input("Cash / Money Market ($)", value=45_000, step=5_000)
ira_start = st.sidebar.number_input("IRA / Stocks ($)", value=1_200_000, step=25_000)

st.sidebar.subheader("Living Expenses")

self_years = st.sidebar.number_input("Self-Sufficient (years)", value=2)
self_cost = st.sidebar.number_input("Self-Sufficient Annual Cost ($)", value=38_000, step=2_000)

ind_years = st.sidebar.number_input("Independent Living starts in (years)", value=2)
ind_cost = st.sidebar.number_input("Independent Living Annual Cost ($)", value=50_000, step=2_000)

assist_years = st.sidebar.number_input("Assisted Living starts in (years)", value=10)
assist_cost = st.sidebar.number_input("Assisted Living Annual Cost ($)", value=60_000, step=2_000)

memory_years = st.sidebar.number_input("Memory Care starts in (years)", value=20)
memory_cost = st.sidebar.number_input("Memory Care Annual Cost ($)", value=90_000, step=5_000)

st.sidebar.subheader("Taxes & Assumptions")
avg_tax_rate = st.sidebar.slider("Average Tax Rate (%)", 0.0, 40.0, 30.0) / 100
cap_gains_rate = st.sidebar.slider("Capital Gains Tax (%)", 0.0, 40.0, 25.0) / 100

living_infl = st.sidebar.slider("Living Inflation (%)", 0.0, 6.0, 3.0) / 100
stock_growth = st.sidebar.slider("Stocks / IRA Growth (%)", 0.0, 10.0, 7.0) / 100
cash_growth = st.sidebar.slider("Money Market Growth (%)", 0.0, 6.0, 4.5) / 100

# =========================
# PROJECTION
# =========================
ages = np.arange(start_age, end_age + 1)

cash = cash_start
ira = ira_start
home_value = home_value_now

net_worth = []
expenses_series = []
cashflow_series = []
cash_series = []
ira_series = []
home_series = []

income_annual = (ssn_income + pension_income + employment_income) * (1 - avg_tax_rate)

for i, age in enumerate(ages):
    # Grow home until sale
    home_value *= (1 + home_growth)

    # Determine expenses
    if age < start_age + self_years:
        expenses = self_cost
    elif age < start_age + assist_years:
        expenses = ind_cost
    elif age < start_age + memory_years:
        expenses = assist_cost
    else:
        expenses = memory_cost

    expenses *= (1 + living_infl) ** i

    # Investment growth
    cash *= (1 + cash_growth)
    ira *= (1 + stock_growth)

    # Home sale
    if i == sell_home_years:
        sale_price = home_value
        sale_cost = sale_price * sale_cost_pct
        taxable_gain = max(sale_price - sale_cost - tax_deductions, 0)
        tax = taxable_gain * cap_gains_rate
        proceeds = sale_price - sale_cost - tax

        ira += proceeds
        home_value = 0

    # Cash flow
    cash_flow = income_annual - expenses

    if cash_flow >= 0:
        cash += cash_flow
    else:
        deficit = -cash_flow
        take_cash = min(cash, deficit)
        cash -= take_cash
        deficit -= take_cash

        if deficit > 0:
            ira -= deficit

    # Net worth
    total_assets = cash + ira + home_value
    net_worth.append(total_assets)

    expenses_series.append(expenses)
    cashflow_series.append(cash_flow)
    cash_series.append(cash)
    ira_series.append(ira)
    home_series.append(home_value)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Expenses": expenses_series,
    "Cash Flow": cashflow_series,
    "Cash": cash_series,
    "IRA / Stocks": ira_series,
    "Home Value": home_series
})

# =========================
# HEADER
# =========================
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Financial Overview</h1>
    <p style="text-align:center; font-size:20px; color:#666;">
    A simplified view of income, expenses, and net worth over time
    </p>
    """,
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)
c1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
c2.metric("Peak Net Worth", f"${df['Net Worth'].max():,.0f}")
c3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# =========================
# CHART 1: NET WORTH + CASH FLOW
# =========================
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Age"], y=df["Net Worth"],
    name="Net Worth",
    line=dict(width=5)
))

fig.add_trace(go.Scatter(
    x=df["Age"], y=df["Expenses"],
    name="Expenses",
    line=dict(dash="dot")
))

fig.add_trace(go.Scatter(
    x=df["Age"], y=df["Cash Flow"],
    name="Cash Flow"
))

fig.update_layout(
    height=600,
    xaxis=dict(title="Age", tickfont=dict(size=18)),
    yaxis=dict(title="Dollars", tickfont=dict(size=18), tickprefix="$"),
    legend=dict(orientation="h"),
    plot_bgcolor="white"
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# CHART 2: ASSETS
# =========================
fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=df["Age"], y=df["Cash"], name="Cash"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["IRA / Stocks"], name="IRA / Stocks"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["Home Value"], name="Home Value", line=dict(dash="dot")))

fig2.update_layout(
    height=600,
    xaxis=dict(title="Age", tickfont=dict(size=18)),
    yaxis=dict(title="Value", tickfont=dict(size=18), tickprefix="$"),
    legend=dict(orientation="h"),
    plot_bgcolor="white"
)

st.plotly_chart(fig2, use_container_width=True)

with st.expander("Show Data Table"):
    st.dataframe(df)
