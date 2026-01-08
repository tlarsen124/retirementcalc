import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import base64

st.set_page_config(page_title="Retirement Overview", layout="wide")

# =========================
# BACKGROUND IMAGE
# =========================
def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = load_image_base64("assets/background.jpg")

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

st.sidebar.subheader("Chart Appearance")
show_background = st.sidebar.checkbox("Show Background Image", True)
image_opacity = st.sidebar.slider("Background Image Opacity", 0.30, 1.00, 0.65, 0.05)

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

    # Calculate liquid home value (net proceeds after sale costs and taxes)
    # This represents what you'd actually get if you sold the home today
    sale_price = home_value
    sale_cost = sale_price * sale_cost_pct
    taxable_gain = max(sale_price - sale_cost - tax_deductions, 0)
    tax = taxable_gain * cap_gains_rate
    liquid_home_value = sale_price - sale_cost - tax

    # Home sale (actual transaction)
    if i == sell_home_years:
        ira += liquid_home_value
        home_value = 0
        liquid_home_value = 0

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

    total_assets = cash + ira + liquid_home_value

    net_worth.append(total_assets)
    expenses_series.append(expenses)
    cashflow_series.append(cash_flow)
    cash_series.append(cash)
    ira_series.append(ira)
    home_series.append(liquid_home_value)

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
# MILESTONES
# =========================
start_idx = 0
peak_idx = df["Net Worth"].idxmax()
mid_idx = int((start_idx + peak_idx) / 2)

decline_candidates = df.loc[peak_idx:]
decline_idx = decline_candidates[
    decline_candidates["Net Worth"] < 0.9 * df.loc[peak_idx, "Net Worth"]
].index
decline_idx = decline_idx[0] if len(decline_idx) > 0 else df.index[-1]

milestones = [
    ("Start", start_idx, "#2c3e50"),
    ("Building Wealth", mid_idx, "#27ae60"),
    ("Peak Net Worth", peak_idx, "#f1c40f"),
    ("Reassessment Phase", decline_idx, "#e67e22"),
]


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
# PHASE HEADERS
# =========================
st.markdown("<br>", unsafe_allow_html=True)
phase_col1, phase_col2, phase_col3 = st.columns(3)
phase_col1.markdown(
    """
    <h2 style="text-align:center; color:#2c3e50;">Phase 1</h2>
    """,
    unsafe_allow_html=True
)
phase_col2.markdown(
    """
    <h2 style="text-align:center; color:#2c3e50;">Phase 2</h2>
    """,
    unsafe_allow_html=True
)
phase_col3.markdown(
    """
    <h2 style="text-align:center; color:#2c3e50;">Phase 3</h2>
    """,
    unsafe_allow_html=True
)
st.markdown("<br>", unsafe_allow_html=True)

# =========================
# BACKGROUND IMAGE CONFIG
# =========================
layout_images = []
if show_background:
    layout_images.append(dict(
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
    ))

# =========================
# BUILD CHART (FORMATTING TEMPLATE)
# =========================
fig = go.Figure()

# Net Worth (right axis)
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#162f3a", width=6, shape="spline"),
    yaxis="y2"
))

# Milestone dots
for label, idx, color in milestones:
    fig.add_trace(go.Scatter(
        x=[df.loc[idx, "Age"]],
        y=[df.loc[idx, "Net Worth"]],
        mode="markers+text",
        marker=dict(size=20, color=color, line=dict(color="white", width=3)),
        text=[label],
        textposition="top center",
        textfont=dict(size=14),
        yaxis="y2",
        showlegend=False
    ))


# Expenses
# fig.add_trace(go.Scatter(
#     x=df["Age"],
#     y=df["Expenses"],
#     name="Expenses",
#     line=dict(color="#c0392b", width=2.5, dash="dot"),
#     opacity=0.85,
#     yaxis="y1"
# ))

# Cash Flow
# fig.add_trace(go.Scatter(
#     x=df["Age"],
#     y=df["Cash Flow"],
#     name="Cash Flow",
#     line=dict(color="#27ae60", width=2.5),
#     opacity=0.85,
#     yaxis="y1"
# ))

# =========================
# BACKGROUND IMAGE
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

# =========================
# LAYOUT (NO GRIDLINES)
# =========================
fig.update_layout(
    images=layout_images,
    height=720,
    legend=dict(
        orientation="h",
        y=1.12,
        font=dict(size=18)
    ),
    xaxis=dict(
        title=dict(text="Age", font=dict(size=30)),
        tickfont=dict(size=24),
        tickmode="linear",
        dtick=5,
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    # yaxis=dict(
    #     title=dict(text="Cash Flow / Expenses ($)", font=dict(size=30)),
    #     tickfont=dict(size=24),
    #     tickprefix="$",
    #     showgrid=False,
    #     zeroline=False,
    #     fixedrange=True
    # ),
    yaxis2=dict(
        title=dict(text="Net Worth ($)", font=dict(size=30)),
        tickfont=dict(size=24),
        overlaying="y",
        side="right",
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    plot_bgcolor="rgba(255,255,255,0.30)",
    margin=dict(t=50, b=50, l=70, r=70)
)

st.plotly_chart(fig, use_container_width=True)


# =========================
fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=df["Age"], y=df["Cash"], name="Cash"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["IRA / Stocks"], name="IRA / Stocks"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["Home Value"], name="Home Value", line=dict(dash="dot")))

fig2.update_layout(
    images=layout_images,
    height=600,
    xaxis=dict(title="Age", tickfont=dict(size=18)),
    yaxis=dict(title="Value", tickfont=dict(size=18), tickprefix="$"),
    legend=dict(orientation="h"),
    plot_bgcolor="rgba(255,255,255,0.35)"
)

st.plotly_chart(fig2, use_container_width=True)

# =========================
# DATA TABLE (COLLAPSIBLE)
# =========================
with st.expander("Show Projection Data"):
    display_df = df.copy()

    currency_cols = [
        "Net Worth",
        "Expenses",
        "Cash Flow",
        "Cash",
        "IRA / Stocks",
        "Home Value"
    ]

    for col in currency_cols:
        display_df[col] = display_df[col].map(lambda x: f"${x:,.0f}")

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
