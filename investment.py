from models import AllocationInputs, AllocationResult, RepaymentEvent
from mortgage import simulate_combined_repayment


def future_value_lump_sum(amount: float, annual_return: float, years: float) -> float:
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


def evaluate_allocation_strategy(
    *,
    mortgage_amount: float,
    annual_rate: float,
    years: int,
    monthly_expendable_cashflow: float,
    net_rent: float,
    monthly_costs: float,
    repayment_share: int,
    alternative_return: float,
    analysis_horizon_years: int,
    repayment_events: list[dict | RepaymentEvent],
) -> AllocationResult:
    inputs = AllocationInputs(
        mortgage_amount=mortgage_amount,
        annual_rate=annual_rate,
        years=years,
        monthly_expendable_cashflow=monthly_expendable_cashflow,
        net_rent=net_rent,
        monthly_costs=monthly_costs,
        repayment_share=repayment_share,
        alternative_return=alternative_return,
        analysis_horizon_years=analysis_horizon_years,
        repayment_events=normalize_repayment_events(repayment_events),
    )
    return evaluate_allocation_inputs(inputs)


def normalize_repayment_events(events: list[dict | RepaymentEvent]) -> list[RepaymentEvent]:
    normalized = []
    for event in events:
        if isinstance(event, RepaymentEvent):
            normalized.append(event)
        else:
            normalized.append(RepaymentEvent.from_mapping(event))

    return [
        event
        for event in normalized
        if event.after_years > 0 and event.amount > 0
    ]


def evaluate_allocation_inputs(inputs: AllocationInputs) -> AllocationResult:
    investment_share = 100 - inputs.repayment_share
    recurring_extra_principal = (
        inputs.monthly_expendable_cashflow * inputs.repayment_share / 100
    )
    monthly_investment = inputs.monthly_expendable_cashflow * investment_share / 100
    strategy_result = simulate_combined_repayment(
        principal=inputs.mortgage_amount,
        annual_rate=inputs.annual_rate,
        years=inputs.years,
        room_rent_income=recurring_extra_principal,
        repayment_events=inputs.repayment_events,
    )

    payoff_months = strategy_result.months
    analysis_horizon_months = inputs.analysis_horizon_years * 12
    pre_payoff_months = min(payoff_months, analysis_horizon_months)
    post_payoff_months = max(analysis_horizon_months - payoff_months, 0)
    post_payoff_monthly_investment = max(inputs.net_rent - inputs.monthly_costs, 0)
    pre_payoff_value_at_payoff = future_value_monthly_for_months(
        monthly_investment,
        inputs.alternative_return,
        pre_payoff_months,
    )
    pre_payoff_future_value = future_value_lump_sum(
        pre_payoff_value_at_payoff,
        inputs.alternative_return,
        post_payoff_months / 12,
    )
    post_payoff_future_value = future_value_monthly_for_months(
        post_payoff_monthly_investment,
        inputs.alternative_return,
        post_payoff_months,
    )
    strategy_future_value = pre_payoff_future_value + post_payoff_future_value
    early_repayment_benefit = strategy_result.interest_saved
    total_strategy_value = strategy_future_value + early_repayment_benefit

    return AllocationResult(
        repayment_share=inputs.repayment_share,
        investment_share=investment_share,
        alternative_return=inputs.alternative_return,
        repayment_result=strategy_result,
        payoff_months=payoff_months,
        analysis_horizon_months=analysis_horizon_months,
        pre_payoff_months=pre_payoff_months,
        post_payoff_months=post_payoff_months,
        recurring_extra_principal=recurring_extra_principal,
        monthly_investment=monthly_investment,
        post_payoff_monthly_investment=post_payoff_monthly_investment,
        pre_payoff_future_value=pre_payoff_future_value,
        post_payoff_future_value=post_payoff_future_value,
        strategy_future_value=strategy_future_value,
        early_repayment_benefit=early_repayment_benefit,
        total_strategy_value=total_strategy_value,
    )


def build_allocation_scenario_rows(
    *,
    mortgage_amount: float,
    annual_rate: float,
    years: int,
    monthly_expendable_cashflow: float,
    net_rent: float,
    monthly_costs: float,
    alternative_return: float,
    analysis_horizon_years: int,
    repayment_events: list[dict | RepaymentEvent],
    repayment_shares: range | list[int] = range(0, 101, 1),
) -> list[dict]:
    rows = []
    for repayment_share in repayment_shares:
        scenario = evaluate_allocation_strategy(
            mortgage_amount=mortgage_amount,
            annual_rate=annual_rate,
            years=years,
            monthly_expendable_cashflow=monthly_expendable_cashflow,
            net_rent=net_rent,
            monthly_costs=monthly_costs,
            repayment_share=repayment_share,
            alternative_return=alternative_return,
            analysis_horizon_years=analysis_horizon_years,
            repayment_events=repayment_events,
        )
        rows.append(
            {
                "Repayment share": repayment_share,
                "Investment share": 100 - repayment_share,
                "Payoff years": scenario.payoff_months / 12,
                "Portfolio value": scenario.strategy_future_value,
                "Interest saved": scenario.early_repayment_benefit,
                "Total split value": scenario.total_strategy_value,
            }
        )

    return rows


def build_return_scenario_rows(
    *,
    mortgage_amount: float,
    annual_rate: float,
    years: int,
    monthly_expendable_cashflow: float,
    net_rent: float,
    monthly_costs: float,
    analysis_horizon_years: int,
    repayment_events: list[dict | RepaymentEvent],
    scenario_shares: list[int],
    scenario_returns: list[float],
) -> list[dict]:
    rows = []
    for scenario_return in scenario_returns:
        return_scenarios = []
        for scenario_share in scenario_shares:
            scenario = evaluate_allocation_strategy(
                mortgage_amount=mortgage_amount,
                annual_rate=annual_rate,
                years=years,
                monthly_expendable_cashflow=monthly_expendable_cashflow,
                net_rent=net_rent,
                monthly_costs=monthly_costs,
                repayment_share=scenario_share,
                alternative_return=scenario_return,
                analysis_horizon_years=analysis_horizon_years,
                repayment_events=repayment_events,
            )
            return_scenarios.append(
                {
                    "Repayment share": scenario_share,
                    "Investment share": 100 - scenario_share,
                    "Alternative return": scenario_return,
                    "Payoff years": scenario.payoff_months / 12,
                    "Investment portfolio value": scenario.strategy_future_value,
                    "Interest saved": scenario.early_repayment_benefit,
                    "Total split value": scenario.total_strategy_value,
                }
            )

        best_total_value = max(
            scenario_row["Total split value"] for scenario_row in return_scenarios
        )
        for scenario_row in return_scenarios:
            scenario_row["Total value vs best model"] = (
                scenario_row["Total split value"] - best_total_value
            )
        rows.extend(return_scenarios)

    return rows
