def calculate_monthly_rental_income(
    rooms: int,
    rent_per_room: float,
    occupancy_rate: float,
) -> float:
    return rooms * rent_per_room * occupancy_rate / 100


def calculate_net_rental_income(gross_income: float, rental_tax_rate: float) -> float:
    return gross_income * (1 - rental_tax_rate / 100)
