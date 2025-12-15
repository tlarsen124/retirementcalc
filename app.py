import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import base64

st.set_page_config(page_title="Retirement Financial Overview", layout="wide")

# =========================
# LOAD BACKGROUND IMAGE
# =========================
def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = load_image_base64("assets/background.jpg")

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

st.sidebar.header("Chart Controls")
show_expenses = st.sidebar.checkbox("Show Expenses", True)
show_cashflow = st.sidebar.checkbox("Show Cash Flow", True)
show_background = st.sidebar.checkbox("Show Background Image", True)

# ⭐ Image strength slider
image_opacity = st.sidebar.slider(
    "Background Image Strength",
    min_value=0.30,
    max_value=0.80,
    value=0.65,
    step=0.05
)

# =========================
# CARE COSTS
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

    net_worth.append(cash_balance + investment_balance + home_value - debt)

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
    <p style="text-align:center; font-size:22px; color:#555;">
    A clear view of net worth, expenses, and cash flow over time
    </p>
    """,
    unsafe_allow_html=True
)

# =========================
# METRICS
# =========================
c1, c2, c3 = st.columns(3)
c1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
c2.metric("Peak Net Worth", f"${df['Net Worth'].max():,.0f}")
c3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# =========================
# AXIS RANGES
# =========================
left_values = []
if show_expenses:
    left_values.extend(df["Expenses"])
if show_cashflow:
    left_values.extend(df["Cash Flow"])

left_min, left_max = (-1, 1) if not left_values else (
    min(left_values) * 0.9,
    max(left_values) * 1.1
)
right_min = df["Net Worth"].min() * 0.9
right_max = df["Net Worth"].max() * 1.1

# =========================
# FIGURE
# =========================
fig = go.Figure()

# Net Worth
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#162f3a", width=6, shape="spline"),
    fill="tozeroy",
    fillcolor="rgba(22,47,58,0.28)",
    yaxis="y2"
))

# Expenses
if show_expenses:
    fig.add_trace(go.Scatter(
        x=df["Age"],
        y=df["Expenses"],
        name="Expenses",
        line=dict(color="#c0392b", width=2.5, dash="dot"),
        opacity=0.85,
        yaxis="y1"
    ))

# Cash Flow
if show_cashflow:
    fig.add_trace(go.Scatter(
        x=df["Age"],
        y=df["Cash Flow"],
        name="Cash Flow",
        line=dict(color="#27ae60", width=2.5),
        opacity=0.85,
        yaxis="y1"
    ))

# =========================
# BACKGROUND IMAGE + GRADIENT MASK
# =========================
layout_images = []
if show_background:
    layout_images.append(
        dict(
            source=f"data:image/jpeg;base64,{bg_image}",
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            opacity=image_opacity,
            layer="below"
        )
    )

fig.update_layout(
    images=layout_images,
    shapes=[
        # soft white gradient mask (top → bottom)
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            fillcolor="rgba(255,255,255,0.30)",
            layer="below",
            line_width=0
        )
    ],
    height=720,
    legend=dict(orientation="h", y=1.1, font=dict(size=18)),
    xaxis=dict(
        title=dict(text="Age", font=dict(size=28)),
        tickfont=dict(size=22),
        tickmode="linear",
        dtick=5,
        showgrid=False,
        fixedrange=True
    ),
    yaxis=dict(
        title=dict(text="Cash Flow / Expenses ($)", font=dict(size=28)),
        tickfont=dict(size=22),
        range=[left_min, left_max],
        tickprefix="$",
        showgrid=False,
        fixedrange=True
    ),
    yaxis2=dict(
        title=dict(text="Net Worth ($)", font=dict(size=28)),
        tickfont=dict(size=22),
        overlaying="y",
        side="right",
        range=[right_min, right_max],
        tickprefix="$",
        showgrid=False,
        fixedrange=True
    ),
    plot_bgcolor="rgba(255,255,255,0.15)",
    margin=dict(t=50, b=50, l=70, r=70)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#666;'>Illustrative projections only.</p>",
    unsafe_allow_html=True
)
