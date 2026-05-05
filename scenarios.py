import pandas as pd

from mortgage import calculate_monthly_payment
from rental import calculate_monthly_rental_income, calculate_net_rental_income


def build_room_scenarios(
    max_rooms: int,
    rent_per_room: float,
    occupancy_rate: float,
    rental_tax_rate: float,
    monthly_payment: float,
    monthly_costs: float,
) -> pd.DataFrame:
    rows = []

    for rooms in range(1, max_rooms + 1):
        gross_rent = calculate_monthly_rental_income(
            rooms=rooms,
            rent_per_room=rent_per_room,
            occupancy_rate=occupancy_rate,
        )
        net_rent = calculate_net_rental_income(gross_rent, rental_tax_rate)
        rows.append(
            {
                "rooms": rooms,
                "gross_rent": gross_rent,
                "net_rent": net_rent,
                "cashflow": net_rent - monthly_payment - monthly_costs,
            }
        )

    return pd.DataFrame(rows)


def build_rate_scenarios(
    mortgage_amount: float,
    years: int,
    rates: list[float],
    net_rent: float,
    monthly_costs: float,
) -> pd.DataFrame:
    rows = []

    for annual_rate in rates:
        monthly_payment = calculate_monthly_payment(mortgage_amount, annual_rate, years)
        rows.append(
            {
                "annual_rate": annual_rate,
                "monthly_payment": monthly_payment,
                "cashflow": net_rent - monthly_payment - monthly_costs,
            }
        )

    return pd.DataFrame(rows)
