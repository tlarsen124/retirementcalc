import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import base64

st.set_page_config(page_title="Retirement Financial Overview", layout="wide")

# ============================================================
# Helpers
# ============================================================
def load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def annual_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard amortizing loan annual payment."""
    if years <= 0 or principal <= 0:
        return 0.0
    r = annual_rate
    if r <= 0:
        return principal / years
    return principal * (r * (1 + r) ** years) / ((1 + r) ** years - 1)

def amortize_one_year(balance: float, annual_rate: float, annual_pmt: float) -> tuple[float, float, float]:
    """Return (new_balance, interest_paid, principal_paid) for one year."""
    if balance <= 0 or annual_pmt <= 0:
        return max(balance, 0.0), 0.0, 0.0
    interest = balance * annual_rate
    principal = max(annual_pmt - interest, 0.0)
    new_balance = max(balance - principal, 0.0)
    return new_balance, interest, principal

def care_level_for_year(
    current_age: int,
    start_age: int,
    yrs_to_ind: int | None,
    yrs_to_assist: int | None,
    yrs_to_memory: int | None
) -> str:
    """Returns one of: 'None', 'Independent', 'Assisted', 'Memory'."""
    level = "None"
    if yrs_to_ind is not None and current_age >= start_age + yrs_to_ind:
        level = "Independent"
    if yrs_to_assist is not None and current_age >= start_age + yrs_to_assist:
        level = "Assisted"
    if yrs_to_memory is not None and current_age >= start_age + yrs_to_memory:
        level = "Memory"
    return level

# ============================================================
# Background image
# ============================================================
bg_image = load_image_base64("assets/background.jpg")

# ============================================================
# Sidebar Inputs
# ============================================================
st.sidebar.header("Key Assumptions")
start_age = st.sidebar.number_input("Age", min_value=50, max_value=95, value=70)
end_age = 95

home_status = st.sidebar.radio(
    "Home Situation",
    ["Do not own", "Own outright", "Own with mortgage"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("Home Details")
original_cost_basis = st.sidebar.number_input("Original Cost Basis ($)", value=550000, step=10000)
home_value_now = st.sidebar.number_input("Value Now ($)", value=1100000, step=25000)
improvements = st.sidebar.number_input("Improvements ($)", value=50000, step=5000)

# Mortgage (only if "Own with mortgage")
mortgage_balance = 0.0
mortgage_term_years = 0
mortgage_rate = 0.0

if home_status == "Own with mortgage":
    with st.sidebar.expander("Mortgage Details", expanded=True):
        mortgage_balance = st.number_input("Existing Mortgage Balance ($)", value=420000.0, step=10000.0, format="%.2f")
        mortgage_term_years = st.number_input("Remaining Term (yrs)", value=11, min_value=1, max_value=40)
        mortgage_rate = st.number_input("Existing Mortgage Rate (%)", value=2.40, step=0.05) / 100.0

# Section 121 assumptions
st.sidebar.markdown("---")
st.sidebar.subheader("Home Sale Tax Assumptions")
single = st.sidebar.checkbox("Single", value=True)
qualified_121 = st.sidebar.checkbox("121 Qualified Property", value=True)

default_121 = 250000 if single else 500000
exclusion_121 = st.sidebar.number_input("121 Tax Deduction / Exclusion ($)", value=float(default_121), step=10000)

sell_home = st.sidebar.checkbox("Sell home", value=True if home_status != "Do not own" else False, disabled=(home_status == "Do not own"))
sell_in_years = st.sidebar.number_input(
    "Sell home in (x) years",
    min_value=0,
    max_value=max(0, end_age - start_age),
    value=5,
    disabled=not sell_home
)

sale_cost_pct = st.sidebar.number_input("Sale Cost %", value=6.0, step=0.25) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Income (Monthly)")
ssn_m = st.sidebar.number_input("SSN ($/mo)", value=1300, step=50)
pension_m = st.sidebar.number_input("Pension ($/mo)", value=2300, step=50)
employment_m = st.sidebar.number_input("Employment ($/mo)", value=0, step=100)
other_income_m = st.sidebar.number_input("Other Income ($/mo)", value=0, step=100)
rental_income_m = st.sidebar.number_input("Rental Income (net) ($/mo)", value=0, step=100)

st.sidebar.markdown("---")
st.sidebar.subheader("Investments")
cash_start = st.sidebar.number_input("Cash ($)", value=45000, step=5000)
money_market_start = st.sidebar.number_input("Money Market ($)", value=100000, step=5000)
ira_start = st.sidebar.number_input("IRA ($)", value=1200000, step=25000)
other_taxable_start = st.sidebar.number_input("Other Investments (Taxable) ($)", value=0, step=5000)

st.sidebar.markdown("---")
st.sidebar.subheader("Living Expenses")
living_monthly = st.sidebar.number_input("Average Monthly ($)", value=3151, step=50)

st.sidebar.markdown("---")
st.sidebar.subheader("Care Transitions (years from now)")
yrs_to_ind = st.sidebar.number_input("Independent Living in (years)", value=2, min_value=0, max_value=60)
yrs_to_assist = st.sidebar.number_input("Assisted Living in (years)", value=10, min_value=0, max_value=60)
yrs_to_memory = st.sidebar.number_input("Memory Care in (years)", value=20, min_value=0, max_value=60)

st.sidebar.markdown("---")
st.sidebar.subheader("Taxes")
avg_tax_rate = st.sidebar.number_input("Average Tax Rate (%)", value=30.0, step=0.5) / 100.0
cap_gains_rate = st.sidebar.number_input("Capital Gain Tax Rate (%)", value=25.0, step=0.5) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Inflation & Growth")
infl_living = st.sidebar.number_input("Living Inflation (%)", value=3.0, step=0.25) / 100.0
infl_care = st.sidebar.number_input("Care Inflation (%)", value=5.0, step=0.25) / 100.0

growth_home = st.sidebar.number_input("Home Value Growth (%)", value=4.0, step=0.25) / 100.0
growth_money_market = st.sidebar.number_input("Money Market Growth (%)", value=4.5, step=0.25) / 100.0
growth_ira = st.sidebar.number_input("IRA Growth (%)", value=7.0, step=0.25) / 100.0
growth_stocks = st.sidebar.number_input("Stocks / Taxable Growth (%)", value=7.0, step=0.25) / 100.0
growth_home_account = st.sidebar.number_input("Stocks after home sale (Home Account) Growth (%)", value=7.0, step=0.25) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Spending / Depletion Order")
order_options = ["Cash", "Money Market", "Other Taxable", "IRA", "Home Account (after sale only)"]
withdrawal_order = st.sidebar.multiselect(
    "Choose depletion order (top = deplete first)",
    options=order_options,
    default=["Cash", "Money Market", "Other Taxable", "IRA", "Home Account (after sale only)"]
)
# Ensure we always have all accounts in some order
for opt in order_options:
    if opt not in withdrawal_order:
        withdrawal_order.append(opt)

st.sidebar.markdown("---")
st.sidebar.subheader("Chart Controls")
show_expenses = st.sidebar.checkbox("Show Expenses", True)
show_cashflow = st.sidebar.checkbox("Show Cash Flow", True)
show_background = st.sidebar.checkbox("Show Background Image", True)
image_opacity = st.sidebar.slider("Background Image Strength", 0.30, 1.00, 0.65, 0.05)

# ============================================================
# Projection
# ============================================================
ages = np.arange(start_age, end_age + 1)
years = np.arange(0, len(ages))  # 0..N-1

# Home values over time (if owned)
if home_status == "Do not own":
    home_values = np.zeros_like(years, dtype=float)
else:
    home_values = home_value_now * (1 + growth_home) ** years

sale_year_index = sell_in_years if sell_home else None
sale_age = start_age + sell_in_years if sell_home else None

# Mortgage schedule
mort_bal = float(mortgage_balance)
mort_annual_pmt = annual_payment(mort_bal, mortgage_rate, int(mortgage_term_years)) if home_status == "Own with mortgage" else 0.0

# Account balances
cash = float(cash_start)
mm = float(money_market_start)
ira = float(ira_start)
taxable = float(other_taxable_start)
home_account = 0.0  # only gets proceeds after sale

# Costs
living_annual = living_monthly * 12.0

# We’ll estimate care annual base costs; you can later make these user-editable if you want
care_cost_base = {
    "Independent": 50000.0,
    "Assisted": 60000.0,
    "Memory": 90000.0
}
# Starting care costs (today dollars) – inflated by infl_care each year when active
care_ind_cost = care_cost_base["Independent"]
care_assist_cost = care_cost_base["Assisted"]
care_memory_cost = care_cost_base["Memory"]

# Series to store
net_worth_series = []
expenses_series = []
cashflow_series = []

cash_series = []
mm_series = []
ira_series = []
taxable_series = []
home_account_series = []
home_value_series = []
mortgage_series = []

# Track if home sold
home_sold = False

for i, age in enumerate(ages):
    # Determine care level
    level = care_level_for_year(
        current_age=int(age),
        start_age=int(start_age),
        yrs_to_ind=int(yrs_to_ind) if yrs_to_ind is not None else None,
        yrs_to_assist=int(yrs_to_assist) if yrs_to_assist is not None else None,
        yrs_to_memory=int(yrs_to_memory) if yrs_to_memory is not None else None,
    )

    # Annual incomes (net rental already)
    gross_income_annual = (ssn_m + pension_m + employment_m + other_income_m + rental_income_m) * 12.0

    # Taxes (simple estimate): apply avg tax rate to gross income
    income_tax = gross_income_annual * avg_tax_rate
    net_income_annual = gross_income_annual - income_tax

    # Expenses:
    # If in any care, STOP adding base living expenses and use care cost instead.
    if level == "None":
        total_expenses = living_annual
    elif level == "Independent":
        total_expenses = care_ind_cost
    elif level == "Assisted":
        total_expenses = care_assist_cost
    else:
        total_expenses = care_memory_cost

    # Mortgage payment (only while mortgage exists and before sale)
    mortgage_pmt = 0.0
    if home_status == "Own with mortgage" and mort_bal > 0 and (not home_sold):
        mortgage_pmt = mort_annual_pmt
        total_expenses += mortgage_pmt

    # Investment growth (end of year)
    # We use "growth" as simple annual compounding on balances
    cash_growth = 0.0  # cash does not earn by default (you could tie to MM if desired)
    mm_growth_amt = mm * growth_money_market
    ira_growth_amt = ira * growth_ira
    taxable_growth_amt = taxable * growth_stocks
    home_account_growth_amt = home_account * growth_home_account

    # Cash flow BEFORE withdrawals: net income + investment growth (we treat growth as a source) - expenses
    # This is an accounting choice aligned to your earlier model style.
    cash_flow = net_income_annual + mm_growth_amt + ira_growth_amt + taxable_growth_amt + home_account_growth_amt - total_expenses

    # Add growth to balances (so it is reflected in assets)
    mm += mm_growth_amt
    ira += ira_growth_amt
    taxable += taxable_growth_amt
    home_account += home_account_growth_amt
    cash += cash_growth

    # If cash_flow is positive, it accumulates to CASH (simple assumption)
    # If negative, we withdraw according to the selected order.
    if cash_flow >= 0:
        cash += cash_flow
    else:
        shortfall = -cash_flow

        # Withdraw in chosen order
        for bucket in withdrawal_order:
            if shortfall <= 0:
                break

            if bucket == "Cash":
                take = min(cash, shortfall)
                cash -= take
                shortfall -= take

            elif bucket == "Money Market":
                take = min(mm, shortfall)
                mm -= take
                shortfall -= take

            elif bucket == "Other Taxable":
                take = min(taxable, shortfall)
                taxable -= take
                shortfall -= take

            elif bucket == "IRA":
                take = min(ira, shortfall)
                ira -= take
                shortfall -= take

            elif bucket == "Home Account (after sale only)":
                # Not allowed until home is sold / proceeds exist
                if home_account > 0:
                    take = min(home_account, shortfall)
                    home_account -= take
                    shortfall -= take

        # If still shortfall, cash goes to 0 and accounts are exhausted (no negative balances)
        # We’ll just keep everything floored at 0.
        if shortfall > 0:
            # In a more advanced model, you'd flag insolvency here
            pass

    # Amortize mortgage for one year (after payment)
    if home_status == "Own with mortgage" and mort_bal > 0 and (not home_sold):
        mort_bal, _, _ = amortize_one_year(mort_bal, mortgage_rate, mort_annual_pmt)

    # Home sale event
    if sell_home and (i == sale_year_index) and (home_status != "Do not own") and (not home_sold):
        sale_price = home_values[i]  # value at sale year
        selling_costs = sale_price * sale_cost_pct

        adjusted_basis = original_cost_basis + improvements
        gain_before_exclusion = sale_price - selling_costs - adjusted_basis

        exclusion = exclusion_121 if qualified_121 else 0.0
        taxable_gain = max(gain_before_exclusion - exclusion, 0.0)
        cap_gains_tax = taxable_gain * cap_gains_rate

        # Pay off remaining mortgage at sale if applicable
        mortgage_payoff = mort_bal if home_status == "Own with mortgage" else 0.0
        mort_bal = 0.0

        net_proceeds = sale_price - selling_costs - mortgage_payoff - cap_gains_tax
        net_proceeds = max(net_proceeds, 0.0)

        # Proceeds go to Home Account (brokerage)
        home_account += net_proceeds

        # Home value becomes 0 after sale going forward
        home_sold = True

    # Home value for this year
    hv = 0.0
    if home_status != "Do not own":
        hv = 0.0 if home_sold else home_values[i]

    # Net Worth = all assets - liabilities
    # Assets: cash + money market + IRA + taxable + home account + home value
    # Liabilities: remaining mortgage balance (if not sold) + debt input
    liabilities = debt + mort_bal
    total_assets = cash + mm + ira + taxable + home_account + hv
    net_worth = total_assets - liabilities

    # Store series
    net_worth_series.append(net_worth)
    expenses_series.append(total_expenses)
    cashflow_series.append(cash_flow)

    cash_series.append(cash)
    mm_series.append(mm)
    ira_series.append(ira)
    taxable_series.append(taxable)
    home_account_series.append(home_account)
    home_value_series.append(hv)
    mortgage_series.append(mort_bal)

    # Inflate living/care costs for next year
    living_annual *= (1 + infl_living)
    care_ind_cost *= (1 + infl_care)
    care_assist_cost *= (1 + infl_care)
    care_memory_cost *= (1 + infl_care)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth_series,
    "Expenses": expenses_series,
    "Cash Flow": cashflow_series,
    "Cash": cash_series,
    "Money Market": mm_series,
    "IRA": ira_series,
    "Other Taxable": taxable_series,
    "Home Account": home_account_series,
    "Home Value": home_value_series,
    "Mortgage Balance": mortgage_series
})

# ============================================================
# Milestones (Net Worth)
# ============================================================
start_idx = 0
peak_idx = int(df["Net Worth"].idxmax())
mid_idx = int((start_idx + peak_idx) / 2)

decline_candidates = df.loc[peak_idx:]
decline_idx_candidates = decline_candidates[
    decline_candidates["Net Worth"] < 0.9 * df.loc[peak_idx, "Net Worth"]
].index
decline_idx = int(decline_idx_candidates[0]) if len(decline_idx_candidates) > 0 else int(df.index[-1])

milestones = [
    ("Start", start_idx, "#2c3e50"),
    ("Building Wealth", mid_idx, "#27ae60"),
    ("Peak Net Worth", peak_idx, "#f1c40f"),
    ("Reassessment Phase", decline_idx, "#e67e22"),
]

# ============================================================
# Header
# ============================================================
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Financial Overview</h1>
    <p style="text-align:center; font-size:22px; color:#555;">
    A clear view of net worth, expenses, and cash flow over time
    </p>
    """,
    unsafe_allow_html=True
)

# Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Starting Net Worth", f"${df.iloc[0]['Net Worth']:,.0f}")
c2.metric("Peak Net Worth", f"${df['Net Worth'].max():,.0f}")
c3.metric("Ending Net Worth", f"${df.iloc[-1]['Net Worth']:,.0f}")

# ============================================================
# Chart 1: Net Worth + optional Expenses/Cash Flow
# ============================================================
left_values = []
if show_expenses:
    left_values.extend(df["Expenses"].values.tolist())
if show_cashflow:
    left_values.extend(df["Cash Flow"].values.tolist())

left_min, left_max = (-1, 1) if not left_values else (min(left_values) * 0.9, max(left_values) * 1.1)
right_min = df["Net Worth"].min() * 0.9
right_max = df["Net Worth"].max() * 1.1

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

# Expenses (left)
if show_expenses:
    fig.add_trace(go.Scatter(
        x=df["Age"],
        y=df["Expenses"],
        name="Expenses",
        line=dict(color="#c0392b", width=2.5, dash="dot"),
        opacity=0.85,
        yaxis="y1"
    ))

# Cash Flow (left)
if show_cashflow:
    fig.add_trace(go.Scatter(
        x=df["Age"],
        y=df["Cash Flow"],
        name="Cash Flow",
        line=dict(color="#27ae60", width=2.5),
        opacity=0.85,
        yaxis="y1"
    ))

# Background image
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

fig.update_layout(
    images=layout_images,
    height=720,
    legend=dict(orientation="h", y=1.1, font=dict(size=18)),
    xaxis=dict(
        title=dict(text="Age", font=dict(size=30)),
        tickfont=dict(size=24),
        tickmode="linear",
        dtick=5,
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    yaxis=dict(
        title=dict(text="Cash Flow / Expenses ($)", font=dict(size=30)),
        tickfont=dict(size=24),
        range=[left_min, left_max],
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    yaxis2=dict(
        title=dict(text="Net Worth ($)", font=dict(size=30)),
        tickfont=dict(size=24),
        overlaying="y",
        side="right",
        range=[right_min, right_max],
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    plot_bgcolor="rgba(255,255,255,0.30)",
    margin=dict(t=50, b=50, l=70, r=70)
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "toImageButtonOptions": {
            "format": "png",
            "filename": "retirement_journey",
            "scale": 3
        }
    }
)

st.markdown("<p style='text-align:center; color:#666;'>Illustrative projections only.</p>", unsafe_allow_html=True)

# ============================================================
# Chart 2: Account Balances (requested)
# ============================================================
st.markdown("### Asset Breakdown Over Time")

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=df["Age"], y=df["Cash"],
    name="Cash",
    line=dict(width=3, shape="spline")
))
fig2.add_trace(go.Scatter(
    x=df["Age"], y=df["Money Market"],
    name="Money Market",
    line=dict(width=3, shape="spline")
))
fig2.add_trace(go.Scatter(
    x=df["Age"], y=df["IRA"],
    name="IRA",
    line=dict(width=3, shape="spline")
))
fig2.add_trace(go.Scatter(
    x=df["Age"], y=df["Home Account"],
    name="Home Account (after sale)",
    line=dict(width=3, shape="spline")
))
fig2.add_trace(go.Scatter(
    x=df["Age"], y=df["Home Value"],
    name="Home Value",
    line=dict(width=3, shape="spline", dash="dot")
))

# Make it clean and readable
y_min2 = 0
y_max2 = max(
    df["Cash"].max(),
    df["Money Market"].max(),
    df["IRA"].max(),
    df["Home Account"].max(),
    df["Home Value"].max()
) * 1.1

fig2.update_layout(
    height=620,
    legend=dict(orientation="h", y=1.1, font=dict(size=16)),
    xaxis=dict(
        title=dict(text="Age", font=dict(size=26)),
        tickfont=dict(size=20),
        tickmode="linear",
        dtick=5,
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    yaxis=dict(
        title=dict(text="Value ($)", font=dict(size=26)),
        tickfont=dict(size=20),
        range=[y_min2, y_max2],
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        fixedrange=True
    ),
    plot_bgcolor="white",
    margin=dict(t=40, b=40, l=70, r=40)
)

st.plotly_chart(
    fig2,
    use_container_width=True,
    config={
        "toImageButtonOptions": {
            "format": "png",
            "filename": "asset_breakdown",
            "scale": 3
        }
    }
)

with st.expander("Show Projection Table"):
    st.dataframe(df, use_container_width=True)
