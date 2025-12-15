import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Cash Flow Analysis", layout="wide")

# ---------------------------
# Background image (stock retirement photo)
# ---------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1520975922284-7b9585a27d1f");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .block-container {
        background-color: rgba(255, 255, 255, 0.92);
        padding: 2rem;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Sidebar Inputs
# ---------------------------
st.sidebar.header("Financial Inputs")

age = st.sidebar.number_input("Current Age", 55, 80, 70)
end_age = 100
retire_age = 75

income = st.sidebar.number_input("Annual Income ($)", value=0)
expenses = st.sidebar.number_input("Annual Expenses ($)", value=65000)

cash = st.sidebar.number_input("Liquid Cash ($)", value=200000)
investments = st.sidebar.number_input("Investments ($)", value=600000)
home_value = st.sidebar.number_input("Home Value ($)", value=700000)
debt = st.sidebar.number_input("Debt ($)", value=0)

sell_home_age = st.sidebar.selectbox(
    "Age to Sell Home",
    options=["Never"] + list(range(age + 1, end_age + 1))
)

st.sidebar.markdown("---")
growth = st.sidebar.slider("Investment Growth (%)", 2.0, 7.0, 5.0) / 100
inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100

# ---------------------------
# Projection Logic (NO SPIKE)
# ---------------------------
ages = np.arange(age, end_age + 1)

net_worth = []
expense_path = []
cashflow_path = []

liquid_assets = cash + investments
home_owned = True

current_expenses = expenses

for yr in ages:
    # Income
    annual_income = income if yr < retire_age else 0

    # Home sale (reclassify only)
    if sell_home_age != "Never" and yr == int(sell_home_age):
        home_owned = False  # value already counted

    # Net worth
    total_assets = liquid_assets + (home_value if home_owned else 0)
    nw = total_assets - debt
    net_worth.append(nw)

    # Cash flow
    cashflow = annual_income - current_expenses
    cashflow_path.append(cashflow)

    # Grow investments
    liquid_assets *= (1 + growth)

    # Track expenses
    expense_path.append(current_expenses)
    current_expenses *= (1 + inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Expenses": expense_path,
    "Cash Flow": cashflow_path
})

# ---------------------------
# Chart (like your example)
# ---------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Cash Flow"],
    name="Cash Flow",
    line=dict(color="gold", width=3),
    yaxis="y1"
))

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=-df["Expenses"],
    name="Total Expenses",
    line=dict(color="red", width=3),
    yaxis="y1"
))

fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="royalblue", width=4, shape="spline"),
    yaxis="y2"
))

fig.update_layout(
    title="Cash Flow Analysis",
    height=650,
    legend=dict(orientation="h", y=1.08),
    yaxis=dict(
        title="Cash Flow / Expenses",
        tickprefix="$",
        showgrid=True
    ),
    yaxis2=dict(
        title="Net Worth",
        overlaying="y",
        side="right",
        tickprefix="$"
    ),
    xaxis=dict(title="Age"),
    plot_bgcolor="white",
    margin=dict(l=60, r=60, t=80, b=40)
)

st.plotly_chart(fig, use_container_width=True)
