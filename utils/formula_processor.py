"""
Formula processor for lab test results.

Resolves formula variables from other test results using name_abbreviation
as the variable identifier, then delegates evaluation to formula_engine.

Usage example — LDL calculation with formula "COL-HDL-(TRI/5)":

    results = [
        {"name_abbreviation": "COL", "result_value": 200.0},
        {"name_abbreviation": "HDL", "result_value": 50.0},
        {"name_abbreviation": "TRI", "result_value": 150.0},
    ]
    process_formula_for_test(
        formula="COL-HDL-(TRI/5)",
        available_results=results,
        num_decimal_result=2,
    )
    # → 120.0  (200 - 50 - 150/5)
"""

from typing import Optional
from utils.formula_engine import evaluate_formula, FormulaError


class FormulaMissingVariableError(FormulaError):
    """Raised when a required variable is not present in the available results."""


class FormulaInvalidResultError(FormulaError):
    """Raised when a result value cannot be converted to a number."""


def build_variables_from_results(
    available_results: list[dict],
) -> dict[str, float]:
    """
    Build a variable mapping from a list of test result dicts.

    Each dict must contain:
      - ``name_abbreviation``: str  — used as variable name in the formula.
      - ``result_value``     : any  — numeric result of that test.

    Non-numeric or missing ``result_value`` entries are silently skipped;
    the caller will receive a ``FormulaMissingVariableError`` if a required
    variable is absent when the formula is evaluated.

    Args:
        available_results: List of result dicts from the current order/sample.

    Returns:
        Dict mapping name_abbreviation → float value.
    """
    variables: dict[str, float] = {}
    for entry in available_results:
        abbreviation = entry.get("name_abbreviation")
        raw_value = entry.get("result_value")

        if not abbreviation or raw_value is None:
            continue

        try:
            variables[abbreviation] = float(raw_value)
        except (TypeError, ValueError):
            # Result is non-numeric (e.g., qualitative) — skip
            continue

    return variables


def process_formula_for_test(
    formula: str,
    available_results: list[dict],
    num_decimal_result: Optional[int] = None,
) -> float:
    """
    Resolve formula variables from other test results and evaluate the formula.

    Args:
        formula:            Expression string using name_abbreviation as
                            variable names (e.g., "COL-HDL-(TRI/5)").
        available_results:  List of result dicts for the current order/sample.
                            Each dict needs ``name_abbreviation`` and
                            ``result_value`` keys.
        num_decimal_result: If provided, rounds the result to this many
                            decimal places.

    Returns:
        The computed numeric result (optionally rounded).

    Raises:
        FormulaMissingVariableError: If any variable in the formula cannot
                                     be resolved from the available results.
        FormulaError:               For any other evaluation error.
    """
    variables = build_variables_from_results(available_results)

    try:
        result = evaluate_formula(formula, variables)
    except FormulaError as exc:
        # Re-raise with context; wrap missing-variable errors with a clearer type
        error_message = str(exc)
        if "Variable no encontrada" in error_message:
            raise FormulaMissingVariableError(error_message) from exc
        raise

    if num_decimal_result is not None:
        result = round(result, num_decimal_result)

    return result


def resolve_formula_variables(
    formula: str,
    available_results: list[dict],
) -> dict[str, float]:
    """
    Return only the variables that are actually referenced in the formula.

    Useful for debugging or displaying which inputs a formula depends on.

    Args:
        formula:           Expression string.
        available_results: List of result dicts.

    Returns:
        Subset of ``build_variables_from_results`` limited to used variables.
    """
    all_variables = build_variables_from_results(available_results)

    # Determine which variable names appear in the formula string
    used = {name: value for name, value in all_variables.items() if name in formula}
    return used
