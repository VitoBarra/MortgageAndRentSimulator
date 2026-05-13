import streamlit as st


def documentation_formula(view: str, explanation: str, latex: str, code: str) -> None:
    st.markdown(explanation)
    if view == "Math formulas":
        st.latex(latex)
    else:
        st.code(code, language="python")


def render_documentation_section(container) -> None:
    with container:
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
            documentation_formula(
                formula_view,
                "**French amortization.** The monthly payment is constant; interest declines over time and principal repayment increases.",
                r"M_t = M",
                "payment = constant_monthly_payment",
            )
            documentation_formula(
                formula_view,
                "**Italian amortization.** Principal repayment is constant; total monthly payment declines as interest declines.",
                r"Q_t = \frac{P}{n} \qquad M_t = Q_t + I_t",
                "principal_payment = principal / months\npayment = principal_payment + interest",
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

        with st.expander("Rent vs interest", expanded=False):
            documentation_formula(
                formula_view,
                "**Initial cash purchase target.** To buy outright, the model starts from the house price plus initial fixed costs.",
                r"T = H + C",
                "cash_purchase_target = house_price + initial_fixed_costs",
            )
            documentation_formula(
                formula_view,
                "**Growing cash purchase target.** While waiting, the cash target can grow or shrink with the expected house price growth assumption.",
                r"T_t = T_{t-1} \times (1 + g)",
                "future_cash_purchase_target *= 1 + monthly_house_growth",
            )
            documentation_formula(
                formula_view,
                "**Saved cash growth.** Current cash and new monthly savings can compound with the expected savings return assumption.",
                r"A_t = A_{t-1} \times (1 + r) + S",
                "saved_cash = saved_cash * (1 + monthly_savings_return) + monthly_saving_after_rent",
            )
            documentation_formula(
                formula_view,
                "**Time to buy cash.** The model simulates month by month until saved cash reaches the future cash purchase target.",
                r"A_t \geq T_t",
                "months_to_cash_purchase = first_month_where_saved_cash_reaches_target",
            )
            documentation_formula(
                formula_view,
                "**Rent paid while waiting.** If you wait to buy in cash, the model multiplies current rent by the estimated saving period.",
                r"R_\text{wait} = R_\text{monthly} \times t",
                "rent_paid_while_waiting = current_monthly_rent * months_to_cash_purchase",
            )
            documentation_formula(
                formula_view,
                "**Rent-equivalent interest.** Mortgage interest is expressed as years of current rent.",
                r"Y = \frac{I_\text{mortgage}}{12 \times R_\text{monthly}}",
                "rent_equivalent_years = total_interest / (current_monthly_rent * 12)",
            )
            documentation_formula(
                formula_view,
                "**Rent minus interest.** Positive values mean waiting rent is higher than mortgage interest in this simplified comparison.",
                r"\Delta = R_\text{wait} - I_\text{mortgage}",
                "rent_minus_interest = rent_paid_while_waiting - total_interest",
            )
            documentation_formula(
                formula_view,
                "**Buy-now savings during the waiting horizon.** If you buy now, the model compounds your expected monthly saving over the same number of months it would take to buy in cash.",
                r"FV_\text{buy-now savings} = \sum_{t=1}^{n} S_\text{buy} (1 + r)^{n-t}",
                "buy_now_savings_while_waiting = future_value_monthly_for_months(monthly_saving_if_buy_now, savings_return_rate, months_to_cash_purchase)",
            )
            documentation_formula(
                formula_view,
                "**Buy-now advantage.** Positive values favor buying now; negative values favor waiting to buy in cash.",
                r"A = R_\text{wait} + FV_\text{buy-now savings} - I_\text{mortgage}",
                "buy_now_advantage = rent_paid_while_waiting + buy_now_savings_while_waiting - total_interest",
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
                "**Pre-payoff invested surplus.** Before payoff, only the selected investment share of positive cashflow is invested. That value is then carried forward to the selected analysis horizon.",
                r"FV_\text{pre} = PMT \times \frac{(1 + m)^{t_\text{pre}} - 1}{m} \times (1 + m)^{t_\text{post}}",
                """pre_payoff_value_at_payoff = PMT * (((1 + monthly_return) ** pre_payoff_months - 1) / monthly_return)
pre_payoff_future_value = pre_payoff_value_at_payoff * (1 + annual_return / 100) ** (post_payoff_months / 12)""",
            )
            documentation_formula(
                formula_view,
                "**Post-payoff invested rent.** After the mortgage is paid off, the full net rent after operating costs is modeled as invested until the selected analysis horizon.",
                r"PMT_\text{post} = \max(N - O, 0)",
                "post_payoff_monthly_investment = max(net_rent - monthly_costs, 0)",
            )
            documentation_formula(
                formula_view,
                "**Post-payoff future value.** The post-payoff monthly cashflow compounds for the months between payoff and the selected horizon.",
                r"FV_\text{post} = PMT_\text{post} \times \frac{(1 + m)^{t_\text{post}} - 1}{m}",
                """post_payoff_invested_future_value = future_value_monthly_for_months(
    post_payoff_monthly_investment,
    alternative_return,
    post_payoff_investment_months,
)""",
            )
            documentation_formula(
                formula_view,
                "**Strategy portfolio value.** The portfolio value is the modeled investment balance at the analysis horizon.",
                r"FV_\text{strategy} = FV_\text{pre} + FV_\text{post}",
                "strategy_future_value = pre_payoff_future_value + post_payoff_future_value",
            )
            documentation_formula(
                formula_view,
                "**Total split value.** The decision comparison combines the investment portfolio with mortgage interest saved, so repayment and investment both contribute to the same score.",
                r"V_\text{split} = FV_\text{strategy} + \text{Interest saved}",
                "total_strategy_value = strategy_future_value + early_repayment_benefit",
            )
            documentation_formula(
                formula_view,
                "**Zero-return investment fallback.** If the alternative return is zero, there is no compounding.",
                r"FV = PMT \times t",
                "future_value = PMT * months",
            )
            documentation_formula(
                formula_view,
                "**Scenario comparison.** Allocation scenarios are compared against the best modeled allocation using total split value at the same analysis horizon.",
                r"\Delta = V_\text{split} - V_\text{best}",
                "value_vs_best_model = total_strategy_value - best_total_value",
            )

        with st.expander("Assumptions and references", expanded=False):
            st.markdown(
                """
**Important assumptions**

- The mortgage is modeled as a fixed-rate amortizing loan.
- The normal mortgage payment is always paid before any surplus allocation.
- Operating costs are subtracted before surplus is split between repayment and investment.
- After mortgage payoff, full net rent after operating costs is modeled as invested until the selected analysis horizon.
- One-off repayment events are treated as mortgage repayments only; they are not also counted as invested cash.
- Rent-vs-interest comparison ignores house price changes, investment returns, inflation, taxes, and opportunity cost.
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
