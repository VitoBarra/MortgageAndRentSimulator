import pandas as pd
import plotly.express as px
import streamlit as st

from mortgage import calculate_monthly_payment, calculate_total_interest
from rental import calculate_monthly_rental_income, calculate_net_rental_income
from scenarios import build_room_scenarios, build_rate_scenarios


st.set_page_config(
    page_title="Mortgage Simulator",
    page_icon="🏠",
    layout="wide",
)


st.title("Mortgage Simulator")

with st.sidebar:
    st.header("Purchase")
    house_price = st.number_input(
        "House price",
        min_value=50_000,
        max_value=500_000,
        value=140_000,
        step=5_000,
        format="%d",
    )
    mortgage_percent = st.slider("Mortgage percentage", 50, 100, 100, 5)
    annual_rate = st.slider("Annual interest rate", 1.0, 8.0, 3.5, 0.1)
    years = st.slider("Mortgage duration", 10, 35, 30, 1)

    st.header("Rental Plan")
    rooms = st.slider("Rented rooms", 1, 6, 3, 1)
    rent_per_room = st.number_input(
        "Rent per room",
        min_value=150,
        max_value=900,
        value=400,
        step=25,
        format="%d",
    )
    occupancy_rate = st.slider("Occupancy rate", 50, 100, 90, 5)
    rental_tax_rate = st.slider("Rental tax rate", 0, 35, 21, 1)

    st.header("Monthly Costs")
    condo_costs = st.number_input("Condo costs", min_value=0, value=80, step=10)
    maintenance = st.number_input("Maintenance reserve", min_value=0, value=80, step=10)
    other_costs = st.number_input("Other costs", min_value=0, value=0, step=10)


mortgage_amount = house_price * mortgage_percent / 100
down_payment = house_price - mortgage_amount
monthly_payment = calculate_monthly_payment(mortgage_amount, annual_rate, years)
total_interest = calculate_total_interest(mortgage_amount, annual_rate, years)

gross_rent = calculate_monthly_rental_income(rooms, rent_per_room, occupancy_rate)
net_rent = calculate_net_rental_income(gross_rent, rental_tax_rate)
monthly_costs = condo_costs + maintenance + other_costs
cashflow_before_costs = net_rent - monthly_payment
cashflow_after_costs = net_rent - monthly_payment - monthly_costs

col1, col2, col3, col4 = st.columns(4)
col1.metric("Mortgage amount", f"€{mortgage_amount:,.0f}")
col2.metric("Monthly payment", f"€{monthly_payment:,.0f}")
col3.metric("Net rental income", f"€{net_rent:,.0f}")
col4.metric("Monthly cashflow", f"€{cashflow_after_costs:,.0f}")

st.divider()

summary_col, chart_col = st.columns([1, 1.4])

with summary_col:
    st.subheader("Scenario Summary")
    summary = pd.DataFrame(
        [
            ("House price", house_price),
            ("Down payment", down_payment),
            ("Mortgage amount", mortgage_amount),
            ("Monthly payment", monthly_payment),
            ("Total interest", total_interest),
            ("Gross rent", gross_rent),
            ("Net rent after tax", net_rent),
            ("Monthly operating costs", monthly_costs),
            ("Cashflow before costs", cashflow_before_costs),
            ("Cashflow after costs", cashflow_after_costs),
        ],
        columns=["Item", "Amount"],
    )
    summary["Amount"] = summary["Amount"].map(lambda value: f"€{value:,.0f}")
    st.dataframe(summary, hide_index=True, use_container_width=True)

with chart_col:
    st.subheader("Rooms Break-even")
    room_scenarios = build_room_scenarios(
        max_rooms=6,
        rent_per_room=rent_per_room,
        occupancy_rate=occupancy_rate,
        rental_tax_rate=rental_tax_rate,
        monthly_payment=monthly_payment,
        monthly_costs=monthly_costs,
    )
    fig = px.bar(
        room_scenarios,
        x="rooms",
        y="cashflow",
        text="cashflow",
        color="cashflow",
        color_continuous_scale=["#b91c1c", "#f59e0b", "#15803d"],
        labels={"rooms": "Rooms", "cashflow": "Monthly cashflow"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#111827")
    fig.update_traces(texttemplate="€%{text:.0f}", textposition="outside")
    fig.update_layout(showlegend=False, yaxis_tickprefix="€")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Interest Rate Sensitivity")
rate_scenarios = build_rate_scenarios(
    mortgage_amount=mortgage_amount,
    years=years,
    rates=[round(rate / 10, 1) for rate in range(20, 61, 5)],
    net_rent=net_rent,
    monthly_costs=monthly_costs,
)

rate_fig = px.line(
    rate_scenarios,
    x="annual_rate",
    y=["monthly_payment", "cashflow"],
    markers=True,
    labels={
        "annual_rate": "Annual rate (%)",
        "value": "Monthly amount",
        "variable": "Metric",
    },
)
rate_fig.update_layout(yaxis_tickprefix="€")
st.plotly_chart(rate_fig, use_container_width=True)

st.subheader("Room Scenario Table")
st.dataframe(
    room_scenarios.assign(
        gross_rent=lambda frame: frame["gross_rent"].round(0),
        net_rent=lambda frame: frame["net_rent"].round(0),
        cashflow=lambda frame: frame["cashflow"].round(0),
    ),
    hide_index=True,
    use_container_width=True,
)
