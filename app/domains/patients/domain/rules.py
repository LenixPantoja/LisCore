import calendar
from datetime import date


def calculate_age(date_of_birth: date) -> dict:
    """Calculate patient age in years, months and days from date of birth."""
    today = date.today()
    years = today.year - date_of_birth.year
    months = today.month - date_of_birth.month
    days = today.day - date_of_birth.day

    if days < 0:
        months -= 1
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        days += calendar.monthrange(prev_year, prev_month)[1]

    if months < 0:
        years -= 1
        months += 12

    return {"years": years, "months": months, "days": days}
