def calculate_monthly_rental_income(
    rooms: int,
    rent_per_room: float | list[float],
    occupancy_rate: float,
) -> float:
    if isinstance(rent_per_room, list):
        selected_rents = rent_per_room[:rooms]
        if len(selected_rents) < rooms and rent_per_room:
            selected_rents.extend([rent_per_room[-1]] * (rooms - len(selected_rents)))
        total_rent = sum(selected_rents)
    else:
        total_rent = rooms * rent_per_room

    return total_rent * occupancy_rate / 100


def calculate_net_rental_income(gross_income: float, rental_tax_rate: float) -> float:
    return gross_income * (1 - rental_tax_rate / 100)
