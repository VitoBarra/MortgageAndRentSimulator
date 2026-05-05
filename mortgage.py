def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0

    months = years * 12
    monthly_rate = annual_rate / 100 / 12

    if monthly_rate == 0:
        return principal / months

    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def calculate_total_interest(principal: float, annual_rate: float, years: int) -> float:
    monthly_payment = calculate_monthly_payment(principal, annual_rate, years)
    return monthly_payment * years * 12 - principal
