import math
import unittest

from mortgage import (
    FRENCH_AMORTIZATION,
    ITALIAN_AMORTIZATION,
    build_standard_schedule,
    calculate_monthly_payment,
    calculate_monthly_payment_for_months,
    calculate_total_interest,
    simulate_combined_repayment,
)
from models import (
    AllocationInputs,
    PurchaseCosts,
    PurchaseInputs,
    RentalInputs,
    RentalResult,
    RentVsInterestInputs,
    RepaymentResult,
    RepaymentEvent,
    ScheduleRow,
)
from rental import calculate_monthly_rental_income, calculate_net_rental_income
from scenarios import build_room_scenarios


class MortgageCalculationTests(unittest.TestCase):
    def test_monthly_payment_matches_known_amortization_value(self):
        payment = calculate_monthly_payment(
            principal=100_000,
            annual_rate=3,
            years=30,
        )

        self.assertAlmostEqual(payment, 421.60, places=2)

    def test_monthly_payment_handles_zero_interest(self):
        payment = calculate_monthly_payment_for_months(
            principal=120_000,
            annual_rate=0,
            months=240,
        )

        self.assertEqual(payment, 500)

    def test_standard_schedule_pays_down_to_zero(self):
        schedule = build_standard_schedule(
            principal=100_000,
            annual_rate=3,
            years=30,
        )

        self.assertEqual(len(schedule), 360)
        self.assertIsInstance(schedule[0], ScheduleRow)
        self.assertAlmostEqual(schedule[-1].balance, 0, places=6)
        self.assertGreater(schedule[0].interest, schedule[-1].interest)
        self.assertLess(schedule[0].principal, schedule[-1].principal)

    def test_italian_amortization_has_constant_principal_and_declining_payment(self):
        schedule = build_standard_schedule(
            principal=120_000,
            annual_rate=3,
            years=10,
            amortization_method=ITALIAN_AMORTIZATION,
        )

        self.assertEqual(len(schedule), 120)
        self.assertAlmostEqual(schedule[0].principal, 1_000, places=6)
        self.assertAlmostEqual(schedule[-1].principal, 1_000, places=6)
        self.assertGreater(schedule[0].payment, schedule[-1].payment)
        self.assertAlmostEqual(schedule[-1].balance, 0, places=6)

    def test_french_amortization_has_constant_payment(self):
        schedule = build_standard_schedule(
            principal=120_000,
            annual_rate=3,
            years=10,
            amortization_method=FRENCH_AMORTIZATION,
        )

        self.assertAlmostEqual(schedule[0].payment, schedule[1].payment, places=6)

    def test_total_interest_matches_schedule_interest_sum(self):
        principal = 100_000
        annual_rate = 3
        years = 30

        total_interest = calculate_total_interest(principal, annual_rate, years)
        schedule_interest = sum(
            row.interest
            for row in build_standard_schedule(principal, annual_rate, years)
        )

        self.assertAlmostEqual(total_interest, schedule_interest, places=6)

    def test_combined_repayment_with_extra_principal_saves_interest(self):
        principal = 100_000
        annual_rate = 3
        years = 30
        base_schedule = build_standard_schedule(principal, annual_rate, years)

        result = simulate_combined_repayment(
            principal=principal,
            annual_rate=annual_rate,
            years=years,
            room_rent_income=200,
            repayment_events=[],
        )

        self.assertIsInstance(result, RepaymentResult)
        self.assertLess(result.months, len(base_schedule))
        self.assertGreater(result.interest_saved, 0)
        self.assertGreater(result.extra_payment_total, 0)
        self.assertAlmostEqual(result.schedule[-1].balance, 0, places=6)

    def test_combined_repayment_applies_one_off_events(self):
        result = simulate_combined_repayment(
            principal=100_000,
            annual_rate=3,
            years=30,
            room_rent_income=0,
            repayment_events=[{"after_years": 1, "amount": 10_000}],
        )

        event_month = result.schedule[11]
        self.assertGreaterEqual(event_month.extra_payment, 10_000)
        self.assertEqual(result.event_total, 10_000)


class RentalCalculationTests(unittest.TestCase):
    def test_monthly_rental_income_uses_selected_room_prices(self):
        income = calculate_monthly_rental_income(
            rooms=2,
            rent_per_room=[400, 500, 600],
            occupancy_rate=90,
        )

        self.assertEqual(income, 810)

    def test_monthly_rental_income_extends_last_known_room_price(self):
        income = calculate_monthly_rental_income(
            rooms=3,
            rent_per_room=[400, 500],
            occupancy_rate=100,
        )

        self.assertEqual(income, 1_400)

    def test_net_rental_income_applies_tax_rate(self):
        self.assertEqual(calculate_net_rental_income(1_000, 21), 790)


class ModelTests(unittest.TestCase):
    def test_purchase_inputs_calculate_financed_and_cash_parts(self):
        purchase = PurchaseInputs(
            house_price=140_000,
            mortgage_percent=80,
            annual_rate=3.5,
            years=30,
            amortization_method=FRENCH_AMORTIZATION,
        )

        self.assertEqual(purchase.mortgage_amount, 112_000)
        self.assertEqual(purchase.down_payment, 28_000)

    def test_purchase_costs_total_and_rows_include_down_payment(self):
        costs = PurchaseCosts(
            notary=3_000,
            istruttoria=800,
            appraisal=300,
            agency=1_000,
            purchase_taxes=1_500,
            renovation=2_000,
            other_initial=500,
        )

        self.assertEqual(costs.total, 9_100)
        self.assertEqual(
            costs.rows(down_payment=20_000),
            [
                ("Down payment", 20_000),
                ("Notary", 3_000),
                ("Istruttoria", 800),
                ("Perizia", 300),
                ("Agency", 1_000),
                ("Purchase taxes", 1_500),
                ("Renovation", 2_000),
                ("Other initial costs", 500),
            ],
        )

    def test_rental_inputs_calculate_monthly_costs(self):
        rental = RentalInputs(
            rooms=3,
            room_prices=[400, 425, 450],
            occupancy_rate=90,
            rental_tax_rate=21,
            condo_costs=80,
            maintenance=70,
            other_costs=20,
        )

        self.assertEqual(rental.monthly_costs, 170)

    def test_rental_result_groups_cashflow_outputs(self):
        result = RentalResult(
            gross_rent=1_000,
            net_rent=790,
            monthly_costs=170,
            cashflow_before_costs=300,
            cashflow_after_costs=130,
        )

        self.assertEqual(result.net_rent, 790)
        self.assertEqual(result.cashflow_after_costs, 130)


class RentVsInterestTests(unittest.TestCase):
    def test_rent_vs_interest_estimates_waiting_cost(self):
        from rent_vs_interest import evaluate_rent_vs_interest

        result = evaluate_rent_vs_interest(
            RentVsInterestInputs(
                current_monthly_rent=700,
                current_cash_available=20_000,
                monthly_saving_after_rent=1_000,
                monthly_saving_if_buy_now=200,
                cash_purchase_target=140_000,
                mortgage_interest=42_000,
            )
        )

        self.assertEqual(result.remaining_cash_to_save, 120_000)
        self.assertEqual(result.months_to_cash_purchase, 120)
        self.assertEqual(result.future_cash_purchase_target, 140_000)
        self.assertEqual(result.saved_cash_at_purchase, 140_000)
        self.assertEqual(result.rent_paid_while_waiting, 84_000)
        self.assertEqual(result.buy_now_savings_while_waiting, 24_000)
        self.assertEqual(result.buy_now_advantage_vs_waiting, 66_000)
        self.assertEqual(result.rent_equivalent_years, 5)
        self.assertEqual(result.rent_minus_interest, 42_000)

    def test_rent_vs_interest_applies_growth_and_savings_return(self):
        from rent_vs_interest import evaluate_rent_vs_interest

        result = evaluate_rent_vs_interest(
            RentVsInterestInputs(
                current_monthly_rent=700,
                current_cash_available=20_000,
                monthly_saving_after_rent=1_000,
                monthly_saving_if_buy_now=200,
                cash_purchase_target=140_000,
                mortgage_interest=42_000,
                house_price_growth_rate=2,
                savings_return_rate=4,
            )
        )

        self.assertIsNotNone(result.months_to_cash_purchase)
        self.assertGreater(result.future_cash_purchase_target, 140_000)
        self.assertGreaterEqual(
            result.saved_cash_at_purchase,
            result.future_cash_purchase_target,
        )
        self.assertGreater(result.rent_paid_while_waiting, 0)
        self.assertGreater(result.buy_now_savings_while_waiting, 0)

    def test_rent_vs_interest_sensitivity_rows_vary_growth_and_return(self):
        from rent_vs_interest import build_rent_vs_interest_sensitivity_rows

        rows = build_rent_vs_interest_sensitivity_rows(
            RentVsInterestInputs(
                current_monthly_rent=700,
                current_cash_available=20_000,
                monthly_saving_after_rent=1_000,
                monthly_saving_if_buy_now=200,
                cash_purchase_target=140_000,
                mortgage_interest=42_000,
            ),
            house_price_growth_rates=[-1, 0, 1],
            savings_return_rates=[-1, 0, 1],
        )

        self.assertEqual(len(rows), 9)
        zero_zero_row = next(
            row
            for row in rows
            if row["House price growth"] == 0 and row["Savings return"] == 0
        )
        self.assertEqual(zero_zero_row["Buy-now advantage"], 66_000)

    def test_rent_vs_interest_handles_zero_saving_capacity(self):
        from rent_vs_interest import evaluate_rent_vs_interest

        result = evaluate_rent_vs_interest(
            RentVsInterestInputs(
                current_monthly_rent=700,
                current_cash_available=20_000,
                monthly_saving_after_rent=0,
                monthly_saving_if_buy_now=0,
                cash_purchase_target=140_000,
                mortgage_interest=42_000,
            )
        )

        self.assertEqual(result.remaining_cash_to_save, 120_000)
        self.assertIsNone(result.months_to_cash_purchase)
        self.assertIsNone(result.future_cash_purchase_target)
        self.assertIsNone(result.saved_cash_at_purchase)
        self.assertIsNone(result.rent_paid_while_waiting)
        self.assertIsNone(result.buy_now_savings_while_waiting)
        self.assertIsNone(result.buy_now_advantage_vs_waiting)
        self.assertEqual(result.rent_equivalent_years, 5)
        self.assertIsNone(result.rent_minus_interest)


class ScenarioCalculationTests(unittest.TestCase):
    def test_room_scenarios_build_cashflow_rows(self):
        scenarios = build_room_scenarios(
            max_rooms=3,
            rent_per_room=[400, 500, 600],
            occupancy_rate=100,
            rental_tax_rate=20,
            monthly_payment=700,
            monthly_costs=100,
        )

        self.assertEqual(list(scenarios["rooms"]), [1, 2, 3])
        self.assertEqual(list(scenarios["gross_rent"]), [400, 900, 1_500])
        self.assertEqual(list(scenarios["net_rent"]), [320, 720, 1_200])
        self.assertEqual(list(scenarios["cashflow"]), [-480, -80, 400])


class InvestmentFormulaTests(unittest.TestCase):
    def test_future_value_formulas_are_stable(self):
        from investment import future_value_lump_sum, future_value_monthly_for_months

        self.assertAlmostEqual(future_value_lump_sum(10_000, 4, 10), 14_802.44, places=2)
        self.assertTrue(math.isclose(future_value_monthly_for_months(100, 0, 12), 1_200))
        self.assertAlmostEqual(
            future_value_monthly_for_months(100, 6, 12),
            1_233.56,
            places=2,
        )

    def test_evaluate_allocation_strategy_balances_repayment_and_investment(self):
        from investment import evaluate_allocation_strategy

        strategy = evaluate_allocation_strategy(
            mortgage_amount=100_000,
            annual_rate=3,
            years=30,
            amortization_method=FRENCH_AMORTIZATION,
            monthly_expendable_cashflow=500,
            net_rent=1_500,
            monthly_costs=300,
            repayment_share=40,
            alternative_return=4,
            analysis_horizon_years=30,
            repayment_events=[],
        )

        self.assertEqual(strategy.repayment_share, 40)
        self.assertEqual(strategy.investment_share, 60)
        self.assertEqual(strategy.recurring_extra_principal, 200)
        self.assertEqual(strategy.monthly_investment, 300)
        self.assertGreater(strategy.strategy_future_value, 0)
        self.assertGreater(strategy.early_repayment_benefit, 0)
        self.assertAlmostEqual(
            strategy.total_strategy_value,
            strategy.strategy_future_value + strategy.early_repayment_benefit,
        )

    def test_evaluate_allocation_inputs_returns_typed_result(self):
        from investment import evaluate_allocation_inputs

        result = evaluate_allocation_inputs(
            AllocationInputs(
                mortgage_amount=100_000,
                annual_rate=3,
                years=30,
                amortization_method=FRENCH_AMORTIZATION,
                monthly_expendable_cashflow=500,
                net_rent=1_500,
                monthly_costs=300,
                repayment_share=40,
                alternative_return=4,
                analysis_horizon_years=30,
                repayment_events=[RepaymentEvent(after_years=1, amount=10_000)],
            )
        )

        self.assertEqual(result.repayment_share, 40)
        self.assertEqual(result.investment_share, 60)
        self.assertEqual(result.recurring_extra_principal, 200)
        self.assertEqual(result.monthly_investment, 300)
        self.assertEqual(result.repayment_result.event_total, 10_000)

    def test_repayment_event_from_mapping_normalizes_negative_values(self):
        event = RepaymentEvent.from_mapping({"after_years": -1, "amount": -500})

        self.assertEqual(event.after_years, 0)
        self.assertEqual(event.amount, 0)

    def test_allocation_scenario_rows_are_generated_for_requested_shares(self):
        from investment import build_allocation_scenario_rows

        rows = build_allocation_scenario_rows(
            mortgage_amount=100_000,
            annual_rate=3,
            years=30,
            amortization_method=FRENCH_AMORTIZATION,
            monthly_expendable_cashflow=500,
            net_rent=1_500,
            monthly_costs=300,
            alternative_return=4,
            analysis_horizon_years=30,
            repayment_events=[RepaymentEvent(after_years=1, amount=10_000)],
            repayment_shares=[0, 50, 100],
        )

        self.assertEqual([row["Repayment share"] for row in rows], [0, 50, 100])
        self.assertEqual([row["Investment share"] for row in rows], [100, 50, 0])
        self.assertTrue(all(row["Total split value"] > 0 for row in rows))

    def test_return_scenario_rows_compare_against_fifty_fifty_per_return(self):
        from investment import build_return_scenario_rows

        rows = build_return_scenario_rows(
            mortgage_amount=100_000,
            annual_rate=3,
            years=30,
            amortization_method=FRENCH_AMORTIZATION,
            monthly_expendable_cashflow=500,
            net_rent=1_500,
            monthly_costs=300,
            analysis_horizon_years=30,
            repayment_events=[],
            scenario_shares=[0, 50, 100],
            scenario_returns=[0, 4],
        )

        self.assertEqual(len(rows), 6)
        for scenario_return in [0, 4]:
            return_rows = [
                row for row in rows if row["Alternative return"] == scenario_return
            ]
            fifty_fifty_row = next(
                row for row in return_rows if row["Repayment share"] == 50
            )
            self.assertEqual(fifty_fifty_row["Total value vs 50/50 split"], 0)


if __name__ == "__main__":
    unittest.main()
