import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from mortgage import (
    build_standard_schedule,
    calculate_monthly_payment,
    calculate_total_interest,
    simulate_combined_repayment,
)
from rental import calculate_monthly_rental_income, calculate_net_rental_income
from scenarios import build_room_scenarios


allocation_buttons = components.declare_component(
    "allocation_buttons",
    path=str(Path(__file__).parent / "components" / "allocation_buttons"),
)

cost_amount_input = components.declare_component(
    "cost_amount_input",
    path=str(Path(__file__).parent / "components" / "cost_amount_input"),
)


def coerce_positive_float(value: object) -> float:
    if pd.isna(value):
        return 0
    return max(float(value), 0)


def future_value_lump_sum(amount: float, annual_return: float, years: int) -> float:
    return amount * (1 + annual_return / 100) ** years


def future_value_monthly(amount: float, annual_return: float, years: int) -> float:
    return future_value_monthly_for_months(amount, annual_return, years * 12)


def future_value_monthly_for_months(
    amount: float,
    annual_return: float,
    months: int,
) -> float:
    if months <= 0:
        return 0

    monthly_return = annual_return / 100 / 12
    if monthly_return == 0:
        return amount * months

    return amount * (((1 + monthly_return) ** months - 1) / monthly_return)


def money(value: float) -> str:
    return f"€{value:,.0f}"


def cost_input(container, label: str, house_price: float, default_amount: int, key: str) -> float:
    state_key = f"{key}_cost_input"
    if state_key not in st.session_state:
        st.session_state[state_key] = {"mode": "amount", "value": float(default_amount)}

    current = st.session_state[state_key]
    with container:
        result = cost_amount_input(
            label=label,
            house_price=house_price,
            mode=current["mode"],
            value=current["value"],
            tooltip=f"Enter {label.lower()} as a fixed euro amount or click the button to use a percentage of the house price.",
            key=key,
            default=current,
        )

    if isinstance(result, dict):
        st.session_state[state_key] = {
            "mode": result.get("mode", current["mode"]),
            "value": float(result.get("value", current["value"]) or 0),
        }
        return float(result.get("amount", 0))

    if current["mode"] == "percent":
        return house_price * current["value"] / 100

    return current["value"]


st.set_page_config(
    page_title="Mortgage Simulator",
    page_icon="🏠",
    layout="wide",
)

st.title("Mortgage Simulator")

summary_area = st.container()
purchase_area = st.container()
room_area = st.container()
repayment_area = st.container()
details_area = st.container()

with purchase_area:
    st.divider()
    st.subheader("Purchase And Mortgage")
    purchase_controls_col, purchase_chart_col = st.columns([0.52, 0.48])

    with purchase_controls_col:
        purchase_col1, purchase_col2 = st.columns(2)
        house_price = purchase_col1.number_input(
            "House price",
            min_value=50_000,
            max_value=500_000,
            value=140_000,
            step=5_000,
            format="%d",
        )
        mortgage_percent = purchase_col2.slider("Mortgage percentage", 50, 100, 100, 5)
        annual_rate = purchase_col1.slider("Annual interest rate", 1.0, 8.0, 3.5, 0.1)
        years = purchase_col2.slider("Mortgage duration", 10, 35, 30, 1)

        st.subheader("Initial Costs")
        cost_col1, cost_col2, cost_col3 = st.columns(3)
        notary_cost = cost_input(cost_col1, "Notary", house_price, 3_000, "notary")
        istruttoria_cost = cost_col2.number_input(
            "Istruttoria",
            min_value=0,
            value=800,
            step=100,
        )
        appraisal_cost = cost_col3.number_input("Perizia", min_value=0, value=300, step=50)
        agency_cost = cost_input(cost_col1, "Agency", house_price, 0, "agency")
        purchase_taxes = cost_col2.number_input(
            "Purchase taxes",
            min_value=0,
            value=1_500,
            step=250,
        )
        renovation_cost = cost_col3.number_input(
            "Renovation",
            min_value=0,
            value=0,
            step=1_000,
        )
        other_initial_costs = cost_col1.number_input(
            "Other initial costs",
            min_value=0,
            value=0,
            step=100,
        )

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

with purchase_chart_col:
    st.subheader("Upfront Cost Split")
    upfront_fig = px.pie(
        initial_costs[initial_costs["Amount"] > 0],
        names="Cost",
        values="Amount",
        hole=0.45,
    )
    upfront_fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(upfront_fig, use_container_width=True)

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

with repayment_area:
    st.divider()
    st.subheader("Surplus Allocation")
    combined_controls_col, combined_chart_col = st.columns([0.36, 0.64])

    with combined_controls_col:
        st.caption(
            "Rent first covers the normal mortgage payment and monthly operating costs. The remaining cashflow is fully allocated between early repayment and investment."
        )
        if "surplus_repayment_share" not in st.session_state:
            st.session_state.surplus_repayment_share = 100

        allocation_left_col, allocation_buttons_col, allocation_right_col = st.columns(
            [0.42, 0.16, 0.42]
        )
        with allocation_buttons_col:
            allocation_click = allocation_buttons(key="surplus_allocation_buttons")
            if allocation_click:
                click_id = allocation_click.get("id")
                if click_id != st.session_state.get("last_surplus_allocation_click"):
                    st.session_state.last_surplus_allocation_click = click_id
                    step = int(allocation_click.get("step", 5))
                    if allocation_click.get("direction") == "invest":
                        st.session_state.surplus_repayment_share = max(
                            st.session_state.surplus_repayment_share - step,
                            0,
                        )
                    elif allocation_click.get("direction") == "repay":
                        st.session_state.surplus_repayment_share = min(
                            st.session_state.surplus_repayment_share + step,
                            100,
                        )

        repayment_share = int(st.session_state.surplus_repayment_share)
        investment_share = 100 - repayment_share
        allocation_left_col.metric("Surplus used for early repayment", f"{repayment_share}%")
        allocation_right_col.metric("Surplus invested", f"{investment_share}%")
        alternative_return = allocation_right_col.number_input(
            "Alternative annual return",
            min_value=0.0,
            max_value=12.0,
            value=4.0,
            step=0.25,
            format="%.2f",
        )
        default_events = pd.DataFrame(
            [
                {"after_years": 5, "amount": 10_000},
            ]
        )
        st.markdown("**One-off repayment events**")
        st.caption("Extra payments applied directly to the mortgage after the selected number of years.")
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
monthly_expendable_cashflow = max(cashflow_after_costs, 0)
monthly_cashflow_deficit = max(-cashflow_after_costs, 0)
rent_surplus_to_mortgage = monthly_expendable_cashflow * repayment_share / 100
rent_surplus_to_invest = monthly_expendable_cashflow * investment_share / 100

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
investment_horizon_months = combined_months
invested_surplus_future_value = future_value_monthly_for_months(
    rent_surplus_to_invest,
    alternative_return,
    investment_horizon_months,
)
early_repayment_benefit = combined_result["interest_saved"]
investment_vs_repayment_delta = invested_surplus_future_value - early_repayment_benefit

with combined_chart_col:
    combined_col1, combined_col2, combined_col3, combined_col4, combined_col5 = st.columns(5)
    combined_col1.metric("Monthly cashflow", money(monthly_expendable_cashflow))
    combined_col2.metric("Extra principal", money(rent_surplus_to_mortgage))
    combined_col3.metric("Invested monthly", money(rent_surplus_to_invest))
    combined_col4.metric("Interest saved", money(combined_result["interest_saved"]))
    combined_col5.metric("Invested value", money(invested_surplus_future_value))
    st.caption(
        f"Investment horizon follows the reduced mortgage duration: {investment_horizon_months} months."
    )

    if monthly_cashflow_deficit > 0:
        st.warning(
            f"Monthly cashflow is {money(monthly_cashflow_deficit)} below zero after mortgage payment and operating costs, so no recurring surplus is allocated."
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
    st.plotly_chart(combined_balance_fig, use_container_width=True)
    st.caption(
        "The mortgage curve assumes the normal payment and operating costs are always covered first. The selected repayment share is applied as recurring extra principal; the remaining cashflow is modeled as a monthly investment."
    )

    allocation_rows = pd.DataFrame(
        [
            (
                "Early repayment",
                f"{repayment_share}%",
                rent_surplus_to_mortgage,
                early_repayment_benefit,
            ),
            (
                "Investment",
                f"{investment_share}%",
                rent_surplus_to_invest,
                invested_surplus_future_value,
            ),
            (
                "Investment minus repayment benefit",
                "",
                0,
                investment_vs_repayment_delta,
            ),
        ],
        columns=["Use", "Share", "Monthly amount", "Estimated benefit"],
    )
    allocation_rows["Monthly amount"] = allocation_rows["Monthly amount"].map(money)
    allocation_rows["Estimated benefit"] = allocation_rows["Estimated benefit"].map(money)
    st.dataframe(allocation_rows, hide_index=True, use_container_width=True)

with summary_area:
    st.subheader("Summary")
    summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
    summary_col1.metric("Upfront cash", money(upfront_cash_needed))
    summary_col2.metric("Mortgage amount", money(mortgage_amount))
    summary_col3.metric("Monthly payment", money(monthly_payment))
    summary_col4.metric("Net rent", money(net_rent))
    summary_col5.metric("Monthly cashflow", money(cashflow_after_costs))

with details_area:
    st.divider()
    st.subheader("Detailed Summary")

    purchase_summary = pd.DataFrame(
        [
            ("House price", money(house_price)),
            ("Mortgage percentage", f"{mortgage_percent}%"),
            ("Mortgage amount", money(mortgage_amount)),
            ("Down payment", money(down_payment)),
            ("Annual interest rate", f"{annual_rate:.1f}%"),
            ("Mortgage duration", f"{years} years"),
            ("Monthly payment", money(monthly_payment)),
            ("Base total interest", money(total_interest)),
        ],
        columns=["Item", "Value"],
    )

    initial_costs_summary = initial_costs.copy()
    initial_costs_summary["Amount"] = initial_costs_summary["Amount"].map(money)

    rental_summary = pd.DataFrame(
        [
            ("Rented rooms", f"{rooms}"),
            ("Room prices total", money(sum(room_prices[:rooms]))),
            ("Occupancy rate", f"{occupancy_rate}%"),
            ("Gross rent", money(gross_rent)),
            ("Rental tax rate", f"{rental_tax_rate}%"),
            ("Net rent after tax", money(net_rent)),
            ("Monthly operating costs", money(monthly_costs)),
            ("Cashflow before costs", money(cashflow_before_costs)),
            ("Cashflow after costs", money(cashflow_after_costs)),
        ],
        columns=["Item", "Value"],
    )

    repayment_summary = pd.DataFrame(
        [
            ("Surplus used for repayment", f"{repayment_share}%"),
            ("Surplus invested", f"{investment_share}%"),
            ("Recurring extra principal", money(rent_surplus_to_mortgage)),
            ("Monthly invested surplus", money(rent_surplus_to_invest)),
            ("Investment horizon", f"{investment_horizon_months} months"),
            ("Invested future value", money(invested_surplus_future_value)),
            ("One-off repayment events", money(sum(event["amount"] for event in repayment_events))),
            ("Interest saved", money(combined_result["interest_saved"])),
            ("Duration saved", f"{duration_saved_months} months"),
            ("Combined payoff duration", f"{combined_months} months"),
        ],
        columns=["Item", "Value"],
    )

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.markdown("**Purchase**")
        st.dataframe(purchase_summary, hide_index=True, use_container_width=True)
        st.markdown("**Initial Costs**")
        st.dataframe(initial_costs_summary, hide_index=True, use_container_width=True)

    with detail_col2:
        st.markdown("**Rental**")
        st.dataframe(rental_summary, hide_index=True, use_container_width=True)
        st.markdown("**Repayment**")
        st.dataframe(repayment_summary, hide_index=True, use_container_width=True)
