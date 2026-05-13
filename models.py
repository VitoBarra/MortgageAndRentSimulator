from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    month: int
    payment: float
    interest: float
    principal: float
    balance: float
    extra_payment: float = 0


@dataclass(frozen=True, slots=True)
class RepaymentResult:
    monthly_payment: float
    months: int
    total_interest: float
    interest_saved: float
    schedule: list[ScheduleRow]
    extra_payment: float = 0
    room_rent_income: float = 0
    extra_payment_total: float = 0
    event_total: float = 0


@dataclass(frozen=True, slots=True)
class PurchaseInputs:
    house_price: float
    mortgage_percent: float
    annual_rate: float
    years: int
    amortization_method: str

    @property
    def mortgage_amount(self) -> float:
        return self.house_price * self.mortgage_percent / 100

    @property
    def down_payment(self) -> float:
        return self.house_price - self.mortgage_amount


@dataclass(frozen=True, slots=True)
class PurchaseCosts:
    notary: float
    istruttoria: float
    appraisal: float
    agency: float
    purchase_taxes: float
    renovation: float
    other_initial: float

    @property
    def total(self) -> float:
        return (
            self.notary
            + self.istruttoria
            + self.appraisal
            + self.agency
            + self.purchase_taxes
            + self.renovation
            + self.other_initial
        )

    def rows(self, down_payment: float) -> list[tuple[str, float]]:
        return [
            ("Down payment", down_payment),
            ("Notary", self.notary),
            ("Istruttoria", self.istruttoria),
            ("Perizia", self.appraisal),
            ("Agency", self.agency),
            ("Purchase taxes", self.purchase_taxes),
            ("Renovation", self.renovation),
            ("Other initial costs", self.other_initial),
        ]


@dataclass(frozen=True, slots=True)
class RentVsInterestInputs:
    current_monthly_rent: float
    current_cash_available: float
    monthly_saving_after_rent: float
    monthly_saving_if_buy_now: float
    cash_purchase_target: float
    mortgage_interest: float
    house_price_growth_rate: float = 0
    savings_return_rate: float = 0


@dataclass(frozen=True, slots=True)
class RentVsInterestResult:
    remaining_cash_to_save: float
    months_to_cash_purchase: float | None
    future_cash_purchase_target: float | None
    saved_cash_at_purchase: float | None
    rent_paid_while_waiting: float | None
    buy_now_savings_while_waiting: float | None
    buy_now_advantage_vs_waiting: float | None
    rent_equivalent_years: float | None
    rent_minus_interest: float | None


@dataclass(frozen=True, slots=True)
class RentalInputs:
    rooms: int
    room_prices: list[float]
    occupancy_rate: float
    rental_tax_rate: float
    condo_costs: float
    maintenance: float
    other_costs: float

    @property
    def monthly_costs(self) -> float:
        return self.condo_costs + self.maintenance + self.other_costs


@dataclass(frozen=True, slots=True)
class RentalResult:
    gross_rent: float
    net_rent: float
    monthly_costs: float
    cashflow_before_costs: float
    cashflow_after_costs: float


@dataclass(frozen=True, slots=True)
class RepaymentEvent:
    after_years: float
    amount: float

    @classmethod
    def from_mapping(cls, event: dict) -> "RepaymentEvent":
        return cls(
            after_years=max(float(event.get("after_years", 0)), 0),
            amount=max(float(event.get("amount", 0)), 0),
        )


@dataclass(frozen=True, slots=True)
class AllocationInputs:
    mortgage_amount: float
    annual_rate: float
    years: int
    amortization_method: str
    monthly_expendable_cashflow: float
    net_rent: float
    monthly_costs: float
    repayment_share: int
    alternative_return: float
    analysis_horizon_years: int
    repayment_events: list[RepaymentEvent]


@dataclass(frozen=True, slots=True)
class AllocationResult:
    repayment_share: int
    investment_share: int
    alternative_return: float
    repayment_result: RepaymentResult
    payoff_months: int
    analysis_horizon_months: int
    pre_payoff_months: int
    post_payoff_months: int
    recurring_extra_principal: float
    monthly_investment: float
    post_payoff_monthly_investment: float
    pre_payoff_future_value: float
    post_payoff_future_value: float
    strategy_future_value: float
    early_repayment_benefit: float
    total_strategy_value: float
