from dataclasses import asdict

import pandas as pd
import plotly.express as px

from models import RepaymentEvent, ScheduleRow


def build_upfront_cost_fig(initial_costs: pd.DataFrame):
    fig = px.pie(
        initial_costs[initial_costs["Amount"] > 0],
        names="Cost",
        values="Amount",
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def build_room_break_even_fig(room_scenarios: pd.DataFrame):
    fig = px.bar(
        room_scenarios,
        x="rooms",
        y="cashflow",
        text="cashflow",
        color="cashflow",
        color_continuous_scale=["#b91c1c", "#f59e0b", "#15803d"],
        labels={"rooms": "Rooms", "cashflow": "Monthly cashflow"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#111827")
    fig.update_traces(texttemplate="€%{text:.0f}", textposition="outside")
    fig.update_layout(showlegend=False, yaxis_tickprefix="€")
    return fig


def build_scenario_heatmap_fig(
    scenario_df: pd.DataFrame,
    scenario_returns: list[float],
    scenario_shares: list[int],
):
    scenario_heatmap = scenario_df.pivot(
        index="Alternative return",
        columns="Repayment share",
        values="Total value vs best model",
    ).reindex(index=scenario_returns, columns=scenario_shares)
    scenario_heatmap_limit = max(
        abs(scenario_heatmap.min().min()),
        abs(scenario_heatmap.max().max()),
    )
    if scenario_heatmap_limit == 0:
        scenario_heatmap_limit = 1

    fig = px.imshow(
        scenario_heatmap,
        text_auto=".0f",
        color_continuous_scale=["#b91c1c", "#f8fafc", "#15803d"],
        zmin=-scenario_heatmap_limit,
        zmax=scenario_heatmap_limit,
        labels={
            "x": "Surplus used for repayment (%)",
            "y": "Alternative annual return (%)",
            "color": "Total value vs best model (€)",
        },
        aspect="auto",
    )
    fig.update_layout(
        coloraxis_colorbar_tickprefix="€",
        height=560,
    )
    fig.update_xaxes(type="category")
    fig.update_yaxes(
        tickmode="linear",
        tick0=-12,
        dtick=1,
    )
    return fig


def build_balance_projection_fig(
    base_schedule: list[ScheduleRow],
    combined_schedule: list[ScheduleRow],
    repayment_events: list[RepaymentEvent],
):
    combined_projection = pd.DataFrame(asdict(row) for row in combined_schedule)
    combined_projection["scenario"] = "Combined strategy"
    base_projection = pd.DataFrame(asdict(row) for row in base_schedule)
    base_projection["scenario"] = "Base mortgage"
    balance_projection = pd.concat(
        [base_projection, combined_projection],
        ignore_index=True,
    )
    balance_projection["year"] = balance_projection["month"] / 12

    fig = px.line(
        balance_projection,
        x="year",
        y="balance",
        color="scenario",
        labels={
            "year": "Year",
            "balance": "Remaining debt",
            "scenario": "Scenario",
        },
    )
    for event in repayment_events:
        fig.add_vline(
            x=event.after_years,
            line_dash="dot",
            line_color="#6b7280",
        )
    fig.update_layout(yaxis_tickprefix="€")
    return fig


def build_allocation_curve_fig(allocation_scenario_df: pd.DataFrame):
    fig = px.line(
        allocation_scenario_df,
        x="Repayment share",
        y="Total value vs best model",
        markers=True,
        labels={
            "Repayment share": "Surplus used for repayment (%)",
            "Total value vs best model": "Total value gap vs best split (€)",
        },
    )
    fig.update_layout(yaxis_tickprefix="€")
    fig.add_hline(y=0, line_dash="dot", line_color="#6b7280")
    return fig
