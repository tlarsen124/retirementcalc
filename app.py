import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import base64

st.set_page_config(page_title="Retirement Financial Overview", layout="wide")

# =========================
# LOAD BACKGROUND IMAGE
# =========================
def load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# If your image is always present in repo at this path:
BG_PATH = "assets/background.jpg"
bg_image = load_image_base64(BG_PATH)

# =========================
# HELPER FUNCTIONS
# =========================
def money(x) -> str:
    try:
        return f"${x:,.0f}"
    except Exception:
        return str(x)

def annual_payment_from_loan(balance: float, annual_rate: float, term_years: int) -> float:
    """
    Standard amortizing loan annual payment approximation using monthly payment * 12.
    """
    if balance <= 0 or term_years <= 0:
        return 0.0
    r_m = annual_rate / 12.0
    n = term_years * 12
    if r_m <= 0:
        return balance / max(n, 1) * 12.0
    pmt_m = balance * (r_m * (1 + r_m) ** n) / ((1 + r_m) ** n - 1)
    return pmt_m * 12.0

def apply_annual_amortization(balance: float, annual_rate: float, annual_payment: float) -> float:
    """
    One-year amortization step:
      - interest on starting balance
      - principal reduction = payment - interest
    """
    if balance <= 0:
        return 0.0
    interest = balance * annual_rate
    principal = max(annual_payment - interest, 0.0)
    new_balance = max(balance - principal, 0.0)
    return new_balance

def compute_home_sale_net_proceeds(
    sale_price: float,
    sale_cost_pct: float,
    original_cost_basis: float,
    improvements: float,
    section121_qualified: bool,
    section121_deduction: float,
    cap_gains_rate: float,
    mortgage_balance: float
) -> dict:
    """
    Implements your rule:
    - Subtract cost basis, 121 deduction, sale cost, and improvements before taxes on the home sale.
    - Tax applies to taxable gain only (not to total proceeds).
    - Mortgage payoff reduces net cash proceeds (but not taxable gain).
    """
    sale_cost = sale_price * sale_cost_pct
    exclusion = section121_deduction if section121_qualified else 0.0

    taxable_gain = sale_price - sale_cost - original_cost_basis - improvements - exclusion
    taxable_gain = max(taxable_gain, 0.0)
    tax = taxable_gain * cap_gains_rate

    net_proceeds = sale_price - sale_cost - tax - mortgage_balance
    net_proceeds = max(net_proceeds, 0.0)

    return {
        "sale_price": sale_price,
        "sale_cost": sale_cost,
        "taxable_gain": taxable_gain,
        "tax": tax,
        "mortgage_payoff": mortgage_balance,
        "net_proceeds": net_proceeds
    }

def pick_withdrawal_order(option: str) -> list:
    """
    Returns a list of buckets in depletion order for deficits.
    Cash is always used first.
    Home Account is disallowed before sale (handled in simulation).
    """
    # Cash first always, then pick the rest
    if option == "Money Market → IRA → Home Account":
        return ["cash", "money_market", "ira", "home_account"]
    if option == "Money Market → Home Account → IRA":
        return ["cash", "money_market", "home_account", "ira"]
    if option == "IRA → Money Market → Home Account":
        return ["cash", "ira", "money_market", "home_account"]
    if option == "IRA → Home Account → Money Market":
        return ["cash", "ira", "home_account", "money_market"]
    if option == "Home Account → Money Market → IRA":
        return ["cash", "home_account", "money_market", "ira"]
    if option == "Home Account → IRA → Money Market":
        return ["cash", "home_account", "ira", "money_market"]
    # default
    return ["cash", "money_market", "ira", "home_account"]

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Key Assumptions")

current_age = st.sidebar.number_input("Age", min_value=50, max_value=95, value=70)
end_age = 95

own_home = st.sidebar.selectbox("Do you own your home?", ["Yes", "No"], index=1)

colA, colB = st.sidebar.columns(2)
single = colA.selectbox("Single", ["Yes", "No"], index=0)
section121_qualified = colB.selectbox("121 Qualified Property", ["Yes", "No"], index=0)

# Home inputs (only if owning a home)
if own_home == "Yes":
    st.sidebar.subheader("Home Details")
    original_cost_basis = st.sidebar.number_input("Original Cost Basis ($)", value=550000, step=25000)
    home_value_now = st.sidebar.number_input("Value Now ($)", value=1100000, step=50000)
    improvements = st.sidebar.number_input("Improvements ($)", value=50000, step=5000)
    mortgage_left = st.sidebar.number_input("Mortgage Left ($)", value=0, step=10000)

    # 121 deduction default depends on single/married
    default_121 = 250000 if single == "Yes" else 500000
    section121_deduction = st.sidebar.number_input("121 Tax Deduction ($)", value=float(default_121), step=50000)

    st.sidebar.subheader("Sell Home")
    sell_home = st.sidebar.selectbox("Sell home", ["Yes", "No"], index=0)
    sell_in_years = st.sidebar.number_input("Sell home in (x) years", min_value=0, max_value=60, value=5)
    sale_cost_pct = st.sidebar.slider("Sale Cost %", min_value=0.0, max_value=12.0, value=6.0, step=0.5) / 100.0
else:
    # dummy values
    original_cost_basis = 0.0
    home_value_now = 0.0
    improvements = 0.0
    mortgage_left = 0.0
    section121_deduction = 0.0
    sell_home = "No"
    sell_in_years = 0
    sale_cost_pct = 0.0

# Mortgage details expander (only if there is a mortgage)
mortgage_balance_input = float(mortgage_left) if own_home == "Yes" else 0.0
mortgage_term_years = 0
mortgage_rate = 0.0

if own_home == "Yes" and mortgage_balance_input > 0:
    with st.sidebar.expander("Mortgage Details (optional)"):
        mortgage_balance_input = st.number_input("Existing Mortgage Balance ($)", value=float(mortgage_balance_input), step=10000.0)
        mortgage_term_years = st.number_input("Remaining Term (yrs)", min_value=1, max_value=40, value=11)
        mortgage_rate = st.number_input("Existing Mortgage Rate (%)", value=2.40, step=0.10) / 100.0

st.sidebar.header("Income (Monthly)")
ssn_m = st.sidebar.number_input("SSN ($/mo)", value=1300, step=100)
pension_m = st.sidebar.number_input("Pension ($/mo)", value=2300, step=100)
employment_m = st.sidebar.number_input("Employment ($/mo)", value=0, step=100)
other_income_m = st.sidebar.number_input("Other Income ($/mo)", value=0, step=100)
rental_net_m = st.sidebar.number_input("Rental Income (net) ($/mo)", value=0, step=100)

st.sidebar.header("Investments")
cash_start = st.sidebar.number_input("Cash ($)", value=45000, step=5000)
money_market_start = st.sidebar.number_input("Money Market ($)", value=100000, step=5000)
ira_start = st.sidebar.number_input("IRA ($)", value=1200000, step=25000)
other_investments = st.sidebar.number_input("Other Investments ($)", value=0, step=5000)

st.sidebar.header("Living Expenses")
living_monthly = st.sidebar.number_input("Average monthly ($)", value=3151, step=100)

st.sidebar.header("Care Timeline (years from now)")
independent_in_years = st.sidebar.number_input("Independent Living in (X) years", min_value=0, max_value=60, value=2)
assisted_in_years = st.sidebar.number_input("Assisted Living in (X) years", min_value=0, max_value=60, value=10)
memory_in_years = st.sidebar.number_input("Memory Care in (X) years", min_value=0, max_value=60, value=20)

st.sidebar.subheader("Care Costs (Annual, today)")
independent_cost_annual = st.sidebar.number_input("Independent Living ($/yr)", value=50000, step=2500)
assisted_cost_annual = st.sidebar.number_input("Assisted Living ($/yr)", value=60000, step=2500)
memory_cost_annual = st.sidebar.number_input("Memory Care ($/yr)", value=90000, step=2500)

st.sidebar.header("Taxes")
avg_tax_rate = st.sidebar.slider("Average tax rate (%)", 0.0, 50.0, 30.0, 0.5) / 100.0
cap_gains_rate = st.sidebar.slider("Capital gain tax rate (%)", 0.0, 50.0, 25.0, 0.5) / 100.0

st.sidebar.header("Inflation")
living_infl = st.sidebar.slider("Living (%)", 0.0, 8.0, 3.0, 0.25) / 100.0
care_infl = st.sidebar.slider("Care (%)", 0.0, 10.0, 5.0, 0.25) / 100.0

st.sidebar.header("Growth")
stocks_after_home_sale = st.sidebar.slider("Stocks after home sale (%)", 0.0, 12.0, 7.0, 0.25) / 100.0
ira_growth = st.sidebar.slider("IRA (%)", 0.0, 12.0, 7.0, 0.25) / 100.0
money_market_growth = st.sidebar.slider("Money Market (%)", 0.0, 8.0, 4.5, 0.25) / 100.0
home_growth = st.sidebar.slider("Home Value (%)", 0.0, 10.0, 4.0, 0.25) / 100.0

st.sidebar.header("Withdrawal Strategy")
withdrawal_option = st.sidebar.selectbox(
    "If expenses exceed income, deplete from:",
    [
        "Money Market → IRA → Home Account",
        "Money Market → Home Account → IRA",
        "IRA → Money Market → Home Account",
        "IRA → Home Account → Money Market",
        "Home Account → Money Market → IRA",
        "Home Account → IRA → Money Market",
    ],
    index=0
)

st.sidebar.header("Chart Controls")
show_background = st.sidebar.checkbox("Show Background Image", True)
image_opacity = st.sidebar.slider("Background Image Strength", 0.30, 1.00, 0.65, 0.05)

# =========================
# DERIVED INPUTS
# =========================
start_age = int(current_age)
ages = np.arange(start_age, end_age + 1)

# Annualize income + apply average tax rate to income (simple estimate)
gross_income_annual_0 = 12.0 * (ssn_m + pension_m + employment_m + other_income_m + rental_net_m)
net_income_annual_0 = gross_income_annual_0 * (1.0 - avg_tax_rate)

living_annual_0 = 12.0 * living_monthly

# Care start ages
indep_age = start_age + int(independent_in_years)
assist_age = start_age + int(assisted_in_years)
memory_age = start_age + int(memory_in_years)

# Home sale age
sell_home_flag = (own_home == "Yes" and sell_home == "Yes" and sell_in_years > 0)
home_sale_age = start_age + int(sell_in_years) if sell_home_flag else None

# =========================
# SIMULATION
# =========================
cash = float(cash_start)
money_market = float(money_market_start)
ira = float(ira_start)
home_account = 0.0  # only funded after home sale
home_value = float(home_value_now) if own_home == "Yes" else 0.0

# treat other investments as part of IRA for now (simple) – or keep separate if you want
ira += float(other_investments)

mortgage_balance = float(mortgage_balance_input)
annual_mortgage_payment = annual_payment_from_loan(mortgage_balance, mortgage_rate, int(mortgage_term_years)) if mortgage_balance > 0 else 0.0

order = pick_withdrawal_order(withdrawal_option)

rows = []
sale_details = None

# current-year care costs
ind_cost = float(independent_cost_annual)
asst_cost = float(assisted_cost_annual)
mem_cost = float(memory_cost_annual)

net_income = float(net_income_annual_0)
living_cost = float(living_annual_0)

for age in ages:
    # Grow home value until sale
    if own_home == "Yes" and home_value > 0:
        home_value *= (1.0 + home_growth)

    # Determine care state and annual expense for this year
    # Rule: once in any care, STOP base living and REPLACE with care cost.
    care_level = "None"
    annual_expense = living_cost

    if age >= memory_age:
        care_level = "Memory Care"
        annual_expense = mem_cost
    elif age >= assist_age:
        care_level = "Assisted Living"
        annual_expense = asst_cost
    elif age >= indep_age:
        care_level = "Independent Living"
        annual_expense = ind_cost

    # Add mortgage payment to annual expense while mortgage exists
    if mortgage_balance > 0:
        annual_expense += annual_mortgage_payment

    # Home sale event (at start of year after appreciation) — proceeds go into Home Account
    if sell_home_flag and home_sale_age is not None and age == home_sale_age and home_value > 0:
        section121_ok = (section121_qualified == "Yes")
        sale_details = compute_home_sale_net_proceeds(
            sale_price=home_value,
            sale_cost_pct=sale_cost_pct,
            original_cost_basis=float(original_cost_basis),
            improvements=float(improvements),
            section121_qualified=section121_ok,
            section121_deduction=float(section121_deduction),
            cap_gains_rate=float(cap_gains_rate),
            mortgage_balance=float(mortgage_balance)
        )
        # Pay off mortgage from proceeds (already accounted in net proceeds)
        mortgage_balance = 0.0
        annual_mortgage_payment = 0.0

        # Fund the home account and remove home value
        home_account += sale_details["net_proceeds"]
        home_value = 0.0

    # Grow investment buckets (start-of-year growth)
    # Cash: no growth
    money_market *= (1.0 + money_market_growth)
    ira *= (1.0 + ira_growth)
    if home_account > 0:
        home_account *= (1.0 + stocks_after_home_sale)

    # Net cash flow from income vs expenses
    # (income is simplified; you can later add inflation to income if desired)
    net_cash_flow = net_income - annual_expense

    # If surplus: add to cash
    if net_cash_flow >= 0:
        cash += net_cash_flow
    else:
        deficit = -net_cash_flow

        # Withdraw in order; HOME ACCOUNT not allowed until after sale (i.e., while home_value > 0 or home_account == 0)
        # We interpret “Home account refers to proceeds only after sale” → available only if home_account > 0.
        buckets = {
            "cash": cash,
            "money_market": money_market,
            "ira": ira,
            "home_account": home_account
        }

        for b in order:
            if deficit <= 0:
                break

            if b == "home_account" and home_account <= 0:
                continue  # not available pre-sale

            available = buckets[b]
            if available <= 0:
                continue

            take = min(available, deficit)
            buckets[b] -= take
            deficit -= take

        # Update balances
        cash = buckets["cash"]
        money_market = buckets["money_market"]
        ira = buckets["ira"]
        home_account = buckets["home_account"]

        # If still deficit after draining everything, allow cash to go to 0 and stop (you can also track a "shortfall")
        # We'll keep it at zero and record a shortfall.
        shortfall = max(deficit, 0.0)

        if shortfall > 0:
            # clamp to zero, nothing else to do
            pass

    # Amortize mortgage yearly (after paying, balance reduces)
    if mortgage_balance > 0 and annual_mortgage_payment > 0:
        mortgage_balance = apply_annual_amortization(mortgage_balance, mortgage_rate, annual_mortgage_payment)

    total_assets = cash + money_market + ira + home_account + home_value
    net_worth = total_assets - mortgage_balance  # mortgage treated as liability

    rows.append({
        "Age": age,
        "Net Worth": net_worth,
        "Cash": cash,
        "Money Market": money_market,
        "IRA": ira,
        "Home Account": home_account,
        "Home Value": home_value,
        "Mortgage Balance": mortgage_balance,
        "Annual Expense": annual_expense,
        "Net Income (after tax)": net_income,
        "Care Level": care_level
    })

    # Inflate living and care costs over time
    living_cost *= (1.0 + living_infl)
    ind_cost *= (1.0 + care_infl)
    asst_cost *= (1.0 + care_infl)
    mem_cost *= (1.0 + care_infl)

# Results
df = pd.DataFrame(rows)

# =========================
# PAGE HEADER + METRICS
# =========================
st.markdown(
    """
    <h1 style="text-align:center;">Retirement Financial Overview</h1>
    <p style="text-align:center; font-size:20px; color:#555;">
    Net worth, expenses, income, and account balances over time
    </p>
    """,
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)
c1.metric("Starting Net Worth", money(df.iloc[0]["Net Worth"]))
c2.metric("Peak Net Worth", money(df["Net Worth"].max()))
c3.metric("Ending Net Worth", money(df.iloc[-1]["Net Worth"]))

# Optional: show sale details
if sale_details is not None:
    with st.expander("Home Sale Details"):
        st.write({
            "Sale Price": money(sale_details["sale_price"]),
            "Sale Cost": money(sale_details["sale_cost"]),
            "Taxable Gain": money(sale_details["taxable_gain"]),
            "Capital Gains Tax": money(sale_details["tax"]),
            "Mortgage Payoff": money(sale_details["mortgage_payoff"]),
            "Net Proceeds (to Home Account)": money(sale_details["net_proceeds"])
        })

# =========================
# CHART 1: NET WORTH + (OPTIONAL) EXPENSE/INCOME
# =========================
left_values = list(df["Annual Expense"].values) + list(df["Net Income (after tax)"].values)
left_min, left_max = min(left_values) * 0.9, max(left_values) * 1.1
right_min, right_max = df["Net Worth"].min() * 0.9, df["Net Worth"].max() * 1.1

fig1 = go.Figure()

# Net worth line
fig1.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    name="Net Worth",
    line=dict(color="#162f3a", width=6, shape="spline"),
    yaxis="y2"
))

# Milestones: start, peak, mid, decline
start_idx = 0
peak_idx = int(df["Net Worth"].idxmax())
mid_idx = int((start_idx + peak_idx) / 2)

decline_candidates = df.loc[peak_idx:]
decline_hits = decline_candidates[decline_candidates["Net Worth"] < 0.9 * df.loc[peak_idx, "Net Worth"]].index
decline_idx = int(decline_hits[0]) if len(decline_hits) > 0 else int(df.index[-1])

milestones = [
    ("Start", start_idx, "#2c3e50"),
    ("Building Wealth", mid_idx, "#27ae60"),
    ("Peak Net Worth", peak_idx, "#f1c40f"),
    ("Reassessment Phase", decline_idx, "#e67e22"),
]

for label, idx, color in milestones:
    fig1.add_trace(go.Scatter(
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

# Expenses and Income on left axis
fig1.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Annual Expense"],
    name="Annual Expense",
    line=dict(width=2.5, dash="dot"),
    opacity=0.85,
    yaxis="y1"
))

fig1.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Income (after tax)"],
    name="Net Income (after tax)",
    line=dict(width=2.5),
    opacity=0.85,
    yaxis="y1"
))

# Background image
layout_images = []
if show_background:
    layout_images.append(dict(
        source=f"data:image/jpeg;base64,{bg_image}",
        xref="paper", yref="paper",
        x=0, y=1,
        sizex=1, sizey=1,
        sizing="stretch",
        opacity=image_opacity,
        layer="below"
    ))

fig1.update_layout(
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
        title=dict(text="Income / Expense ($)", font=dict(size=30)),
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
    fig1,
    use_container_width=True,
    config={
        "toImageButtonOptions": {
            "format": "png",
            "filename": "retirement_overview",
            "scale": 3
        }
    }
)

# =========================
# CHART 2: ACCOUNT BALANCES (requested)
# =========================
fig
