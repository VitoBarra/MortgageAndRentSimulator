from models import RepaymentEvent, RepaymentResult, ScheduleRow


FRENCH_AMORTIZATION = "French amortization"
ITALIAN_AMORTIZATION = "Italian amortization"
AMORTIZATION_METHODS = (FRENCH_AMORTIZATION, ITALIAN_AMORTIZATION)


def normalize_amortization_method(method: str | None) -> str:
    if method in AMORTIZATION_METHODS:
        return method
    return FRENCH_AMORTIZATION


def calculate_monthly_payment(
    principal: float,
    annual_rate: float,
    years: int,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> float:
    return calculate_monthly_payment_for_months(
        principal,
        annual_rate,
        years * 12,
        amortization_method,
    )


def calculate_monthly_payment_for_months(
    principal: float,
    annual_rate: float,
    months: int,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> float:
    if principal <= 0:
        return 0
    if months <= 0:
        return principal

    monthly_rate = annual_rate / 100 / 12
    method = normalize_amortization_method(amortization_method)

    if method == ITALIAN_AMORTIZATION:
        constant_principal = principal / months
        return constant_principal + principal * monthly_rate

    if monthly_rate == 0:
        return principal / months

    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def calculate_total_interest(
    principal: float,
    annual_rate: float,
    years: int,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> float:
    return sum(
        row.interest
        for row in build_standard_schedule(
            principal,
            annual_rate,
            years,
            amortization_method=amortization_method,
        )
    )


def _build_schedule_with_extra_payment(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_payment: float,
    extra_monthly_payment: float = 0,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> list[ScheduleRow]:
    if principal <= 0:
        return []

    monthly_rate = annual_rate / 100 / 12
    method = normalize_amortization_method(amortization_method)
    constant_principal = principal / (years * 12)
    balance = principal
    schedule = []

    for month in range(1, years * 12 + 1):
        interest = balance * monthly_rate
        if method == ITALIAN_AMORTIZATION:
            principal_payment = min(constant_principal, balance)
        else:
            principal_payment = min(monthly_payment - interest, balance)

        if principal_payment <= 0:
            break

        balance -= principal_payment
        recurring_applied = min(extra_monthly_payment, balance)
        balance -= recurring_applied
        schedule.append(
            ScheduleRow(
                month=month,
                payment=interest + principal_payment + recurring_applied,
                interest=interest,
                principal=principal_payment + recurring_applied,
                extra_payment=recurring_applied,
                balance=max(balance, 0),
            )
        )

        if balance <= 0:
            break

    return schedule


def build_standard_schedule(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_payment: float | None = None,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> list[ScheduleRow]:
    monthly_payment = monthly_payment or calculate_monthly_payment(
        principal,
        annual_rate,
        years,
        amortization_method,
    )
    return _build_schedule_with_extra_payment(
        principal,
        annual_rate,
        years,
        monthly_payment,
        amortization_method=amortization_method,
    )


def simulate_room_rent_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    room_rent_income: float,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> RepaymentResult:
    base_payment = calculate_monthly_payment(
        principal,
        annual_rate,
        years,
        amortization_method,
    )
    base_schedule = build_standard_schedule(
        principal,
        annual_rate,
        years,
        base_payment,
        amortization_method,
    )
    extra_payment = max(room_rent_income, 0)
    schedule = _build_schedule_with_extra_payment(
        principal,
        annual_rate,
        years,
        base_payment,
        extra_payment,
        amortization_method,
    )

    base_total_interest = sum(row.interest for row in base_schedule)
    total_interest = sum(row.interest for row in schedule)

    return RepaymentResult(
        monthly_payment=base_payment + extra_payment,
        extra_payment=extra_payment,
        months=len(schedule),
        total_interest=total_interest,
        interest_saved=base_total_interest - total_interest,
        schedule=schedule,
    )


def _event_amount(event: dict | RepaymentEvent) -> float:
    if isinstance(event, RepaymentEvent):
        return max(float(event.amount), 0)
    return max(float(event.get("amount", 0)), 0)


def _event_after_years(event: dict | RepaymentEvent) -> float:
    if isinstance(event, RepaymentEvent):
        return max(float(event.after_years), 0)
    return max(float(event.get("after_years", 0)), 0)


def simulate_combined_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    room_rent_income: float,
    repayment_events: list[dict | RepaymentEvent],
    amortization_method: str = FRENCH_AMORTIZATION,
) -> RepaymentResult:
    base_payment = calculate_monthly_payment(
        principal,
        annual_rate,
        years,
        amortization_method,
    )
    base_schedule = build_standard_schedule(
        principal,
        annual_rate,
        years,
        base_payment,
        amortization_method,
    )
    total_months = years * 12
    monthly_rate = annual_rate / 100 / 12
    method = normalize_amortization_method(amortization_method)
    constant_principal = principal / total_months

    event_map: dict[int, float] = {}
    normalized_events = []
    for event in repayment_events:
        amount = _event_amount(event)
        after_years = _event_after_years(event)
        if amount > 0 and after_years > 0:
            month = min(max(int(round(after_years * 12)), 1), total_months)
            event_map[month] = event_map.get(month, 0) + amount
            normalized_events.append((month, amount))

    recurring_extra = max(float(room_rent_income), 0)
    balance = principal
    schedule = []

    for month in range(1, total_months + 1):
        interest = balance * monthly_rate
        if method == ITALIAN_AMORTIZATION:
            principal_payment = min(constant_principal, balance)
        else:
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
            ScheduleRow(
                month=month,
                payment=interest + principal_payment + extra_payment,
                interest=interest,
                principal=principal_payment + extra_payment,
                extra_payment=extra_payment,
                balance=max(balance, 0),
            )
        )

        if balance <= 0:
            break

    base_total_interest = sum(row.interest for row in base_schedule)
    total_interest = sum(row.interest for row in schedule)
    total_extra_payment = sum(row.extra_payment for row in schedule)

    return RepaymentResult(
        monthly_payment=base_payment,
        room_rent_income=recurring_extra,
        extra_payment_total=total_extra_payment,
        event_total=sum(amount for _, amount in normalized_events),
        months=len(schedule),
        total_interest=total_interest,
        interest_saved=base_total_interest - total_interest,
        schedule=schedule,
    )


def simulate_partial_repayment(
    principal: float,
    annual_rate: float,
    years: int,
    repayment_amount: float,
    repayment_after_years: int,
    mode: str,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> RepaymentResult:
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
        amortization_method=amortization_method,
    )


def simulate_partial_repayment_events(
    principal: float,
    annual_rate: float,
    years: int,
    repayment_events: list[dict | RepaymentEvent],
    mode: str,
    amortization_method: str = FRENCH_AMORTIZATION,
) -> RepaymentResult:
    base_payment = calculate_monthly_payment(
        principal,
        annual_rate,
        years,
        amortization_method,
    )
    base_schedule = build_standard_schedule(
        principal,
        annual_rate,
        years,
        base_payment,
        amortization_method,
    )
    total_months = years * 12
    method = normalize_amortization_method(amortization_method)
    base_principal_payment = principal / total_months

    normalized_events = []
    for event in repayment_events:
        amount = _event_amount(event)
        after_years = _event_after_years(event)
        if amount > 0 and after_years > 0:
            month = min(max(int(round(after_years * 12)), 1), total_months)
            normalized_events.append((month, amount))

    if not normalized_events:
        return RepaymentResult(
            monthly_payment=base_payment,
            extra_payment_total=0,
            months=len(base_schedule),
            total_interest=sum(row.interest for row in base_schedule),
            interest_saved=0,
            schedule=base_schedule,
        )

    event_map: dict[int, float] = {}
    for month, amount in normalized_events:
        event_map[month] = event_map.get(month, 0) + amount

    monthly_rate = annual_rate / 100 / 12
    balance = principal
    schedule = []
    current_payment = base_payment

    for month in range(1, total_months + 1):
        interest = balance * monthly_rate
        if method == ITALIAN_AMORTIZATION:
            principal_payment = min(base_principal_payment, balance)
        else:
            principal_payment = min(current_payment - interest, balance)

        if principal_payment <= 0:
            break

        balance -= principal_payment
        extra_payment = 0

        if month in event_map and balance > 0:
            extra_payment = min(event_map[month], balance)
            balance -= extra_payment

        schedule.append(
            ScheduleRow(
                month=month,
                payment=interest + principal_payment + extra_payment,
                interest=interest,
                principal=principal_payment + extra_payment,
                extra_payment=extra_payment,
                balance=max(balance, 0),
            )
        )

        if balance <= 0:
            break

        if mode == "Reduce monthly payment" and method == FRENCH_AMORTIZATION:
            remaining_months = total_months - month
            if remaining_months > 0:
                current_payment = calculate_monthly_payment_for_months(
                    balance,
                    annual_rate,
                    remaining_months,
                    amortization_method,
                )
        else:
            current_payment = base_payment

    base_total_interest = sum(row.interest for row in base_schedule)
    total_interest = sum(row.interest for row in schedule)
    total_extra_payment = sum(row.extra_payment for row in schedule)

    return RepaymentResult(
        monthly_payment=current_payment,
        extra_payment_total=total_extra_payment,
        months=len(schedule),
        total_interest=total_interest,
        interest_saved=base_total_interest - total_interest,
        schedule=schedule,
    )
