from models import RentVsInterestInputs, RentVsInterestResult


MAX_WAIT_MONTHS = 100 * 12


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


def evaluate_rent_vs_interest(inputs: RentVsInterestInputs) -> RentVsInterestResult:
    remaining_cash_to_save = max(
        inputs.cash_purchase_target - inputs.current_cash_available,
        0,
    )
    annual_rent = inputs.current_monthly_rent * 12
    rent_equivalent_years = (
        inputs.mortgage_interest / annual_rent
        if annual_rent > 0
        else None
    )

    if remaining_cash_to_save == 0:
        return RentVsInterestResult(
            remaining_cash_to_save=remaining_cash_to_save,
            months_to_cash_purchase=0,
            future_cash_purchase_target=inputs.cash_purchase_target,
            saved_cash_at_purchase=inputs.current_cash_available,
            rent_paid_while_waiting=0,
            buy_now_savings_while_waiting=0,
            buy_now_advantage_vs_waiting=-inputs.mortgage_interest,
            rent_equivalent_years=rent_equivalent_years,
            rent_minus_interest=-inputs.mortgage_interest,
        )

    if inputs.monthly_saving_after_rent <= 0 and inputs.savings_return_rate <= 0:
        return RentVsInterestResult(
            remaining_cash_to_save=remaining_cash_to_save,
            months_to_cash_purchase=None,
            future_cash_purchase_target=None,
            saved_cash_at_purchase=None,
            rent_paid_while_waiting=None,
            buy_now_savings_while_waiting=None,
            buy_now_advantage_vs_waiting=None,
            rent_equivalent_years=rent_equivalent_years,
            rent_minus_interest=None,
        )

    monthly_house_growth = inputs.house_price_growth_rate / 100 / 12
    monthly_savings_return = inputs.savings_return_rate / 100 / 12
    saved_cash = inputs.current_cash_available
    future_cash_purchase_target = inputs.cash_purchase_target

    for month in range(1, MAX_WAIT_MONTHS + 1):
        future_cash_purchase_target *= 1 + monthly_house_growth
        saved_cash *= 1 + monthly_savings_return
        saved_cash += inputs.monthly_saving_after_rent

        if saved_cash >= future_cash_purchase_target:
            rent_paid_while_waiting = inputs.current_monthly_rent * month
            buy_now_savings_while_waiting = future_value_monthly_for_months(
                inputs.monthly_saving_if_buy_now,
                inputs.savings_return_rate,
                month,
            )
            return RentVsInterestResult(
                remaining_cash_to_save=remaining_cash_to_save,
                months_to_cash_purchase=month,
                future_cash_purchase_target=future_cash_purchase_target,
                saved_cash_at_purchase=saved_cash,
                rent_paid_while_waiting=rent_paid_while_waiting,
                buy_now_savings_while_waiting=buy_now_savings_while_waiting,
                buy_now_advantage_vs_waiting=(
                    rent_paid_while_waiting
                    + buy_now_savings_while_waiting
                    - inputs.mortgage_interest
                ),
                rent_equivalent_years=rent_equivalent_years,
                rent_minus_interest=rent_paid_while_waiting - inputs.mortgage_interest,
            )

    return RentVsInterestResult(
        remaining_cash_to_save=remaining_cash_to_save,
        months_to_cash_purchase=None,
        future_cash_purchase_target=None,
        saved_cash_at_purchase=None,
        rent_paid_while_waiting=None,
        buy_now_savings_while_waiting=None,
        buy_now_advantage_vs_waiting=None,
        rent_equivalent_years=rent_equivalent_years,
        rent_minus_interest=None,
    )


def build_rent_vs_interest_sensitivity_rows(
    base_inputs: RentVsInterestInputs,
    house_price_growth_rates: list[float],
    savings_return_rates: list[float],
) -> list[dict]:
    rows = []
    for house_price_growth_rate in house_price_growth_rates:
        for savings_return_rate in savings_return_rates:
            result = evaluate_rent_vs_interest(
                RentVsInterestInputs(
                    current_monthly_rent=base_inputs.current_monthly_rent,
                    current_cash_available=base_inputs.current_cash_available,
                    monthly_saving_after_rent=base_inputs.monthly_saving_after_rent,
                    monthly_saving_if_buy_now=base_inputs.monthly_saving_if_buy_now,
                    cash_purchase_target=base_inputs.cash_purchase_target,
                    mortgage_interest=base_inputs.mortgage_interest,
                    house_price_growth_rate=house_price_growth_rate,
                    savings_return_rate=savings_return_rate,
                )
            )
            rows.append(
                {
                    "House price growth": house_price_growth_rate,
                    "Savings return": savings_return_rate,
                    "Buy-now advantage": result.buy_now_advantage_vs_waiting,
                    "Months to buy cash": result.months_to_cash_purchase,
                }
            )

    return rows
