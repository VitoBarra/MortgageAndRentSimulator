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


def documentation_formula(view: str, explanation: str, latex: str, code: str) -> None:
    st.markdown(explanation)
    if view == "Math formulas":
        st.latex(latex)
    else:
        st.code(code, language="python")


def normalize_room_prices(room_prices_df: pd.DataFrame) -> pd.DataFrame:
    normalized = room_prices_df.copy()
    if "room" not in normalized:
        normalized.insert(0, "room", None)
    if "monthly_rent" not in normalized:
        normalized["monthly_rent"] = 0

    normalized = normalized[["room", "monthly_rent"]]
    for position, index in enumerate(normalized.index, start=1):
        room_label = normalized.at[index, "room"]
        if pd.isna(room_label) or str(room_label).strip() == "":
            normalized.at[index, "room"] = f"Room {position}"

    return normalized


def cost_input(
    container,
    label: str,
    house_price: float,
    default_amount: int,
    key: str,
    tooltip: str,
) -> float:
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
            tooltip=tooltip,
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
documentation_area = st.container()

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
            help="Total purchase price of the property before mortgage financing and upfront costs.",
        )
        mortgage_percent = purchase_col2.slider(
            "Mortgage percentage",
            50,
            100,
            100,
            5,
            help="Share of the house price financed by the mortgage. The remainder is the down payment.",
        )
        annual_rate = purchase_col1.slider(
            "Annual interest rate",
            1.0,
            8.0,
            3.5,
            0.1,
            help="Nominal annual mortgage interest rate used to calculate the monthly payment.",
        )
        years = purchase_col2.slider(
            "Mortgage duration",
            10,
            35,
            30,
            1,
            help="Mortgage term in years for the base repayment schedule.",
        )

        st.subheader("Initial Costs")
        st.markdown("**Professional fees**")
        professional_col1, professional_col2 = st.columns(2)
        notary_cost = cost_input(
            professional_col1,
            "Notary",
            house_price,
            3_000,
            "notary",
            "Notary fees paid at purchase. Use a fixed euro amount or switch to a percentage of the house price.",
        )
        agency_cost = cost_input(
            professional_col2,
            "Agency",
            house_price,
            0,
            "agency",
            "Real estate agency commission. Use a fixed euro amount or switch to a percentage of the house price.",
        )

        st.markdown("**Bank and taxes**")
        bank_col1, bank_col2, bank_col3 = st.columns(3)
        istruttoria_cost = bank_col1.number_input(
            "Istruttoria",
            min_value=0,
            value=800,
            step=100,
            help="Bank application or mortgage setup fee charged during loan approval.",
        )
        appraisal_cost = bank_col2.number_input(
            "Perizia",
            min_value=0,
            value=300,
            step=50,
            help="Property appraisal fee required by the bank before issuing the mortgage.",
        )
        purchase_taxes = bank_col3.number_input(
            "Purchase taxes",
            min_value=0,
            value=1_500,
            step=250,
            help="Taxes due on the property purchase, excluding professional and bank fees.",
        )

        st.markdown("**Property setup**")
        setup_col1, setup_col2 = st.columns(2)
        renovation_cost = setup_col1.number_input(
            "Renovation",
            min_value=0,
            value=0,
            step=1_000,
            help="One-off renovation or furnishing budget needed before renting or moving in.",
        )
        other_initial_costs = setup_col2.number_input(
            "Other initial costs",
            min_value=0,
            value=0,
            step=100,
            help="Any additional upfront cash cost not covered by the other categories.",
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
        rental_estimate_area = st.container()

        st.markdown("**Rental assumptions**")
        rental_settings_col1, rental_settings_col2 = st.columns(2)
        occupancy_rate = rental_settings_col1.slider(
            "Expected occupancy",
            50,
            100,
            90,
            5,
            help="Average share of time the rooms are expected to be rented. Lower this if you expect vacancy between tenants.",
        )
        rental_tax_rate = rental_settings_col2.slider(
            "Rental tax rate",
            0,
            35,
            21,
            1,
            help="Tax applied to gross rental income. The app subtracts this before calculating rental cashflow.",
        )

        st.markdown("**Monthly operating costs**")
        cost_col1, cost_col2, cost_col3 = st.columns(3)
        condo_costs = cost_col1.number_input(
            "Condo fees",
            min_value=0,
            value=80,
            step=10,
            help="Monthly condominium, building management, or shared-property charges.",
        )
        maintenance = cost_col2.number_input(
            "Maintenance",
            min_value=0,
            value=80,
            step=10,
            help="Monthly reserve for repairs, replacements, and routine property maintenance.",
        )
        other_costs = cost_col3.number_input(
            "Other",
            min_value=0,
            value=0,
            step=10,
            help="Other recurring monthly costs, such as utilities paid by the owner or insurance.",
        )

        st.markdown("**Room rents**")
        if "room_prices_data" not in st.session_state:
            st.session_state.room_prices_data = normalize_room_prices(
                pd.DataFrame(
                    {
                        "room": ["Room 1", "Room 2", "Room 3"],
                        "monthly_rent": [400, 425, 450],
                    }
                )
            )
        room_prices_df = st.data_editor(
            st.session_state.room_prices_data,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "room": st.column_config.TextColumn(
                    "Room",
                    help="Optional room label used only to keep the rent table readable.",
                ),
                "monthly_rent": st.column_config.NumberColumn(
                    "Monthly rent",
                    min_value=0,
                    step=25,
                    format="€%.0f",
                    help="Monthly rent charged for this room. Each row counts as one rentable room.",
                ),
            },
            key="room_prices",
        )
        normalized_room_prices_df = normalize_room_prices(room_prices_df)
        has_missing_room_labels = not normalized_room_prices_df["room"].equals(room_prices_df["room"])
        st.session_state.room_prices_data = normalized_room_prices_df
        if has_missing_room_labels:
            st.rerun()

    room_prices = [
        coerce_positive_float(value)
        for value in normalized_room_prices_df["monthly_rent"].tolist()
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

    with rental_estimate_area:
        st.markdown("**Rental estimate**")
        estimate_col1, estimate_col2, estimate_col3 = st.columns(3)
        estimate_col1.metric("Gross rent", money(gross_rent))
        estimate_col2.metric("Net rent", money(net_rent))
        estimate_col3.metric("Costs", money(monthly_costs))

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
            help="Expected annual return for surplus cash invested instead of used for early mortgage repayment.",
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

with documentation_area:
    st.divider()
    st.subheader("Formulas And References")
    st.caption(
        "This section documents the formulas used by the simulator. Inputs such as taxes, rents, costs, and expected returns are assumptions entered by the user; verify them against your contract, lender quote, and tax situation."
    )
    formula_view = st.segmented_control(
        "Documentation view",
        ["Math formulas", "Code formulas"],
        default="Math formulas",
        help="Choose rendered mathematical formulas or code-style formulas matching the implementation. Both views include explanations.",
    )

    with st.expander("Purchase and upfront cash", expanded=False):
        documentation_formula(
            formula_view,
            "**Mortgage amount.** The mortgage covers the selected share of the house price.",
            r"\text{Mortgage} = H \times \frac{L}{100}",
            "mortgage_amount = house_price * mortgage_percentage / 100",
        )
        documentation_formula(
            formula_view,
            "**Down payment.** Anything not financed by the mortgage must be paid upfront.",
            r"\text{Down payment} = H - \text{Mortgage}",
            "down_payment = house_price - mortgage_amount",
        )
        documentation_formula(
            formula_view,
            "**Percentage-based costs.** Notary and agency can be entered as a percentage of the house price.",
            r"\text{Percentage cost} = H \times \frac{p}{100}",
            "percentage_cost = house_price * percentage / 100",
        )
        documentation_formula(
            formula_view,
            "**Initial costs.** All one-off purchase costs are added together.",
            r"C = C_\text{notary} + C_\text{bank} + C_\text{appraisal} + C_\text{agency} + C_\text{taxes} + C_\text{renovation} + C_\text{other}",
            """initial_fixed_costs = (
    notary_cost
    + istruttoria_cost
    + appraisal_cost
    + agency_cost
    + purchase_taxes
    + renovation_cost
    + other_initial_costs
)""",
        )
        documentation_formula(
            formula_view,
            "**Upfront cash.** The cash needed at purchase is the down payment plus all initial costs.",
            r"\text{Upfront cash} = \text{Down payment} + C",
            "upfront_cash_needed = down_payment + initial_fixed_costs",
        )

    with st.expander("Mortgage payment and amortization", expanded=False):
        st.markdown(
            "The app models a fixed-rate amortizing mortgage. The normal payment is constant, but early payments contain more interest because the remaining balance is higher."
        )
        documentation_formula(
            formula_view,
            "**Monthly rate and term.** The annual mortgage rate is converted to a monthly rate and the term is converted to months.",
            r"r = \frac{\text{annual rate}}{100 \times 12} \qquad n = 12 \times \text{years}",
            "monthly_rate = annual_rate / 100 / 12\nmonths = years * 12",
        )
        documentation_formula(
            formula_view,
            "**Monthly payment.** For a positive interest rate, the payment is the standard amortizing-loan payment.",
            r"M = \frac{P r}{1 - (1 + r)^{-n}}",
            "monthly_payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)",
        )
        documentation_formula(
            formula_view,
            "**Zero-rate fallback.** If the interest rate is zero, the principal is spread evenly over the term.",
            r"M = \frac{P}{n}",
            "monthly_payment = principal / months",
        )
        documentation_formula(
            formula_view,
            "**Monthly amortization.** Each month interest is calculated first; the rest of the payment reduces principal.",
            r"I_t = B_t r \qquad Q_t = M - I_t \qquad B_{t+1} = B_t - Q_t",
            """interest = balance * monthly_rate
principal_payment = monthly_payment - interest
balance = balance - principal_payment""",
        )

    with st.expander("Rental income and cashflow", expanded=False):
        documentation_formula(
            formula_view,
            "**Gross rent.** The room rents are summed and adjusted by expected occupancy.",
            r"G = \left(\sum_{j=1}^{k} R_j\right) \times \frac{o}{100}",
            "gross_rent = sum(room_monthly_rents) * occupancy_rate / 100",
        )
        documentation_formula(
            formula_view,
            "**Net rent.** Rental tax is applied to gross rent using the user-entered tax rate.",
            r"N = G \times \left(1 - \frac{\tau}{100}\right)",
            "net_rent = gross_rent * (1 - rental_tax_rate / 100)",
        )
        documentation_formula(
            formula_view,
            "**Operating costs.** Monthly owner costs are added together before calculating final cashflow.",
            r"O = O_\text{condo} + O_\text{maintenance} + O_\text{other}",
            "monthly_costs = condo_costs + maintenance + other_costs",
        )
        documentation_formula(
            formula_view,
            "**Cashflow.** The app subtracts the mortgage payment and monthly operating costs from net rent.",
            r"CF = N - M - O",
            "cashflow_after_costs = net_rent - monthly_payment - monthly_costs",
        )
        documentation_formula(
            formula_view,
            "**Break-even chart.** The same cashflow formula is repeated for one room, two rooms, and so on.",
            r"CF_k = N_k - M - O",
            "scenario_cashflow = scenario_net_rent - monthly_payment - monthly_costs",
        )

    with st.expander("Surplus allocation, repayment, and investment", expanded=False):
        documentation_formula(
            formula_view,
            "**Available surplus.** Only positive cashflow is allocated. Negative cashflow is shown as a deficit.",
            r"S = \max(CF, 0) \qquad D = \max(-CF, 0)",
            """monthly_expendable_cashflow = max(cashflow_after_costs, 0)
monthly_cashflow_deficit = max(-cashflow_after_costs, 0)""",
        )
        documentation_formula(
            formula_view,
            "**Allocation split.** The repayment share goes to extra principal; the rest is invested.",
            r"E = S \times \frac{s}{100} \qquad PMT = S \times \left(1 - \frac{s}{100}\right)",
            """rent_surplus_to_mortgage = monthly_expendable_cashflow * repayment_share / 100
rent_surplus_to_invest = monthly_expendable_cashflow * investment_share / 100""",
        )
        documentation_formula(
            formula_view,
            "**Combined repayment month.** Extra principal and one-off events reduce the balance after the normal monthly principal is applied.",
            r"B_{t+1} = B_t - Q_t - E_t - A_t",
            """balance -= normal_principal
balance -= recurring_extra_principal
balance -= one_off_repayment_due_this_month""",
        )
        documentation_formula(
            formula_view,
            "**Interest saved.** The repayment benefit is measured against the base mortgage schedule.",
            r"\text{Interest saved} = I_\text{base} - I_\text{strategy}",
            "interest_saved = base_total_interest - combined_strategy_total_interest",
        )
        documentation_formula(
            formula_view,
            "**Invested surplus future value.** The invested monthly surplus compounds monthly for the selected investment horizon.",
            r"FV = PMT \times \frac{(1 + m)^t - 1}{m}",
            "future_value = PMT * (((1 + monthly_return) ** months - 1) / monthly_return)",
        )
        documentation_formula(
            formula_view,
            "**Zero-return investment fallback.** If the alternative return is zero, there is no compounding.",
            r"FV = PMT \times t",
            "future_value = PMT * months",
        )

    with st.expander("Assumptions and references", expanded=False):
        st.markdown(
            """
**Important assumptions**

- The mortgage is modeled as a fixed-rate amortizing loan.
- The normal mortgage payment is always paid before any surplus allocation.
- Operating costs are subtracted before surplus is split between repayment and investment.
- Rental tax is a user-entered rate. The app does not determine the correct tax regime.
- Alternative investment return is a user assumption, not a forecast or guarantee.
- The app does not include inflation, vacancies beyond the occupancy input, transaction timing, tax deductions, insurance, IMU, personal income tax brackets, or investment taxes.

**References**

- [European Commission: Mortgage credit](https://finance.ec.europa.eu/consumer-finance-and-payments/retail-financial-services/credit/mortgage-credit_en)
- [Your Europe: Mortgage loans and consumer rights](https://europa.eu/youreurope/citizens/consumers/financial-products-and-services/mortgages/index_en.htm)
- [EUR-Lex: Buying residential immovable property, rules on loans](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3A0904_5)
- [European Banking Authority: Mortgage Credit Directive](https://eba.europa.eu/regulation-and-policy/single-rulebook/interactive-single-rulebook/14486)
- [European Commission: Financial literacy](https://finance.ec.europa.eu/consumer-finance-and-payments/financial-literacy_en)
- [FiscoOggi / Agenzia delle Entrate: cedolare secca on short rentals](https://www.fiscooggi.it/posta/cedolare-secca-locazioni-brevi)

Use the EU references to check mortgage-credit rights, consumer-information rules, early repayment context, and financial-literacy assumptions. Use national tax and lender documents to verify your exact tax rates, fees, and contract inputs.
"""
        )
