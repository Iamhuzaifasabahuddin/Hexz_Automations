import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Investment Portfolio Analysis",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


def format_pkr(amount):
    if amount >= 10000000:
        return f'PKR {amount / 10000000:.2f} Cr'
    elif amount >= 100000:
        return f'PKR {amount / 100000:.2f} Lac'
    else:
        return f'PKR {amount:,.0f}'


def calculate_sip(monthly_investment, annual_return, years):
    monthly_rate = annual_return / 12 / 100
    months = years * 12

    if monthly_rate == 0:
        return monthly_investment * months

    return monthly_investment * ((1 + monthly_rate) ** months - 1) / monthly_rate * (1 + monthly_rate)


def calculate_alternating_sip(monthly_investment, equity_return, balanced_return, stock_return, years):
    """
    Calculate SIP with alternating strategy:
    - Odd months (1,3,5...): Invest in mutual funds (70% equity, 30% balanced)
    - Even months (2,4,6...): Invest in stocks
    """
    months = years * 12
    monthly_equity_rate = equity_return / 12 / 100
    monthly_balanced_rate = balanced_return / 12 / 100
    monthly_stock_rate = stock_return / 12 / 100
    
    total_value = 0
    
    for month in range(1, months + 1):
        months_remaining = months - month + 1
        
        if month % 2 == 1:  # Odd month - Mutual Funds (70% equity, 30% balanced)
            equity_investment = monthly_investment * 0.70
            balanced_investment = monthly_investment * 0.30
            
            if monthly_equity_rate == 0:
                equity_value = equity_investment
            else:
                equity_value = equity_investment * ((1 + monthly_equity_rate) ** months_remaining)
            
            if monthly_balanced_rate == 0:
                balanced_value = balanced_investment
            else:
                balanced_value = balanced_investment * ((1 + monthly_balanced_rate) ** months_remaining)
            
            total_value += equity_value + balanced_value
            
        else:  # Even month - Stocks (100%)
            if monthly_stock_rate == 0:
                stock_value = monthly_investment
            else:
                stock_value = monthly_investment * ((1 + monthly_stock_rate) ** months_remaining)
            
            total_value += stock_value
    
    return total_value


def calculate_portfolio(allocations, returns, years):
    total = 0
    invested = 0

    for allocation, ret in zip(allocations, returns):
        total += calculate_sip(allocation, ret, years)
        invested += allocation * 12 * years

    return {
        "total": total,
        "invested": invested,
        "gains": total - invested,
        "roi": ((total - invested) / invested) * 100
    }


def calculate_alternating_portfolio(monthly_investment, equity_return, balanced_return, stock_return, years):
    total = calculate_alternating_sip(monthly_investment, equity_return, balanced_return, stock_return, years)
    invested = monthly_investment * 12 * years
    
    return {
        "total": total,
        "invested": invested,
        "gains": total - invested,
        "roi": ((total - invested) / invested) * 100
    }


def calculate_yearly_growth(allocations, returns, max_years):
    return [
        calculate_portfolio(allocations, returns, y)["total"]
        for y in range(1, max_years + 1)
    ]


def calculate_alternating_yearly_growth(monthly_investment, equity_return, balanced_return, stock_return, max_years):
    return [
        calculate_alternating_sip(monthly_investment, equity_return, balanced_return, stock_return, y)
        for y in range(1, max_years + 1)
    ]


def apply_market_scenario(equity, balanced, stocks, scenario):
    if scenario == "Bear":
        return max(equity - 6, 0), max(balanced - 4, 0), max(stocks - 10, 0)
    elif scenario == "Bull":
        return equity + 6, balanced + 4, stocks + 10
    return equity, balanced, stocks


st.markdown("## 💰 Investment Portfolio Analysis")

st.sidebar.header("⚙️ Investment Parameters")

monthly_amount = st.sidebar.number_input(
    "Monthly Investment (PKR)",
    min_value=5000,
    max_value=500000,
    value=20000,
    step=1000
)

years = st.sidebar.slider(
    "Investment Period (Years)",
    min_value=5,
    max_value=35,
    value=15
)

st.sidebar.subheader("📉📈 Market Scenario")
market_scenario = st.sidebar.radio(
    "Select Scenario",
    ["Bear", "Base", "Bull"],
    index=1
)

st.sidebar.subheader("Expected Returns (Base CAGR %)")

base_equity_roi = st.sidebar.slider("Equity", 0.0, 30.0, 16.0, 0.5)
base_balanced_roi = st.sidebar.slider("Balanced", 0.0, 20.0, 11.0, 0.5)
base_stock_roi = st.sidebar.slider("PSX / Stocks", 0.0, 40.0, 18.0, 1.0)

equity_roi, balanced_roi, stock_roi = apply_market_scenario(
    base_equity_roi,
    base_balanced_roi,
    base_stock_roi,
    market_scenario
)

scenario_icon = {"Bear": "🔴", "Base": "🟡", "Bull": "🟢"}

st.info(
    f"{scenario_icon[market_scenario]} **{market_scenario} Market Applied**  \n"
    f"- Equity: {equity_roi:.1f}%  \n"
    f"- Balanced: {balanced_roi:.1f}%  \n"
    f"- PSX/Stocks: {stock_roi:.1f}%"
)

option1_equity = monthly_amount * 0.75
option1_balanced = monthly_amount * 0.25

option2_equity = monthly_amount * 0.5
option2_psx = monthly_amount * 0.5

option3_equity = monthly_amount * 0.5
option3_balanced = monthly_amount * 0.25
option3_stocks = monthly_amount * 0.25

options = [
    {
        "name": "Option 1: Equity Heavy",
        "allocations": [option1_equity, option1_balanced],
        "returns": [equity_roi, balanced_roi],
        "type": "standard"
    },
    {
        "name": "Option 2: Equity + PSX",
        "allocations": [option2_equity, option2_psx],
        "returns": [equity_roi, stock_roi],
        "type": "standard"
    },
    {
        "name": "Option 3: Balanced Mix",
        "allocations": [option3_equity, option3_balanced, option3_stocks],
        "returns": [equity_roi, balanced_roi, stock_roi],
        "type": "standard"
    },
    {
        "name": "Option 4: Alternating Strategy",
        "allocations": None,
        "returns": None,
        "type": "alternating"
    }
]

results = []
for opt in options:
    if opt["type"] == "standard":
        results.append(calculate_portfolio(opt["allocations"], opt["returns"], years))
    else:  # alternating
        results.append(calculate_alternating_portfolio(monthly_amount, equity_roi, balanced_roi, stock_roi, years))

best_index = max(range(len(results)), key=lambda i: results[i]["total"])

st.header("📊 Investment Options Comparison")
cols = st.columns(4)

for i, (col, opt, res) in enumerate(zip(cols, options, results)):
    with col:
        st.subheader(opt["name"] + (" 🏆" if i == best_index else ""))
        
        if opt["type"] == "alternating":
            st.caption("🔄 Odd months: 70% Equity + 30% Balanced  \n📈 Even months: 100% Stocks")
        
        st.metric("Final Value", format_pkr(res["total"]))
        st.metric("Invested", format_pkr(res["invested"]))
        st.metric("Gains", format_pkr(res["gains"]))
        st.metric("ROI", f"{res['roi']:.2f}%")

st.header("📈 Portfolio Growth")

fig = go.Figure()

colors = ["#667eea", "#f6ad55", "#48bb78", "#9f7aea"]

for opt, color in zip(options, colors):
    if opt["type"] == "standard":
        y_values = calculate_yearly_growth(opt["allocations"], opt["returns"], years)
    else:  # alternating
        y_values = calculate_alternating_yearly_growth(monthly_amount, equity_roi, balanced_roi, stock_roi, years)
    
    fig.add_trace(go.Scatter(
        x=list(range(1, years + 1)),
        y=y_values,
        mode="lines",
        name=opt["name"],
        line=dict(width=3, color=color)
    ))

fig.update_layout(
    xaxis_title="Years",
    yaxis_title="Portfolio Value (PKR)",
    hovermode="x unified",
    template="plotly_white",
    height=500
)

st.plotly_chart(fig, width="stretch", key="Testing")

st.header("💵 Final Value Comparison")

fig_bar = go.Figure(go.Bar(
    x=[o["name"] for o in options],
    y=[r["total"] for r in results],
    text=[format_pkr(r["total"]) for r in results],
    textposition="outside",
    marker_color=colors
))

fig_bar.update_layout(
    yaxis_title="PKR",
    template="plotly_white",
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# Alternating Strategy Breakdown
with st.expander("🔍 Option 4: Alternating Strategy Details"):
    st.markdown("""
    ### How it works:
    - **Odd Months (Jan, Mar, May...)**: Invest full amount in Mutual Funds
      - 70% → Equity Fund
      - 30% → Balanced Fund
    - **Even Months (Feb, Apr, Jun...)**: Invest full amount in PSX/Stocks
      - 100% → Direct Stocks
    
    ### Benefits:
    - ✅ Automatic diversification over time
    - ✅ Captures both mutual fund stability and stock market upside
    - ✅ Dollar-cost averaging across asset classes
    - ✅ Reduces timing risk
    """)

st.warning("""
⚠️ **Important Notes**
- Bear/Base/Bull scenarios represent **return uncertainty**, not predictions
- Long-term equity returns are volatile and cyclical
- This tool is for **educational modeling only**
- Consult a licensed financial advisor before investing
""")

st.success("💡 Tip: Switch scenarios to understand downside risk before committing capital.")