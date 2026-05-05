def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    return calculate_monthly_payment_for_months(principal, annual_rate, years * 12)


def calculate_monthly_payment_for_months(
    principal: float,
    annual_rate: float,
    months: int,
) -> float:
    if principal <= 0:
        return 0
    if months <= 0:
        return principal

    monthly_rate = annual_rate / 100 / 12

    if monthly_rate == 0:
        return principal / months

    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def calculate_total_interest(principal: float, annual_rate: float, years: int) -> float:
    monthly_payment = calculate_monthly_payment(principal, annual_rate, years)
    return monthly_payment * years * 12 - principal


def _build_schedule_with_extra_payment(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_payment: float,
    extra_monthly_payment: float = 0,
) -> list[dict]:
    if principal <= 0:
        return []

    monthly_rate = annual_rate / 100 / 12
    balance = principal
    schedule = []

    for month in range(1, years * 12 + 1):
        interest = balance * monthly_rate
        total_payment = monthly_payment + extra_monthly_payment
        principal_payment = min(total_payment - interest, balance)

        if principal_payment <= 0:
            break

        balance -= principal_payment
        schedule.append(
            {
                "month": month,
                "payment": interest + principal_payment,
                "interest": interest,
                "principal": principal_payment,
                "balance": max(balance, 0),
            }
        )

        if balance <= 0:
            break

    return schedule


def build_standard_schedule(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_payment: float | None = None,
) -> list[dict]:
    monthly_payment = monthly_payment or calculate_monthly_payment(
        principal,
        annual_rate,
        years,
    )
    return _build_schedule_with_extra_payment(principal, annual_rate, years, monthly_payment)


def simulate_room_rent_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    room_rent_income: float,
) -> dict:
    base_payment = calculate_monthly_payment(principal, annual_rate, years)
    base_schedule = build_standard_schedule(principal, annual_rate, years, base_payment)
    extra_payment = max(room_rent_income, 0)
    schedule = _build_schedule_with_extra_payment(
        principal,
        annual_rate,
        years,
        base_payment,
        extra_payment,
    )

    base_total_interest = sum(row["interest"] for row in base_schedule)
    total_interest = sum(row["interest"] for row in schedule)

    return {
        "monthly_payment": base_payment + extra_payment,
        "extra_payment": extra_payment,
        "months": len(schedule),
        "total_interest": total_interest,
        "interest_saved": base_total_interest - total_interest,
        "schedule": schedule,
    }


def simulate_combined_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    room_rent_income: float,
    repayment_events: list[dict],
) -> dict:
    base_payment = calculate_monthly_payment(principal, annual_rate, years)
    base_schedule = build_standard_schedule(principal, annual_rate, years, base_payment)
    total_months = years * 12
    monthly_rate = annual_rate / 100 / 12

    event_map: dict[int, float] = {}
    normalized_events = []
    for event in repayment_events:
        amount = max(float(event.get("amount", 0)), 0)
        after_years = max(float(event.get("after_years", 0)), 0)
        if amount > 0 and after_years > 0:
            month = min(max(int(round(after_years * 12)), 1), total_months)
            event_map[month] = event_map.get(month, 0) + amount
            normalized_events.append((month, amount))

    recurring_extra = max(float(room_rent_income), 0)
    balance = principal
    schedule = []

    for month in range(1, total_months + 1):
        interest = balance * monthly_rate
        principal_payment = min(base_payment - interest, balance)

        if principal_payment <= 0:
            break

        balance -= principal_payment
        recurring_applied = min(recurring_extra, balance)
        balance -= recurring_applied
        event_applied = min(event_map.get(month, 0), balance)
        balance -= event_applied
        extra_payment = recurring_applied + event_applied

        schedule.append(
            {
                "month": month,
                "payment": interest + principal_payment + extra_payment,
                "interest": interest,
                "principal": principal_payment + extra_payment,
                "extra_payment": extra_payment,
                "balance": max(balance, 0),
            }
        )

        if balance <= 0:
            break

    base_total_interest = sum(row["interest"] for row in base_schedule)
    total_interest = sum(row["interest"] for row in schedule)
    total_extra_payment = sum(row["extra_payment"] for row in schedule)

    return {
        "monthly_payment": base_payment,
        "room_rent_income": recurring_extra,
        "extra_payment_total": total_extra_payment,
        "event_total": sum(amount for _, amount in normalized_events),
        "months": len(schedule),
        "total_interest": total_interest,
        "interest_saved": base_total_interest - total_interest,
        "schedule": schedule,
    }


def simulate_partial_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    repayment_amount: float,
    repayment_after_years: int,
    mode: str,
) -> dict:
    return simulate_partial_repayment_events(
        principal=principal,
        annual_rate=annual_rate,
        years=years,
        repayment_events=[
            {
                "after_years": repayment_after_years,
                "amount": repayment_amount,
            }
        ],
        mode=mode,
    )


def simulate_partial_repayment_events(
    principal: float,
    annual_rate: float,
    years: int,
    repayment_events: list[dict],
    mode: str,
) -> dict:
    base_payment = calculate_monthly_payment(principal, annual_rate, years)
    base_schedule = build_standard_schedule(principal, annual_rate, years, base_payment)
    total_months = years * 12

    normalized_events = []
    for event in repayment_events:
        amount = max(float(event.get("amount", 0)), 0)
        after_years = max(float(event.get("after_years", 0)), 0)
        if amount > 0 and after_years > 0:
            month = min(max(int(round(after_years * 12)), 1), total_months)
            normalized_events.append((month, amount))

    if not normalized_events:
        return {
            "monthly_payment": base_payment,
            "extra_payment_total": 0,
            "months": len(base_schedule),
            "total_interest": sum(row["interest"] for row in base_schedule),
            "interest_saved": 0,
            "schedule": base_schedule,
        }

    event_map: dict[int, float] = {}
    for month, amount in normalized_events:
        event_map[month] = event_map.get(month, 0) + amount

    monthly_rate = annual_rate / 100 / 12
    balance = principal
    schedule = []
    current_payment = base_payment

    for month in range(1, total_months + 1):
        interest = balance * monthly_rate
        principal_payment = min(current_payment - interest, balance)

        if principal_payment <= 0:
            break

        balance -= principal_payment
        extra_payment = 0

        if month in event_map and balance > 0:
            extra_payment = min(event_map[month], balance)
            balance -= extra_payment

        schedule.append(
            {
                "month": month,
                "payment": interest + principal_payment + extra_payment,
                "interest": interest,
                "principal": principal_payment + extra_payment,
                "extra_payment": extra_payment,
                "balance": max(balance, 0),
            }
        )

        if balance <= 0:
            break

        if mode == "Reduce monthly payment":
            remaining_months = total_months - month
            if remaining_months > 0:
                current_payment = calculate_monthly_payment_for_months(
                    balance,
                    annual_rate,
                    remaining_months,
                )
        else:
            current_payment = base_payment

    base_total_interest = sum(row["interest"] for row in base_schedule)
    total_interest = sum(row["interest"] for row in schedule)
    total_extra_payment = sum(row["extra_payment"] for row in schedule)

    return {
        "monthly_payment": current_payment,
        "extra_payment_total": total_extra_payment,
        "months": len(schedule),
        "total_interest": total_interest,
        "interest_saved": base_total_interest - total_interest,
        "schedule": schedule,
    }
