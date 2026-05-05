import pandas as pd
import plotly.express as px
import streamlit as st

from mortgage import (
    build_standard_schedule,
    calculate_monthly_payment,
    calculate_total_interest,
    simulate_combined_repayment,
)
from rental import calculate_monthly_rental_income, calculate_net_rental_income
from scenarios import build_room_scenarios, build_rate_scenarios


def coerce_positive_float(value: object) -> float:
    if pd.isna(value):
        return 0
    return max(float(value), 0)


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

    st.header("Initial Costs")
    notary_cost = st.number_input("Notary", min_value=0, value=3_000, step=250)
    istruttoria_cost = st.number_input("Istruttoria", min_value=0, value=800, step=100)
    appraisal_cost = st.number_input("Perizia", min_value=0, value=300, step=50)
    agency_cost = st.number_input("Agency", min_value=0, value=0, step=250)
    purchase_taxes = st.number_input("Purchase taxes", min_value=0, value=1_500, step=250)
    renovation_cost = st.number_input("Renovation", min_value=0, value=0, step=1_000)
    other_initial_costs = st.number_input("Other initial costs", min_value=0, value=0, step=100)


mortgage_amount = house_price * mortgage_percent / 100
down_payment = house_price - mortgage_amount
initial_fixed_costs = (
    notary_cost
    + istruttoria_cost
    + appraisal_cost
    + agency_cost
    + purchase_taxes
    + renovation_cost
    + other_initial_costs
)
upfront_cash_needed = down_payment + initial_fixed_costs
monthly_payment = calculate_monthly_payment(mortgage_amount, annual_rate, years)
total_interest = calculate_total_interest(mortgage_amount, annual_rate, years)

metrics_area = st.container()
summary_area = st.container()
room_area = st.container()

with room_area:
    st.divider()
    st.subheader("Room Pricing")
    room_controls_col, room_chart_col = st.columns([0.42, 0.58])

    with room_controls_col:
        rental_settings_col1, rental_settings_col2 = st.columns(2)
        occupancy_rate = rental_settings_col1.slider("Occupancy rate", 50, 100, 90, 5)
        rental_tax_rate = rental_settings_col2.slider("Rental tax rate", 0, 35, 21, 1)

        cost_col1, cost_col2, cost_col3 = st.columns(3)
        condo_costs = cost_col1.number_input("Condo costs", min_value=0, value=80, step=10)
        maintenance = cost_col2.number_input(
            "Maintenance reserve",
            min_value=0,
            value=80,
            step=10,
        )
        other_costs = cost_col3.number_input("Other costs", min_value=0, value=0, step=10)

        default_room_prices = pd.DataFrame({"monthly_rent": [400, 425, 450]})
        room_prices_df = st.data_editor(
            default_room_prices,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "monthly_rent": st.column_config.NumberColumn(
                    "Monthly rent (€)",
                    min_value=0,
                    step=25,
                    format="€%.0f",
                ),
            },
            key="room_prices",
        )

    room_prices = [
        coerce_positive_float(value)
        for value in room_prices_df["monthly_rent"].tolist()
        if not pd.isna(value)
    ]
    rooms = len(room_prices)
    if rooms == 0:
        room_prices = [0]
        rooms = 1

    monthly_costs = condo_costs + maintenance + other_costs
    gross_rent = calculate_monthly_rental_income(rooms, room_prices, occupancy_rate)
    net_rent = calculate_net_rental_income(gross_rent, rental_tax_rate)
    cashflow_before_costs = net_rent - monthly_payment
    cashflow_after_costs = net_rent - monthly_payment - monthly_costs

    with room_chart_col:
        st.subheader("Rooms Break-even")
        room_scenarios = build_room_scenarios(
            max_rooms=rooms,
            rent_per_room=room_prices,
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

with summary_area:
    st.divider()
    summary_chart_col, summary_table_col = st.columns([0.46, 0.54])

with summary_chart_col:
    st.subheader("Upfront Cost Split")
    initial_costs = pd.DataFrame(
        [
            ("Down payment", down_payment),
            ("Notary", notary_cost),
            ("Istruttoria", istruttoria_cost),
            ("Perizia", appraisal_cost),
            ("Agency", agency_cost),
            ("Purchase taxes", purchase_taxes),
            ("Renovation", renovation_cost),
            ("Other initial costs", other_initial_costs),
        ],
        columns=["Cost", "Amount"],
    )
    upfront_fig = px.pie(
        initial_costs[initial_costs["Amount"] > 0],
        names="Cost",
        values="Amount",
        hole=0.45,
    )
    upfront_fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(upfront_fig, use_container_width=True)

with summary_table_col:
    st.subheader("Scenario Summary")
    summary = pd.DataFrame(
        [
            ("House price", house_price),
            ("Down payment", down_payment),
            ("Initial fixed costs", initial_fixed_costs),
            ("Upfront cash needed", upfront_cash_needed),
            ("Mortgage amount", mortgage_amount),
            ("Monthly payment", monthly_payment),
            ("Total interest", total_interest),
            ("Rented rooms", rooms),
            ("Room prices total", sum(room_prices[:rooms])),
            ("Gross rent", gross_rent),
            ("Net rent after tax", net_rent),
            ("Monthly operating costs", monthly_costs),
            ("Cashflow before costs", cashflow_before_costs),
            ("Cashflow after costs", cashflow_after_costs),
        ],
        columns=["Item", "Amount"],
    )
    summary["Amount"] = summary.apply(
        lambda row: f"{int(row['Amount'])}"
        if row["Item"] == "Rented rooms"
        else f"€{row['Amount']:,.0f}",
        axis=1,
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)

with metrics_area:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Mortgage amount", f"€{mortgage_amount:,.0f}")
    col2.metric("Upfront cash needed", f"€{upfront_cash_needed:,.0f}")
    col3.metric("Monthly payment", f"€{monthly_payment:,.0f}")
    col4.metric("Net rental income", f"€{net_rent:,.0f}")
    col5.metric("Monthly cashflow", f"€{cashflow_after_costs:,.0f}")

st.subheader("Interest Rate Sensitivity")
rate_scenarios = build_rate_scenarios(
    mortgage_amount=mortgage_amount,
    years=years,
    rates=[round(rate / 10, 1) for rate in range(20, 61, 5)],
    net_rent=net_rent,
)

rate_fig = px.line(
    rate_scenarios,
    x="annual_rate",
    y=["monthly_payment", "net_rent"],
    markers=True,
    labels={
        "annual_rate": "Annual rate (%)",
        "value": "Monthly amount",
        "variable": "Metric",
    },
)
rate_fig.update_layout(yaxis_tickprefix="€")
st.plotly_chart(rate_fig, use_container_width=True)

st.subheader("Combined Repayment Scenario")
combined_controls_col, combined_chart_col = st.columns([0.36, 0.64])

with combined_controls_col:
    st.caption(
        "Rent first covers the normal mortgage payment. This scenario redirects a percentage of the remaining rent surplus as extra principal."
    )
    surplus_redirect_share = st.slider(
        "Rent surplus redirected to mortgage",
        min_value=0,
        max_value=100,
        value=100,
        step=5,
    )
    default_events = pd.DataFrame(
        [
            {"after_years": 5, "amount": 10_000},
        ]
    )
    repayment_events_df = st.data_editor(
        default_events,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "after_years": st.column_config.NumberColumn(
                "After years",
                min_value=1,
                step=1,
                help="Year when the extra payment happens.",
            ),
            "amount": st.column_config.NumberColumn(
                "Amount (€)",
                min_value=0,
                step=1_000,
                format="€%.0f",
                help="Extra repayment amount.",
            ),
        },
        key="combined_repayment_events",
    )

repayment_events = []
for row in repayment_events_df.itertuples(index=False):
    after_years = coerce_positive_float(getattr(row, "after_years", 0))
    amount = coerce_positive_float(getattr(row, "amount", 0))
    if after_years > 0 and amount > 0:
        repayment_events.append(
            {
                "after_years": after_years,
                "amount": amount,
            }
        )

base_schedule = build_standard_schedule(mortgage_amount, annual_rate, years, monthly_payment)
room_rent_gross = gross_rent
room_rent_tax = room_rent_gross * rental_tax_rate / 100
room_rent_after_tax = room_rent_gross - room_rent_tax
rent_surplus_after_payment = max(room_rent_after_tax - monthly_payment, 0)
rent_deficit_after_payment = max(monthly_payment - room_rent_after_tax, 0)
rent_surplus_to_mortgage = rent_surplus_after_payment * surplus_redirect_share / 100

combined_result = simulate_combined_repayment(
    principal=mortgage_amount,
    annual_rate=annual_rate,
    years=years,
    room_rent_income=rent_surplus_to_mortgage,
    repayment_events=repayment_events,
)

combined_months = combined_result["months"]
base_months = len(base_schedule)
duration_saved_months = max(base_months - combined_months, 0)

combined_col1, combined_col2, combined_col3, combined_col4 = (
    combined_chart_col.columns(4)
)
combined_col1.metric("Rent after payment", f"€{rent_surplus_after_payment:,.0f}")
combined_col2.metric("Extra principal", f"€{rent_surplus_to_mortgage:,.0f}")
combined_col3.metric("Interest saved", f"€{combined_result['interest_saved']:,.0f}")
combined_col4.metric("Duration saved", f"{duration_saved_months} months")

if rent_deficit_after_payment > 0:
    combined_chart_col.warning(
        f"Net rent is €{rent_deficit_after_payment:,.0f} below the monthly mortgage payment, so no recurring rent surplus is redirected."
    )

combined_projection = pd.DataFrame(combined_result["schedule"])
combined_projection["scenario"] = "Combined strategy"
base_projection = pd.DataFrame(base_schedule)
base_projection["scenario"] = "Base mortgage"
combined_balance_projection = pd.concat(
    [base_projection, combined_projection],
    ignore_index=True,
)
combined_balance_projection["year"] = combined_balance_projection["month"] / 12

combined_balance_fig = px.line(
    combined_balance_projection,
    x="year",
    y="balance",
    color="scenario",
    labels={
        "year": "Year",
        "balance": "Remaining debt",
        "scenario": "Scenario",
    },
)
for event in repayment_events:
    combined_balance_fig.add_vline(
        x=event["after_years"],
        line_dash="dot",
        line_color="#6b7280",
    )
combined_balance_fig.update_layout(yaxis_tickprefix="€")
combined_chart_col.plotly_chart(combined_balance_fig, use_container_width=True)

combined_chart_col.caption(
    "The curve assumes the normal mortgage payment is always made. Only the selected share of rent left after that payment is applied as recurring extra principal."
)
