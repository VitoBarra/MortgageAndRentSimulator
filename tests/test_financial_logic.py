import math
import unittest

from mortgage import (
    build_standard_schedule,
    calculate_monthly_payment,
    calculate_monthly_payment_for_months,
    calculate_total_interest,
    simulate_combined_repayment,
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
        self.assertAlmostEqual(schedule[-1]["balance"], 0, places=6)
        self.assertGreater(schedule[0]["interest"], schedule[-1]["interest"])
        self.assertLess(schedule[0]["principal"], schedule[-1]["principal"])

    def test_total_interest_matches_schedule_interest_sum(self):
        principal = 100_000
        annual_rate = 3
        years = 30

        total_interest = calculate_total_interest(principal, annual_rate, years)
        schedule_interest = sum(
            row["interest"]
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

        self.assertLess(result["months"], len(base_schedule))
        self.assertGreater(result["interest_saved"], 0)
        self.assertGreater(result["extra_payment_total"], 0)
        self.assertAlmostEqual(result["schedule"][-1]["balance"], 0, places=6)

    def test_combined_repayment_applies_one_off_events(self):
        result = simulate_combined_repayment(
            principal=100_000,
            annual_rate=3,
            years=30,
            room_rent_income=0,
            repayment_events=[{"after_years": 1, "amount": 10_000}],
        )

        event_month = result["schedule"][11]
        self.assertGreaterEqual(event_month["extra_payment"], 10_000)
        self.assertEqual(result["event_total"], 10_000)


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
            monthly_expendable_cashflow=500,
            net_rent=1_500,
            monthly_costs=300,
            repayment_share=40,
            alternative_return=4,
            analysis_horizon_years=30,
            repayment_events=[],
        )

        self.assertEqual(strategy["repayment_share"], 40)
        self.assertEqual(strategy["investment_share"], 60)
        self.assertEqual(strategy["recurring_extra_principal"], 200)
        self.assertEqual(strategy["monthly_investment"], 300)
        self.assertGreater(strategy["strategy_future_value"], 0)
        self.assertGreater(strategy["early_repayment_benefit"], 0)
        self.assertAlmostEqual(
            strategy["total_strategy_value"],
            strategy["strategy_future_value"] + strategy["early_repayment_benefit"],
        )

    def test_allocation_scenario_rows_are_generated_for_requested_shares(self):
        from investment import build_allocation_scenario_rows

        rows = build_allocation_scenario_rows(
            mortgage_amount=100_000,
            annual_rate=3,
            years=30,
            monthly_expendable_cashflow=500,
            net_rent=1_500,
            monthly_costs=300,
            alternative_return=4,
            analysis_horizon_years=30,
            repayment_events=[],
            repayment_shares=[0, 50, 100],
        )

        self.assertEqual([row["Repayment share"] for row in rows], [0, 50, 100])
        self.assertEqual([row["Investment share"] for row in rows], [100, 50, 0])
        self.assertTrue(all(row["Total split value"] > 0 for row in rows))

    def test_return_scenario_rows_mark_best_model_per_return(self):
        from investment import build_return_scenario_rows

        rows = build_return_scenario_rows(
            mortgage_amount=100_000,
            annual_rate=3,
            years=30,
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
            self.assertEqual(
                max(row["Total value vs best model"] for row in return_rows),
                0,
            )


if __name__ == "__main__":
    unittest.main()
