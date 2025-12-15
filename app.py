import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Journey", layout="wide")

# =========================
# SIDEBAR INPUTS
# =========================
st.sidebar.header("Your Financial Snapshot")

start_age = st.sidebar.number_input("Current Age", min_value=60, max_value=85, value=75)
end_age = 95

annual_income = st.sidebar.number_input("Annual Income ($)", value=0)
annual_expenses = st.sidebar.number_input("Annual Living Expenses ($)", value=65000)

cash = st.sidebar.number_input("Liquid Cash ($)", value=200000)
investments = st.sidebar.number_input("Investments ($)", value=650000)
home_value = st.sidebar.number_input("Home Value ($)", value=700000)
debt = st.sidebar.number_input("Debt ($)", value=0)

st.sidebar.markdown("---")
growth = st.sidebar.slider("Investment Growth (%)", 2.0, 7.0, 5.0) / 100
inflation = st.sidebar.slider("Expense Inflation (%)", 1.0, 4.0, 2.5) / 100

# =========================
# PROJECTION LOGIC
# =========================
ages = np.arange(start_age, end_age + 1)

assets = cash + investments
expenses = annual_expenses

net_worth = []

for age in ages:
    # cash flow affects assets
    cashflow = annual_income - expenses
    assets = (assets + cashflow) * (1 + growth)

    # total net worth includes home, subtract debt
    net_worth.append(assets + home_value - debt)

    # expenses inflate
    expenses *= (1 + inflation)

df = pd.DataFrame({
    "Age": ages,
    "Net Worth": net_worth
})

# =========================
# MILESTONES
# =========================
peak_idx = df["Net Worth"].idxmax()
peak_age = df.loc[peak_idx, "Age"]
peak_value = df.loc[peak_idx, "Net Worth"]

decline_age = min(peak_age + 7, end_age)
decline_value = df.loc[df["Age"] == decline_age, "Net Worth"].values[0]

milestones = [
    (start_age, df.iloc[0]["Net Worth"], "Start:\nstrong position", "#1f7a63"),
    (peak_age, peak_value, "Peak:\nhighest net worth", "#d4a017"),
    (decline_age, decline_value, "Noticeable\ndecline", "#8f9779"),
    (end_age, df.iloc[-1]["Net Worth"], "Time to\nreassess", "#c2a24d"),
]

# =========================
# HEADER
# =========================
st.markdown(
    """
    <h1 style="text-align:center; margin-bottom:0;">
        Retirement Journey
    </h1>
    <p style="text-align:center; font-size:18px; color:#555; margin-top:5px;">
        A visual path of how your financial life may unfold
    </p>
    """,
    unsafe_allow_html=True
)

# =========================
# JOURNEY GRAPH
# =========================
fig = go.Figure()

# --- Background image INSIDE Plotly ---
fig.update_layout(
    images=[
        dict(
            source="https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91",
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            opacity=0.45,          # <-- KEY CHANGE (less washed out)
            layer="below"
        )
    ]
)

# --- Net worth journey path ---
fig.add_trace(go.Scatter(
    x=df["Age"],
    y=df["Net Worth"],
    mode="lines",
    line=dict(
        color="#4f6f73",
        width=6,
        shape="spline"
    ),
    fill="tozeroy",
    fillcolor="rgba(79,111,115,0.35)",
    hovertemplate="Age %{x}<br>Net Worth: $%{y:,.0f}<extra></extra>"
))

# --- Milestone markers ---
for age, value, label, color in milestones:
    fig.add_trace(go.Scatter(
        x=[age],
        y=[value],
        mode="markers+text",
        marker=dict(
            size=20,
            color=color,
            line=dict(color="white", width=3)
        ),
        text=[label],
        textposition="top center"
    ))

# =========================
# AXIS & LAYOUT STYLING
# =========================
fig.update_layout(
    height=720,
    showlegend=False,
    xaxis=dict(
        tickmode="array",
        tickvals=[75, 80, 90, 95],
        ticktext=["75", "80", "90", "95"],
        showgrid=False,
        zeroline=False
    ),
    yaxis=dict(
        showgrid=False,
        showticklabels=False,
        zeroline=False
    ),
    plot_bgcolor="rgba(255,255,255,0.82)",  # lighter overlay, not grey
    margin=dict(t=30, b=60, l=40, r=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<p style='text-align:center; color:#666;'>Illustrative example for planning purposes only.</p>",
    unsafe_allow_html=True
)
