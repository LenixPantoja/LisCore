"""
Formula engine for lab test calculations.

Uses simpleeval for safe expression evaluation.
Variables in formulas are referenced by test code (e.g., "GLU", "HTO").

Supported operators: +, -, *, /, **, %
Supported functions: abs, round, min, max, sqrt, log, log10, pow, ceil, floor
"""

import math
from typing import Optional
from simpleeval import SimpleEval, EvalWithCompoundTypes, NameNotDefined, InvalidExpression


# Allowed math functions exposed inside formula expressions
_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "ROUNDTO": round,       # alias: ROUNDTO(value, decimals) — supports negative decimals
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "pow": math.pow,
    "ceil": math.ceil,
    "floor": math.floor,
}


class FormulaError(Exception):
    """Raised when formula evaluation fails."""


def evaluate_formula(formula: str, variables: dict[str, float]) -> float:
    """
    Evaluate a formula expression using the provided variable values.

    Args:
        formula:   Expression string, e.g. "GLU / HTO * 100"
        variables: Mapping of variable name to numeric value,
                   e.g. {"GLU": 95.0, "HTO": 45.0}

    Returns:
        The numeric result of the evaluated expression.

    Raises:
        FormulaError: If the formula is empty, a variable is missing,
                      or the expression is invalid / unsafe.
    """
    if not formula or not formula.strip():
        raise FormulaError("La fórmula está vacía.")

    evaluator = SimpleEval()
    evaluator.functions = _ALLOWED_FUNCTIONS
    evaluator.names = {k: float(v) for k, v in variables.items()}

    try:
        result = evaluator.eval(formula.strip())
    except NameNotDefined as exc:
        raise FormulaError(f"Variable no encontrada en la fórmula: {exc}") from exc
    except ZeroDivisionError:
        raise FormulaError("División por cero en la fórmula.")
    except InvalidExpression as exc:
        raise FormulaError(f"Expresión inválida: {exc}") from exc
    except Exception as exc:
        raise FormulaError(f"Error al evaluar la fórmula: {exc}") from exc

    if not isinstance(result, (int, float)):
        raise FormulaError("La fórmula no retornó un valor numérico.")

    return float(result)


def validate_formula(formula: str, sample_variables: Optional[dict[str, float]] = None) -> bool:
    """
    Validate that a formula can be evaluated without errors.

    Args:
        formula:          Expression string to validate.
        sample_variables: Optional dict of variable names with dummy values
                          to test the expression. If None, variables default to 1.0.

    Returns:
        True if the formula is valid.

    Raises:
        FormulaError: With a descriptive message when the formula is invalid.
    """
    if not formula or not formula.strip():
        raise FormulaError("La fórmula está vacía.")

    # Extract variable names used in the formula via a dry-run attempt.
    # If sample_variables not provided, supply defaults of 1.0 to catch syntax errors.
    variables = sample_variables or {}

    evaluator = SimpleEval()
    evaluator.functions = _ALLOWED_FUNCTIONS

    # Intercept unknown names so we can assign them 1.0 for validation purposes
    class _FallbackNames(dict):
        def __missing__(self, key: str):
            return 1.0

    evaluator.names = _FallbackNames({k: float(v) for k, v in variables.items()})

    try:
        evaluator.eval(formula.strip())
    except ZeroDivisionError:
        pass  # Acceptable during validation with dummy values
    except InvalidExpression as exc:
        raise FormulaError(f"Expresión inválida: {exc}") from exc
    except Exception as exc:
        raise FormulaError(f"Fórmula inválida: {exc}") from exc

    return True


def apply_formula_to_result(
    formula: str,
    variables: dict[str, float],
    num_decimal_result: Optional[int] = None,
) -> float:
    """
    Evaluate a formula and optionally round the result to a fixed number of decimals.

    Args:
        formula:            Expression string.
        variables:          Variable name → numeric value mapping.
        num_decimal_result: If provided, round result to this many decimal places.

    Returns:
        The (optionally rounded) numeric result.
    """
    result = evaluate_formula(formula, variables)

    if num_decimal_result is not None:
        result = round(result, num_decimal_result)

    return result
