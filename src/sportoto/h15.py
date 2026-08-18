"""H15 V1: option sets, scenarios, filters and audit only."""
from __future__ import annotations

from itertools import product
from typing import Any, Callable, Iterable

VALID = {"1", "X", "2"}


def build_option_sets(decisions: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    output = {}
    for decision in decisions:
        selection = str(decision["selection"])
        options = [value for value in selection if value in VALID]
        if not options or not set(options).issubset(VALID):
            raise ValueError(f"invalid option set for {decision.get('match_id')}")
        output[str(decision["match_id"])] = options
    return output


def generate_scenarios(option_sets: dict[str, list[str]]) -> list[dict[str, str]]:
    if not option_sets:
        raise ValueError("option sets cannot be empty")
    match_ids = list(option_sets)
    return [dict(zip(match_ids, values)) for values in product(*(option_sets[mid] for mid in match_ids))]


def apply_filters(scenarios: list[dict[str, str]], filters: Iterable[tuple[str, Callable[[dict[str, str]], bool]]]) -> tuple[list[dict[str, str]], list[dict[str, int | str]]]:
    current = list(scenarios)
    audit = []
    for name, predicate in filters:
        before = len(current)
        current = [scenario for scenario in current if predicate(scenario)]
        audit.append({"filter": name, "before": before, "after": len(current), "removed": before - len(current)})
    return current, audit


def actual_audit(all_scenarios: list[dict[str, str]], filtered_scenarios: list[dict[str, str]], actual: dict[str, str] | None = None, filters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if actual is None:
        return {"actual_result": None, "actual_in_all_scenarios": None, "actual_in_filtered": None, "eliminated_by": None}
    if set(actual.values()) - VALID:
        raise ValueError("actual outcomes must be 1, X or 2")
    in_all = actual in all_scenarios
    in_filtered = actual in filtered_scenarios
    eliminated_by = None
    if in_all and not in_filtered and filters:
        for item in filters:
            if item["after"] < item["before"]:
                eliminated_by = item["filter"]
                break
    return {"actual_result": actual, "actual_in_all_scenarios": in_all, "actual_in_filtered": in_filtered, "eliminated_by": eliminated_by}


def build_coupon_state(decisions: Iterable[dict[str, Any]], filters: Iterable[tuple[str, Callable[[dict[str, str]], bool]]] = (), actual: dict[str, str] | None = None) -> dict[str, Any]:
    option_sets = build_option_sets(decisions)
    all_scenarios = generate_scenarios(option_sets)
    filtered, filter_audit = apply_filters(all_scenarios, filters)
    return {"option_sets": option_sets, "scenario_count": len(all_scenarios), "filters": filter_audit,
            "filtered_scenario_count": len(filtered), "selected_scenarios": filtered,
            "portfolio": {"target_size": None, "coverage": None},
            "audit": actual_audit(all_scenarios, filtered, actual, filter_audit)}


__all__ = ["actual_audit", "apply_filters", "build_coupon_state", "build_option_sets", "generate_scenarios"]
