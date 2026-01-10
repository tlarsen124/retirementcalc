import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import base64
import re

st.set_page_config(page_title="Retirement Overview", layout="wide")

# =========================
# BACKGROUND IMAGE
# =========================
def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = load_image_base64("assets/background.jpg")

# =========================
# MORTGAGE CALCULATION FUNCTIONS
# =========================

def calculate_monthly_payment(principal, annual_rate, years):
    """
    Calculate monthly mortgage payment using standard amortization formula.
    Formula: P * (r * (1+r)^n) / ((1+r)^n - 1)
    where P = principal, r = monthly rate, n = number of months
    """
    if principal <= 0 or years <= 0:
        return 0
    
    monthly_rate = annual_rate / 12
    num_months = years * 12
    
    if monthly_rate == 0:
        return principal / num_months
    
    payment = principal * (monthly_rate * (1 + monthly_rate) ** num_months) / ((1 + monthly_rate) ** num_months - 1)
    return payment


def calculate_annual_mortgage_amortization(principal, monthly_payment, monthly_rate, months_remaining):
    """
    Calculate annual mortgage payment breakdown (interest and principal).
    Returns (total_interest, total_principal, new_balance)
    """
    if principal <= 0 or months_remaining <= 0:
        return 0, 0, 0
    
    total_interest = 0
    total_principal = 0
    balance = principal
    
    # Calculate for 12 months (one year)
    for month in range(min(12, months_remaining)):
        if balance <= 0:
            break
        
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        
        # Adjust if payment exceeds remaining balance
        if principal_payment > balance:
            principal_payment = balance
            monthly_payment_adjusted = principal_payment + interest_payment
        else:
            monthly_payment_adjusted = monthly_payment
        
        total_interest += interest_payment
        total_principal += principal_payment
        balance -= principal_payment
    
    return total_interest, total_principal, max(0, balance)


# =========================
# DATA IMPORT FUNCTIONS
# =========================

def parse_pasted_data(pasted_text):
    """
    Parse pasted tab-separated or space-separated data from Google Sheets.
    Returns a dictionary mapping parameter names to values.
    """
    data_dict = {}
    lines = pasted_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try tab separation first (most common from Google Sheets)
        if '\t' in line:
            parts = line.split('\t', 1)
        else:
            # Try multiple spaces
            parts = re.split(r'\s{2,}', line, 1)
            if len(parts) < 2:
                # Try single space as last resort
                parts = line.split(' ', 1)
        
        if len(parts) >= 2:
            param_name = parts[0].strip()
            value_str = parts[1].strip()
            
            # Try to convert to number
            try:
                # Remove commas, dollar signs, and percent signs
                value_str_clean = value_str.replace(',', '').replace('$', '').replace('%', '').strip()
                # Try float first, then int
                try:
                    value = float(value_str_clean)
                    # If it's a whole number, convert to int
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    value = value_str
            except:
                value = value_str
            
            data_dict[param_name] = value
    
    return data_dict


def map_parameter_to_variable(param_name):
    """
    Map a parameter name from the Google Sheet to the corresponding variable name.
    Returns the variable name if found, None otherwise.
    Uses case-insensitive matching and handles variations.
    Prioritizes more specific (longer) matches by checking all possible matches first.
    """
    param_lower = param_name.lower()
    # Remove common suffixes that might vary
    param_clean = re.sub(r'\s*\([^)]*\)\s*', '', param_lower)  # Remove parentheses content
    param_clean = param_clean.replace('$', '').replace('%', '').strip()
    
    # Mapping dictionary with various possible parameter name variations
    # IMPORTANT: Growth-related fields must come before their base fields to ensure correct matching
    # Keywords within each mapping should be ordered from most specific (longest) to least specific
    mappings = [
        ('start_age', ['age']),
        # Growth fields must come before base fields
        ('home_growth', ['home value growth', 'home growth']),
        ('home_value_now', ['home value today', 'home value']),
        ('tax_deductions', ['cost basis + improvements + 121 deduction', 'cost basis', 'improvements', '121 deduction', 'tax deductions']),
        ('sell_home_years', ['sell home in', 'sell home', 'home sale years']),
        ('sale_cost_pct', ['sale cost']),
        ('mortgage_balance', ['existing mortgage balance', 'mortgage balance']),
        ('mortgage_term', ['remaining term', 'mortgage term']),
        ('mortgage_rate', ['existing mortgage rate', 'mortgage rate']),
        ('mortgage_interest_cap', ['cap on mortgage interest']),
        ('balloon_payment', ['balloon payment']),
        ('ssn_income', ['ssn', 'social security']),
        ('pension_income', ['pension']),
        ('employment_income', ['employment']),
        ('cash_start', ['cash / money market', 'cash', 'money market']),
        # Growth fields must come before base fields
        ('stock_growth', ['stocks / ira growth', 'stocks growth', 'ira growth', 'stock growth']),
        ('ira_start', ['ira / stocks', 'ira', 'stocks']),
        # IMPORTANT: Cost fields must come before years fields to match correctly
        ('self_cost', ['self-sufficient annual cost', 'self sufficient annual cost']),
        ('self_years', ['self-sufficient', 'self sufficient']),
        ('ind_cost', ['independent living annual cost']),
        ('ind_years', ['independent living starts in', 'independent living']),
        ('assist_cost', ['assisted living annual cost']),
        ('assist_years', ['assisted living starts in', 'assisted living']),
        ('memory_cost', ['memory care annual cost']),
        ('memory_years', ['memory care starts in', 'memory care']),
        ('avg_tax_rate', ['average tax rate']),
        ('cap_gains_rate', ['capital gains tax', 'capital gains']),
        ('living_infl', ['living inflation', 'inflation']),
        ('care_infl', ['care level inflation', 'care inflation', 'care infl']),
        ('cash_growth', ['money market growth', 'cash growth']),
    ]
    
    # Collect all possible matches with their keyword lengths
    # This allows us to pick the best (longest keyword) match
    matches = []
    
    for var_name, keywords in mappings:
        # Sort keywords from longest to shortest for this variable
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        
        for keyword in sorted_keywords:
            keyword_lower = keyword.lower()
            keyword_clean = keyword_lower.replace('$', '').replace('%', '').strip()
            
            # Check multiple matching strategies:
            # 1. Exact match at start (most reliable)
            # 2. Cleaned match at start
            # 3. Word-boundary match (keyword appears as whole words)
            
            # Strategy 1: Direct start match
            starts_with = (param_lower.startswith(keyword_lower) or 
                          param_clean.startswith(keyword_clean))
            
            if starts_with:
                matches.append((len(keyword), var_name))
                break  # Found a match for this variable, move to next
            
            # Strategy 2: Word-boundary match (for keywords that don't start the parameter)
            # Create a regex pattern that matches the keyword as whole words
            # Replace spaces in keyword with \s+ to allow flexible spacing
            keyword_regex = re.sub(r'\s+', r'\\s+', re.escape(keyword_clean))
            # Match at start, or after word boundary (space, slash, or start), and before word boundary or end
            pattern = r'(^|[\s/])' + keyword_regex + r'([\s%/]|$)'
            
            if re.search(pattern, param_clean, re.IGNORECASE):
                matches.append((len(keyword), var_name))
                break  # Found a match for this variable, move to next
    
    # Return the match with the longest keyword (most specific)
    if matches:
        matches.sort(reverse=True)  # Sort by keyword length (longest first)
        return matches[0][1]  # Return the variable name of the longest match
    
    return None


def import_data(pasted_text):
    """
    Import data from pasted text, parse it, map to variables, and store in session state.
    Returns (success: bool, message: str, imported_count: int)
    """
    try:
        # Parse the pasted data
        data_dict = parse_pasted_data(pasted_text)
        
        if not data_dict:
            return False, "No data found. Please paste data in 'Parameter Name | Value' format.", 0
        
        # Default values for validation
        defaults = {
            'start_age': 70,
            'home_value_now': 1_100_000,
            'home_growth': 4.0,
            'tax_deductions': 300_000.0,
            'sell_home_years': 5,
            'sale_cost_pct': 6.0,
            'mortgage_balance': 420_000,
            'mortgage_term': 11,
            'mortgage_rate': 2.40,
            'mortgage_interest_cap': 750_000,
            'balloon_payment': 0,
            'ssn_income': 15_600,
            'pension_income': 27_600,
            'employment_income': 0,
            'cash_start': 145_000,
            'ira_start': 1_200_000,
            'self_years': 2,
            'self_cost': 37_812,
            'ind_years': 2,
            'ind_cost': 108_000,
            'assist_years': 10,
            'assist_cost': 114_000,
            'memory_years': 20,
            'memory_cost': 120_000,
            'avg_tax_rate': 30.0,
            'cap_gains_rate': 25.0,
            'living_infl': 3.0,
            'care_infl': 4.0,
            'stock_growth': 7.0,
            'cash_growth': 4.5,
        }
        
        imported_count = 0
        errors = []
        
        # Map and validate each parameter
        for param_name, value in data_dict.items():
            var_name = map_parameter_to_variable(param_name)
            
            if var_name is None:
                continue  # Skip unmapped parameters
            
            # Validate and convert value
            try:
                if isinstance(value, str):
                    # Try to convert string to number
                    value_clean = value.replace(',', '').replace('$', '').strip()
                    if '.' in value_clean:
                        value = float(value_clean)
                    else:
                        value = int(value_clean)
                
                # Validate ranges for specific variables
                if var_name == 'start_age' and not (50 <= value <= 95):
                    errors.append(f"{param_name}: Age must be between 50 and 95")
                    continue
                elif var_name == 'sell_home_years' and not (0 <= value <= 40):
                    errors.append(f"{param_name}: Sell Home In (Years) must be between 0 and 40")
                    continue
                elif var_name == 'mortgage_term' and not (0 <= value <= 30):
                    errors.append(f"{param_name}: Mortgage Term (Years) must be between 0 and 30")
                    continue
                elif var_name in ['home_growth', 'sale_cost_pct', 'avg_tax_rate', 'cap_gains_rate', 
                                 'living_infl', 'care_infl', 'stock_growth', 'cash_growth', 'mortgage_rate']:
                    # These are percentages - validate 0-100 range
                    if not (0 <= value <= 100):
                        errors.append(f"{param_name}: Percentage must be between 0 and 100")
                        continue
                    # Store as percentage (0-100) for sliders
                    st.session_state[f'imported_{var_name}'] = value
                else:
                    # Store as-is for other values
                    st.session_state[f'imported_{var_name}'] = value
                
                imported_count += 1
                
            except (ValueError, TypeError) as e:
                errors.append(f"{param_name}: Could not convert '{value}' to a number")
                continue
        
        if imported_count == 0:
            return False, "No valid parameters found. Please check your parameter names.", 0
        
        message = f"✓ Successfully imported {imported_count} values. You can now edit them using the inputs below."
        if errors:
            message += f" ({len(errors)} errors ignored)"
        
        return True, message, imported_count
        
    except Exception as e:
        return False, f"⚠ Error: {str(e)}", 0


# =========================
# SIDEBAR INPUTS
# =========================

# Import mode toggle
st.sidebar.markdown("### Data Input Method")
# Initialize input_mode in session state if not present
if 'input_mode' not in st.session_state:
    st.session_state['input_mode'] = 'manual'

input_mode = st.sidebar.radio(
    "Choose input method:",
    ["Manual Input", "Import from Data"],
    index=1 if st.session_state.get('input_mode') == 'import' else 0
)

st.session_state['input_mode'] = 'import' if input_mode == "Import from Data" else 'manual'

# Show import interface if import mode is selected
if input_mode == "Import from Data":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Import Data from Google Sheets**")
    st.sidebar.markdown("*Paste your data here (Parameter Name | Value format)*")
    
    pasted_data = st.sidebar.text_area(
        "Paste your data here:",
        value="",
        height=200,
        placeholder="Age\t70\nHome Value Today ($)\t1100000\nHome Value Growth (%)\t4.0\n..."
    )
    
    if st.sidebar.button("Import Data", type="primary"):
        if pasted_data.strip():
            success, message, count = import_data(pasted_data)
            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)
        else:
            st.sidebar.warning("Please paste data before importing.")
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Tip:** Imported values populate the inputs below. You can edit them at any time.")

st.sidebar.header("Key Assumptions")

# Get default values from session state (imported) or use defaults
start_age = st.sidebar.number_input(
    "Age", 
    min_value=50, 
    max_value=95, 
    value=int(st.session_state.get('imported_start_age', 70))
)
end_age = 95

st.sidebar.subheader("Home (Owned Outright)")
home_value_now = st.sidebar.number_input(
    "Home Value Today ($)", 
    value=int(st.session_state.get('imported_home_value_now', 1_100_000)), 
    step=50_000
)
# Sliders need percentage values (0-100), but we store as 0-100 in session state for sliders
home_growth_slider_value = st.session_state.get('imported_home_growth', 4.0)
home_growth = st.sidebar.slider("Home Value Growth (%)", 0.0, 8.0, float(home_growth_slider_value)) / 100

tax_deductions = st.sidebar.number_input(
    "Cost Basis + Improvements + 121 Deduction ($)",
    value=float(st.session_state.get('imported_tax_deductions', 300_000.0)),
    step=25_000.0
)

sell_home_years = st.sidebar.number_input(
    "Sell Home In (Years)", 
    min_value=0, 
    max_value=40, 
    value=int(st.session_state.get('imported_sell_home_years', 5))
)
sale_cost_pct_slider_value = st.session_state.get('imported_sale_cost_pct', 6.0)
sale_cost_pct = st.sidebar.slider("Sale Cost (%)", 0.0, 10.0, float(sale_cost_pct_slider_value)) / 100

st.sidebar.subheader("Mortgage")
mortgage_balance = st.sidebar.number_input(
    "Existing Mortgage Balance ($)",
    value=int(st.session_state.get('imported_mortgage_balance', 420_000)),
    step=10_000
)
mortgage_term = st.sidebar.number_input(
    "Remaining Term (yrs)",
    min_value=0,
    max_value=30,
    value=int(st.session_state.get('imported_mortgage_term', 11))
)
mortgage_rate_slider_value = st.session_state.get('imported_mortgage_rate', 2.40)
mortgage_rate = st.sidebar.slider("Existing Mortgage Rate (%)", 0.0, 10.0, float(mortgage_rate_slider_value)) / 100
mortgage_interest_cap = st.sidebar.number_input(
    "Cap on Mortgage Interest ($)",
    value=int(st.session_state.get('imported_mortgage_interest_cap', 750_000)),
    step=50_000
)
balloon_payment = st.sidebar.number_input(
    "Balloon Payment ($)",
    value=int(st.session_state.get('imported_balloon_payment', 0)),
    step=10_000
)

st.sidebar.subheader("Income (Annual)")
ssn_income = st.sidebar.number_input(
    "SSN ($)", 
    value=int(st.session_state.get('imported_ssn_income', 15_600)), 
    step=500
)
pension_income = st.sidebar.number_input(
    "Pension ($)", 
    value=int(st.session_state.get('imported_pension_income', 27_600)), 
    step=500
)
employment_income = st.sidebar.number_input(
    "Employment ($)", 
    value=int(st.session_state.get('imported_employment_income', 0)), 
    step=1_000
)

st.sidebar.subheader("Investments")
cash_start = st.sidebar.number_input(
    "Cash / Money Market ($)", 
    value=int(st.session_state.get('imported_cash_start', 145_000)), 
    step=5_000
)
ira_start = st.sidebar.number_input(
    "IRA / Stocks ($)", 
    value=int(st.session_state.get('imported_ira_start', 1_200_000)), 
    step=25_000
)

st.sidebar.subheader("Living Expenses")

self_years = st.sidebar.number_input(
    "Self-Sufficient (years)", 
    value=int(st.session_state.get('imported_self_years', 2))
)
self_cost = st.sidebar.number_input(
    "Self-Sufficient Annual Cost ($)", 
    value=int(st.session_state.get('imported_self_cost', 37_812)), 
    step=2_000
)

ind_years = st.sidebar.number_input(
    "Independent Living starts in (years)", 
    value=int(st.session_state.get('imported_ind_years', 2))
)
ind_cost = st.sidebar.number_input(
    "Independent Living Annual Cost ($)", 
    value=int(st.session_state.get('imported_ind_cost', 108_000)), 
    step=2_000
)

assist_years = st.sidebar.number_input(
    "Assisted Living starts in (years)", 
    value=int(st.session_state.get('imported_assist_years', 10))
)
assist_cost = st.sidebar.number_input(
    "Assisted Living Annual Cost ($)", 
    value=int(st.session_state.get('imported_assist_cost', 114_000)), 
    step=2_000
)

memory_years = st.sidebar.number_input(
    "Memory Care starts in (years)", 
    value=int(st.session_state.get('imported_memory_years', 20))
)
memory_cost = st.sidebar.number_input(
    "Memory Care Annual Cost ($)", 
    value=int(st.session_state.get('imported_memory_cost', 120_000)), 
    step=5_000
)

st.sidebar.subheader("Taxes & Assumptions")
avg_tax_rate_slider_value = st.session_state.get('imported_avg_tax_rate', 30.0)
avg_tax_rate = st.sidebar.slider("Average Tax Rate (%)", 0.0, 40.0, float(avg_tax_rate_slider_value)) / 100
cap_gains_rate_slider_value = st.session_state.get('imported_cap_gains_rate', 25.0)
cap_gains_rate = st.sidebar.slider("Capital Gains Tax (%)", 0.0, 40.0, float(cap_gains_rate_slider_value)) / 100

living_infl_slider_value = st.session_state.get('imported_living_infl', 3.0)
living_infl = st.sidebar.slider("Living Inflation (%)", 0.0, 6.0, float(living_infl_slider_value)) / 100
care_infl_slider_value = st.session_state.get('imported_care_infl', 4.0)
care_infl = st.sidebar.slider("Care Level Inflation (%)", 0.0, 10.0, float(care_infl_slider_value)) / 100
stock_growth_slider_value = st.session_state.get('imported_stock_growth', 7.0)
stock_growth = st.sidebar.slider("Stocks / IRA Growth (%)", 0.0, 10.0, float(stock_growth_slider_value)) / 100
cash_growth_slider_value = st.session_state.get('imported_cash_growth', 4.5)
cash_growth = st.sidebar.slider("Money Market Growth (%)", 0.0, 6.0, float(cash_growth_slider_value)) / 100

st.sidebar.subheader("Chart Appearance")
show_background = st.sidebar.checkbox("Show Background Image", True)
image_opacity = st.sidebar.slider("Background Image Opacity", 0.30, 1.00, 1.00, 0.05)

# =========================
# PROJECTION
# =========================
ages = np.arange(start_age, end_age + 1)

# Initialize accounts
money_market = cash_start
money_market_cost_basis = cash_start  # All contributions already taxed
money_market_tax_deferred = 0  # Accumulated untaxed growth
money_market_prev_value = cash_start  # Track previous year value for growth calculation

brokerage = 0
brokerage_cost_basis = 0
brokerage_tax_deferred = 0
brokerage_prev_value = 0

ira = ira_start
home_value = home_value_now
mortgage_balance_current = mortgage_balance
mortgage_remaining_months = mortgage_term * 12 if mortgage_term > 0 else 0

# Calculate monthly mortgage payment if mortgage exists
if mortgage_balance_current > 0 and mortgage_term > 0:
    monthly_mortgage_payment = calculate_monthly_payment(mortgage_balance_current, mortgage_rate, mortgage_term)
    monthly_mortgage_rate = mortgage_rate / 12
else:
    monthly_mortgage_payment = 0
    monthly_mortgage_rate = 0

net_worth = []
expenses_series = []
cashflow_series = []
money_market_series = []
brokerage_series = []
ira_series = []
ira_liquid_series = []
home_series = []
mortgage_balance_series = []

# Detailed tracking for calculation verification
mortgage_interest_series = []
mortgage_principal_series = []
mortgage_tax_shield_series = []
money_market_growth_series = []
money_market_cost_basis_series = []
money_market_tax_deferred_series = []
brokerage_growth_series = []
brokerage_cost_basis_series = []
brokerage_tax_deferred_series = []
ira_growth_series = []
mm_withdrawal_series = []
mm_withdrawal_tax_series = []
brokerage_withdrawal_series = []
brokerage_withdrawal_tax_series = []
ira_withdrawal_series = []
home_sale_price_series = []
home_sale_cost_series = []
home_sale_tax_series = []
expense_type_series = []
income_series = []
notes_series = []

# Expense calculation tracking
expense_base_cost_series = []
expense_inflation_rate_series = []
expense_inflation_multiplier_series = []
expense_inflated_base_cost_series = []
expense_mortgage_payment_series = []
expense_mortgage_tax_shield_series = []

income_annual = (ssn_income + pension_income + employment_income) * (1 - avg_tax_rate)

for i, age in enumerate(ages):
    # Grow home until sale
    home_value *= (1 + home_growth)

    # Determine expenses
    # Store base cost before inflation
    if age < start_age + self_years:
        base_cost = self_cost
        # Use living inflation for self-sufficient mode
        inflation_rate = living_infl
    elif age < start_age + assist_years:
        base_cost = ind_cost
        # Use care inflation for care levels (not self-sufficient)
        inflation_rate = care_infl
    elif age < start_age + memory_years:
        base_cost = assist_cost
        # Use care inflation for care levels (not self-sufficient)
        inflation_rate = care_infl
    else:
        base_cost = memory_cost
        # Use care inflation for care levels (not self-sufficient)
        inflation_rate = care_infl

    # Calculate inflation multiplier and inflated base cost
    inflation_multiplier = (1 + inflation_rate) ** i
    inflated_base_cost = base_cost * inflation_multiplier
    expenses = inflated_base_cost

    # Mortgage payments and tax shield
    mortgage_payment_annual = 0
    mortgage_interest_annual = 0
    mortgage_tax_shield = 0
    
    if mortgage_balance_current > 0 and i < sell_home_years:
        # Calculate annual mortgage payment and interest
        if mortgage_remaining_months > 0:
            annual_interest, annual_principal, new_balance = calculate_annual_mortgage_amortization(
                mortgage_balance_current, monthly_mortgage_payment, monthly_mortgage_rate, mortgage_remaining_months
            )
            mortgage_interest_annual = annual_interest
            mortgage_payment_annual = annual_interest + annual_principal
            mortgage_balance_current = new_balance
            mortgage_remaining_months = max(0, mortgage_remaining_months - 12)
            
            # Calculate tax shield (interest payment * (1 - tax_rate))
            mortgage_tax_shield = mortgage_interest_annual * (1 - avg_tax_rate)
            
            # Add mortgage payment to expenses, then subtract tax shield
            expenses += mortgage_payment_annual
            expenses -= mortgage_tax_shield
            
            # If mortgage is paid off, set to 0
            if mortgage_remaining_months <= 0 or mortgage_balance_current <= 0:
                mortgage_balance_current = 0
                mortgage_remaining_months = 0

    # Determine expense type for notes
    if age < start_age + self_years:
        expense_type = "Self-Sufficient"
    elif age < start_age + assist_years:
        expense_type = "Independent Living"
    elif age < start_age + memory_years:
        expense_type = "Assisted Living"
    else:
        expense_type = "Memory Care"
    
    # Investment growth
    # Money Market: Grow, then track tax-deferred amount (untaxed growth)
    # First, ensure that if account is effectively zero, all tracking variables are zeroed
    if money_market < 0.01:
        money_market = 0
        money_market_cost_basis = 0
        money_market_tax_deferred = 0
        money_market_prev_value = 0
        money_market_growth = 0
    else:
        money_market_prev_value = money_market
        money_market_before_growth = money_market
        money_market *= (1 + cash_growth)
        money_market_growth = money_market - money_market_before_growth
        # Track the untaxed growth amount (this is what will be taxed on withdrawal)
        # If negative growth (losses), reduce tax-deferred amount proportionally
        if money_market_growth > 0:
            money_market_tax_deferred += money_market_growth
        elif money_market_growth < 0 and money_market > 0:
            # Losses reduce tax-deferred proportionally
            loss_ratio = abs(money_market_growth) / money_market_prev_value if money_market_prev_value > 0 else 0
            money_market_tax_deferred = max(0, money_market_tax_deferred * (1 - loss_ratio))
        # Ensure money_market didn't become zero due to negative growth (shouldn't happen, but safeguard)
        if money_market < 0.01:
            money_market = 0
            money_market_cost_basis = 0
            money_market_tax_deferred = 0
            money_market_prev_value = 0
            money_market_growth = 0
    
    # Brokerage: Grow, then track tax-deferred amount (if exists)
    # First, ensure that if account is effectively zero, all tracking variables are zeroed
    if brokerage < 0.01:
        brokerage = 0
        brokerage_cost_basis = 0
        brokerage_tax_deferred = 0
        brokerage_prev_value = 0
        brokerage_growth = 0
    else:
        brokerage_before_growth = brokerage
        brokerage_prev_value = brokerage
        brokerage *= (1 + stock_growth)
        brokerage_growth = brokerage - brokerage_prev_value
        # Track the untaxed growth amount (this is what will be taxed on withdrawal)
        if brokerage_growth > 0:
            brokerage_tax_deferred += brokerage_growth
        elif brokerage_growth < 0 and brokerage > 0:
            # Losses reduce tax-deferred proportionally
            loss_ratio = abs(brokerage_growth) / brokerage_prev_value if brokerage_prev_value > 0 else 0
            brokerage_tax_deferred = max(0, brokerage_tax_deferred * (1 - loss_ratio))
        # Ensure brokerage didn't become zero due to negative growth (shouldn't happen, but safeguard)
        if brokerage < 0.01:
            brokerage = 0
            brokerage_cost_basis = 0
            brokerage_tax_deferred = 0
            brokerage_prev_value = 0
            brokerage_growth = 0
    
    # IRA: Grow (tax calculation handled in liquid value)
    ira_before_growth = ira
    ira *= (1 + stock_growth)
    ira_growth = ira - ira_before_growth

    # Calculate liquid home value (net proceeds after sale costs, taxes, and mortgage payoff)
    # This represents what you'd actually get if you sold the home today
    sale_price = home_value
    sale_cost = sale_price * sale_cost_pct
    taxable_gain = max(sale_price - sale_cost - tax_deductions, 0)
    home_tax = taxable_gain * cap_gains_rate
    liquid_home_value = sale_price - sale_cost - home_tax
    
    # Subtract remaining mortgage principal balance from liquid home value
    # This represents the net proceeds after paying off the mortgage
    if mortgage_balance_current > 0:
        liquid_home_value -= mortgage_balance_current
        liquid_home_value = max(0, liquid_home_value)  # Ensure non-negative

    # Home sale (actual transaction)
    home_sale_this_year = False
    if i == sell_home_years:
        home_sale_this_year = True
        # Pay off mortgage when home is sold
        if mortgage_balance_current > 0:
            mortgage_balance_current = 0
            mortgage_remaining_months = 0
        
        # Move home sale proceeds to brokerage account
        brokerage += liquid_home_value
        brokerage_cost_basis = liquid_home_value  # Already taxed contribution
        brokerage_tax_deferred = 0  # Start fresh with new contribution
        brokerage_prev_value = brokerage  # Initialize for growth tracking
        
        home_value = 0
        liquid_home_value = 0

    # Cash flow
    cash_flow = income_annual - expenses
    
    # Initialize withdrawal tracking for this year
    mm_withdrawal = 0
    mm_withdrawal_tax = 0
    brokerage_withdrawal = 0
    brokerage_withdrawal_tax = 0
    ira_withdrawal = 0

    if cash_flow >= 0:
        # Surplus goes to money market
        money_market += cash_flow
        money_market_cost_basis += cash_flow  # New contributions are already taxed
    else:
        deficit = -cash_flow
        
        # Withdrawal order: Money Market → Brokerage → IRA
        
        # 1. Withdraw from Money Market
        # Need to withdraw enough to cover both deficit and tax on withdrawal
        # Formula: net_available = withdrawal * (1 - (tax_deferred/account) * tax_rate)
        # So: withdrawal = net_available / (1 - (tax_deferred/account) * tax_rate)
        if deficit > 0 and money_market > 0:
            # Calculate effective tax rate on withdrawals
            tax_rate_on_withdrawal = (money_market_tax_deferred / money_market * cap_gains_rate) if money_market > 0 else 0
            # Calculate gross withdrawal needed to get net amount (deficit)
            if tax_rate_on_withdrawal < 1:
                gross_needed = deficit / (1 - tax_rate_on_withdrawal)
            else:
                gross_needed = deficit
            take_money_market = min(money_market, gross_needed)
            
            if take_money_market > 0:
                withdrawal_pct = take_money_market / money_market
                untaxed_portion = withdrawal_pct * money_market_tax_deferred
                tax_owed_mm = untaxed_portion * cap_gains_rate
                net_available = take_money_market - tax_owed_mm
                
                # Track withdrawals
                mm_withdrawal = take_money_market
                mm_withdrawal_tax = tax_owed_mm
                
                # Reduce account value
                money_market -= take_money_market
                money_market = max(0, money_market)  # Ensure money_market can't go negative
                
                # Check if money market account is depleted BEFORE doing pro-rata calculations
                # This prevents floating-point precision issues
                if money_market < 0.01:  # Handle floating-point precision - account is effectively depleted
                    # Explicitly zero everything when depleted
                    money_market = 0
                    money_market_cost_basis = 0
                    money_market_tax_deferred = 0
                    money_market_prev_value = 0
                else:
                    # Only do pro-rata reduction if account is not depleted
                    money_market_cost_basis *= (1 - withdrawal_pct)
                    money_market_tax_deferred *= (1 - withdrawal_pct)
                    # Update previous value for next year's growth calculation
                    money_market_prev_value = money_market
                
                # Reduce deficit by net amount available
                deficit -= net_available
        
        # 2. Withdraw from Brokerage
        if deficit > 0 and brokerage > 0:
            # Calculate effective tax rate on withdrawals
            tax_rate_on_withdrawal = (brokerage_tax_deferred / brokerage * cap_gains_rate) if brokerage > 0 else 0
            # Calculate gross withdrawal needed to get net amount (deficit)
            if tax_rate_on_withdrawal < 1:
                gross_needed = deficit / (1 - tax_rate_on_withdrawal)
            else:
                gross_needed = deficit
            take_brokerage = min(brokerage, gross_needed)
            
            if take_brokerage > 0:
                withdrawal_pct = take_brokerage / brokerage
                untaxed_portion = withdrawal_pct * brokerage_tax_deferred
                tax_owed_brokerage = untaxed_portion * cap_gains_rate
                net_available = take_brokerage - tax_owed_brokerage
                
                # Track withdrawals
                brokerage_withdrawal = take_brokerage
                brokerage_withdrawal_tax = tax_owed_brokerage
                
                # Reduce account value
                brokerage -= take_brokerage
                brokerage = max(0, brokerage)  # Ensure brokerage can't go negative
                
                # Check if brokerage account is depleted BEFORE doing pro-rata calculations
                # This prevents floating-point precision issues
                if brokerage < 0.01:  # Handle floating-point precision - account is effectively depleted
                    # Explicitly zero everything when depleted
                    brokerage = 0
                    brokerage_cost_basis = 0
                    brokerage_tax_deferred = 0
                    brokerage_prev_value = 0
                else:
                    # Only do pro-rata reduction if account is not depleted
                    brokerage_cost_basis *= (1 - withdrawal_pct)
                    brokerage_tax_deferred *= (1 - withdrawal_pct)
                    # Update previous value for next year's growth calculation
                    brokerage_prev_value = brokerage
                
                # Reduce deficit by net amount available
                deficit -= net_available
        
        # 3. Withdraw from IRA (no additional tax, already accounted in liquid value)
        if deficit > 0:
            ira_withdrawal = deficit
            ira -= deficit
            ira = max(0, ira)  # Ensure non-negative

    # Calculate liquid values for net worth
    ira_liquid = ira * (1 - cap_gains_rate)  # IRA is fully untaxed
    # Money market and brokerage are already after withdrawal taxes, use gross value
    
    total_assets = money_market + brokerage + ira_liquid + liquid_home_value
    
    # Build notes explaining calculations
    notes = []
    # Determine which inflation rate was used based on expense type
    current_infl_rate = living_infl if expense_type == "Self-Sufficient" else care_infl
    notes.append(f"Expenses: {expense_type} (inflated {current_infl_rate*100:.1f}%)")
    if mortgage_interest_annual > 0:
        notes.append(f"Mortgage: ${mortgage_interest_annual:,.0f} interest, ${mortgage_payment_annual - mortgage_interest_annual:,.0f} principal, ${mortgage_tax_shield:,.0f} tax shield")
    if money_market_growth != 0:
        notes.append(f"MM growth: ${money_market_growth:,.0f} ({cash_growth*100:.1f}%)")
    if brokerage_growth != 0:
        notes.append(f"Brokerage growth: ${brokerage_growth:,.0f} ({stock_growth*100:.1f}%)")
    if ira_growth != 0:
        notes.append(f"IRA growth: ${ira_growth:,.0f} ({stock_growth*100:.1f}%)")
    if home_sale_this_year:
        notes.append(f"HOME SALE: ${sale_price:,.0f} sale, ${sale_cost:,.0f} costs, ${home_tax:,.0f} tax, ${liquid_home_value:,.0f} net → brokerage")
    if cash_flow >= 0:
        notes.append(f"Surplus: ${cash_flow:,.0f} → money market")
    else:
        if mm_withdrawal > 0:
            notes.append(f"MM withdrawal: ${mm_withdrawal:,.0f} gross, ${mm_withdrawal_tax:,.0f} tax, ${mm_withdrawal - mm_withdrawal_tax:,.0f} net")
        if brokerage_withdrawal > 0:
            notes.append(f"Brokerage withdrawal: ${brokerage_withdrawal:,.0f} gross, ${brokerage_withdrawal_tax:,.0f} tax, ${brokerage_withdrawal - brokerage_withdrawal_tax:,.0f} net")
        if ira_withdrawal > 0:
            notes.append(f"IRA withdrawal: ${ira_withdrawal:,.0f} (tax already in liquid value)")
    notes_str = " | ".join(notes)

    net_worth.append(total_assets)
    expenses_series.append(expenses)
    cashflow_series.append(cash_flow)
    money_market_series.append(money_market)
    brokerage_series.append(brokerage)
    ira_series.append(ira)
    ira_liquid_series.append(ira_liquid)
    home_series.append(liquid_home_value)
    mortgage_balance_series.append(mortgage_balance_current)
    
    # Append detailed tracking
    mortgage_interest_series.append(mortgage_interest_annual)
    mortgage_principal_series.append(mortgage_payment_annual - mortgage_interest_annual if mortgage_payment_annual > 0 else 0)
    mortgage_tax_shield_series.append(mortgage_tax_shield)
    money_market_growth_series.append(money_market_growth)
    money_market_cost_basis_series.append(money_market_cost_basis)
    money_market_tax_deferred_series.append(money_market_tax_deferred)
    brokerage_growth_series.append(brokerage_growth)
    brokerage_cost_basis_series.append(brokerage_cost_basis)
    brokerage_tax_deferred_series.append(brokerage_tax_deferred)
    ira_growth_series.append(ira_growth)
    mm_withdrawal_series.append(mm_withdrawal)
    mm_withdrawal_tax_series.append(mm_withdrawal_tax)
    brokerage_withdrawal_series.append(brokerage_withdrawal)
    brokerage_withdrawal_tax_series.append(brokerage_withdrawal_tax)
    ira_withdrawal_series.append(ira_withdrawal)
    # Track home sale details (only populated when sale occurs, but calculation happens every year)
    home_sale_price_series.append(sale_price if home_sale_this_year else 0)
    home_sale_cost_series.append(sale_cost if home_sale_this_year else 0)
    home_sale_tax_series.append(home_tax if home_sale_this_year else 0)
    expense_type_series.append(expense_type)
    income_series.append(income_annual)
    notes_series.append(notes_str)
    
    # Append expense calculation tracking
    expense_base_cost_series.append(base_cost)
    expense_inflation_rate_series.append(inflation_rate * 100)  # Store as percentage
    expense_inflation_multiplier_series.append(inflation_multiplier)
    expense_inflated_base_cost_series.append(inflated_base_cost)
    expense_mortgage_payment_series.append(mortgage_payment_annual)
    expense_mortgage_tax_shield_series.append(mortgage_tax_shield)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth,
    "Expenses": expenses_series,
    "Cash Flow": cashflow_series,
    "Money Market": money_market_series,
    "Brokerage": brokerage_series,
    "IRA": ira_series,
    "IRA Liquid": ira_liquid_series,
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
    ("Peak Net Worth", peak_idx, "#f1c40f"),
    ("Reassessment Phase", decline_idx, "#e67e22"),
]


# =========================
# HEADER
# =========================
header_spacer, header_content = st.columns([0.75, 9.25])

with header_content:
    st.markdown(
        """
        <div style="text-align:center;">
            <h1>Retirement Financial Overview</h1>
            <p style="font-size:20px; color:#666;">A simplified view of income, expenses, and net worth over time</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================
# PHASE HEADERS
# =========================
st.markdown("<br>", unsafe_allow_html=True)
spacer, phase_col1, phase_col2, phase_col3 = st.columns([0.75, 3, 3, 3])

with phase_col1:
    st.markdown(
        """
        <div style="text-align:center; background-color:#90EE90; padding:15px; border-radius:10px;">
            <h2 style="text-align:center; color:#2c3e50;">Phase 1</h2>
            <p style="text-align:center; font-size:18px; color:#2c3e50; margin-top:10px;">💰 Surplus</p>
            <p style="text-align:center; font-size:16px; color:#2c3e50; margin-top:5px;">Income > Costs</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with phase_col2:
    st.markdown(
        """
        <div style="text-align:center; background-color:#FFA500; padding:15px; border-radius:10px;">
            <h2 style="text-align:center; color:#2c3e50;">Phase 2</h2>
            <p style="text-align:center; font-size:18px; color:#2c3e50; margin-top:10px;">Living Well On Savings</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with phase_col3:
    st.markdown(
        """
        <div style="text-align:center; background-color:#87CEEB; padding:15px; border-radius:10px;">
            <h2 style="text-align:center; color:#2c3e50;">Phase 3</h2>
            <p style="text-align:center; font-size:18px; color:#2c3e50; margin-top:10px;">Savings Deplete</p>
            <p style="text-align:center; font-size:16px; color:#2c3e50; margin-top:5px;">Additional support may be needed</p>
        </div>
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
        mode="markers",
        marker=dict(size=20, color=color, line=dict(color="white", width=3)),
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
# Add annotations for metrics at milestone points
annotations = [
    # Starting Net Worth at Start milestone
    dict(
        x=df.loc[start_idx, "Age"],
        y=df.loc[start_idx, "Net Worth"],
        text=f"<b>Starting Net Worth</b><br>${df.iloc[0]['Net Worth']:,.0f}",
        showarrow=True,
        arrowhead=2,
        arrowsize=2,
        arrowwidth=3,
        arrowcolor="white",
        ax=0,
        ay=-50,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#2c3e50",
        borderwidth=3,
        borderpad=12,
        font=dict(size=20, color="#2c3e50"),
        yref="y2"
    ),
    # Peak Net Worth at Peak milestone
    dict(
        x=df.loc[peak_idx, "Age"],
        y=df.loc[peak_idx, "Net Worth"],
        text=f"<b>Peak Net Worth</b><br>${df['Net Worth'].max():,.0f}",
        showarrow=True,
        arrowhead=2,
        arrowsize=2,
        arrowwidth=3,
        arrowcolor="white",
        ax=0,
        ay=-50,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#2c3e50",
        borderwidth=3,
        borderpad=12,
        font=dict(size=20, color="#2c3e50"),
        yref="y2"
    ),
    # Ending Net Worth at end of data
    dict(
        x=df.loc[df.index[-1], "Age"],
        y=df.loc[df.index[-1], "Net Worth"],
        text=f"<b>Ending Net Worth</b><br>${df.iloc[-1]['Net Worth']:,.0f}",
        showarrow=True,
        arrowhead=2,
        arrowsize=2,
        arrowwidth=3,
        arrowcolor="white",
        ax=0,
        ay=-50,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#2c3e50",
        borderwidth=3,
        borderpad=12,
        font=dict(size=20, color="#2c3e50"),
        yref="y2"
    )
]

fig.update_layout(
    images=layout_images,
    height=720,
    annotations=annotations,
    legend=dict(
        orientation="h",
        y=-0.15,
        font=dict(size=18)
    ),
    xaxis=dict(
        title=dict(text="Age", font=dict(size=30, color="black")),
        tickfont=dict(size=24, color="black"),
        tickmode="linear",
        dtick=5,
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="black",
        linewidth=2,
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
        title=dict(text="Net Worth ($)", font=dict(size=30, color="black")),
        tickfont=dict(size=24, color="black"),
        overlaying="y",
        side="left",
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="black",
        linewidth=2,
        fixedrange=True
    ),
    plot_bgcolor="rgba(255,255,255,0.30)",
    margin=dict(t=50, b=100, l=70, r=70)
)

st.plotly_chart(fig, use_container_width=True)


# =========================
fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=df["Age"], y=df["Money Market"], name="Money Market"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["Brokerage"], name="Brokerage"))
fig2.add_trace(go.Scatter(x=df["Age"], y=df["IRA"], name="IRA (Gross)"))
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
        "Money Market",
        "Brokerage",
        "IRA",
        "IRA Liquid",
        "Home Value"
    ]

    for col in currency_cols:
        display_df[col] = display_df[col].map(lambda x: f"${x:,.0f}")

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )

# =========================
# DETAILED CALCULATION BREAKDOWN (COLLAPSIBLE)
# =========================
with st.expander("Show Detailed Calculation Breakdown"):
    st.markdown("### Calculation Details by Year")
    st.markdown("*This table shows all intermediate calculations and formulas used for verification.*")
    
    detailed_df = pd.DataFrame({
        "Age": ages,
        "Expense Type": expense_type_series,
        "Income (After Tax)": income_series,
        "Expenses": expenses_series,
        "Cash Flow": cashflow_series,
        "Mortgage Interest": mortgage_interest_series,
        "Mortgage Principal": mortgage_principal_series,
        "Mortgage Tax Shield": mortgage_tax_shield_series,
        "MM Growth": money_market_growth_series,
        "MM Cost Basis": money_market_cost_basis_series,
        "MM Tax Deferred": money_market_tax_deferred_series,
        "MM Withdrawal": mm_withdrawal_series,
        "MM Withdrawal Tax": mm_withdrawal_tax_series,
        "Brokerage Growth": brokerage_growth_series,
        "Brokerage Cost Basis": brokerage_cost_basis_series,
        "Brokerage Tax Deferred": brokerage_tax_deferred_series,
        "Brokerage Withdrawal": brokerage_withdrawal_series,
        "Brokerage Withdrawal Tax": brokerage_withdrawal_tax_series,
        "IRA Growth": ira_growth_series,
        "IRA Withdrawal": ira_withdrawal_series,
        "Home Sale Price": home_sale_price_series,
        "Home Sale Cost": home_sale_cost_series,
        "Home Sale Tax": home_sale_tax_series,
        "Notes": notes_series
    })
    
    # Format currency columns
    currency_cols_detailed = [
        "Income (After Tax)",
        "Expenses",
        "Cash Flow",
        "Mortgage Interest",
        "Mortgage Principal",
        "Mortgage Tax Shield",
        "MM Growth",
        "MM Cost Basis",
        "MM Tax Deferred",
        "MM Withdrawal",
        "MM Withdrawal Tax",
        "Brokerage Growth",
        "Brokerage Cost Basis",
        "Brokerage Tax Deferred",
        "Brokerage Withdrawal",
        "Brokerage Withdrawal Tax",
        "IRA Growth",
        "IRA Withdrawal",
        "Home Sale Price",
        "Home Sale Cost",
        "Home Sale Tax"
    ]
    
    for col in currency_cols_detailed:
        detailed_df[col] = detailed_df[col].map(lambda x: f"${x:,.0f}" if x != 0 else "$0")
    
    st.dataframe(
        detailed_df,
        use_container_width=True,
        height=600
    )
    
    st.markdown("### Calculation Formulas")
    st.markdown("""
    **Net Worth Calculation:**
    - Net Worth = Money Market + Brokerage + IRA Liquid + Home Value (Liquid)
    - IRA Liquid = IRA × (1 - Capital Gains Rate)
    - Home Value (Liquid) = Sale Price - Sale Cost - Tax - Mortgage Balance
    
    **Income:**
    - Income (After Tax) = (SSN + Pension + Employment) × (1 - Average Tax Rate)
    
    **Expenses:**
    - Expenses = Base Cost × (1 + Living Inflation)^Years
    - Expenses with Mortgage = Base Expenses + Mortgage Payment - Mortgage Tax Shield
    - Mortgage Tax Shield = Mortgage Interest × (1 - Average Tax Rate)
    
    **Investment Growth:**
    - Money Market: Value × (1 + Cash Growth Rate)
    - Brokerage: Value × (1 + Stock Growth Rate)
    - IRA: Value × (1 + Stock Growth Rate)
    
    **Tax-Deferred Tracking:**
    - Growth amounts are tracked separately as "tax-deferred"
    - Withdrawals are taxed on the proportion of untaxed growth
    - Tax on Withdrawal = (Withdrawal × Tax-Deferred/Total Value) × Capital Gains Rate
    
    **Withdrawal Order (when cash flow negative):**
    1. Money Market (with capital gains tax on growth portion)
    2. Brokerage (with capital gains tax on growth portion)
    3. IRA (tax already accounted in liquid value calculation)
    
    **Home Sale (at specified year):**
    - Sale Price = Home Value (after growth)
    - Sale Cost = Sale Price × Sale Cost %
    - Taxable Gain = max(Sale Price - Sale Cost - Tax Deductions, 0)
    - Tax = Taxable Gain × Capital Gains Rate
    - Net Proceeds = Sale Price - Sale Cost - Tax - Mortgage Balance
    - Proceeds moved to Brokerage account
    """)

# =========================
# EXPENSE CALCULATIONS (COLLAPSIBLE)
# =========================
with st.expander("Show Expense Calculations"):
    st.markdown("### Expense Calculation Details by Year")
    st.markdown("*This table shows expense calculations broken down by expense type, inflation adjustments, and mortgage impacts for each year.*")
    
    expense_df = pd.DataFrame({
        "Age": ages,
        "Expense Type": expense_type_series,
        "Base Annual Cost": expense_base_cost_series,
        "Years Since Start": list(range(len(ages))),
        "Inflation Rate (%)": expense_inflation_rate_series,
        "Inflation Multiplier": expense_inflation_multiplier_series,
        "Inflated Base Cost": expense_inflated_base_cost_series,
        "Mortgage Payment": expense_mortgage_payment_series,
        "Mortgage Tax Shield": expense_mortgage_tax_shield_series,
        "Total Expenses": expenses_series
    })
    
    # Format currency columns
    expense_currency_cols = [
        "Base Annual Cost",
        "Inflated Base Cost",
        "Mortgage Payment",
        "Mortgage Tax Shield",
        "Total Expenses"
    ]
    
    for col in expense_currency_cols:
        expense_df[col] = expense_df[col].map(lambda x: f"${x:,.0f}" if x != 0 else "$0")
    
    # Format percentage column
    expense_df["Inflation Rate (%)"] = expense_df["Inflation Rate (%)"].map(lambda x: f"{x:.2f}%")
    
    # Format inflation multiplier to show as multiplier (e.g., 1.0300)
    expense_df["Inflation Multiplier"] = expense_df["Inflation Multiplier"].map(lambda x: f"{x:.4f}")
    
    st.dataframe(
        expense_df,
        use_container_width=True,
        height=600
    )
    
    st.markdown("### Expense Calculation Formulas")
    st.markdown("""
    **Base Annual Cost:**
    - Determined by expense type based on age and phase transitions
    - Self-Sufficient: Used for years 0 to self_years
    - Independent Living: Used from self_years to assist_years
    - Assisted Living: Used from assist_years to memory_years
    - Memory Care: Used from memory_years onwards
    
    **Inflation Adjustment:**
    - Inflation Multiplier = (1 + Living Inflation Rate)^Years Since Start
    - Inflated Base Cost = Base Annual Cost × Inflation Multiplier
    
    **Mortgage Impact (if applicable):**
    - Mortgage Payment = Interest Payment + Principal Payment
    - Mortgage Tax Shield = Mortgage Interest × (1 - Average Tax Rate)
    - Net Mortgage Cost = Mortgage Payment - Mortgage Tax Shield
    
    **Total Expenses:**
    - Total Expenses = Inflated Base Cost + Mortgage Payment - Mortgage Tax Shield
    - This represents the net annual expense after accounting for mortgage payments and tax benefits
    """)
