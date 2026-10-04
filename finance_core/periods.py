"""Date and financial-period helpers.

South African tax years and SARS filing cycles run from 1 March to the end of
February, so period arithmetic is written against a configurable *year-end
month* rather than hardcoded calendar years. Every value produced here is a
planning default: SARS deadlines are set by the Income Tax Act and the VAT
Act and can change, so callers should present them as "due dates to confirm"
with the user's tax practitioner rather than as authoritative filing dates.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Iterator, Union

#: Standard VAT rate in South Africa.
DEFAULT_VAT_RATE = 0.15

#: Month numbers (1-12) for the supported VAT submission intervals.
VAT_INTERVAL_MONTHS = {
    'monthly': 1,
    'bi_monthly': 2,
    'quarterly': 3,
    'four_monthly': 4,
}

MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]

#: SARS tax year runs 1 March - 28/29 February, so the year ends in February.
DEFAULT_YEAR_END_MONTH = 2

DateLike = Union[str, date, datetime, None]


def today() -> date:
    """Return today's date."""
    return date.today()


def parse_date(value: DateLike, field_name: str = 'date') -> Optional[date]:
    """Parse an ISO date or datetime string into a ``date``.

    Returns ``None`` for empty input. Raises ``ValueError`` on unparseable or
    out-of-order values, e.g. a period where the end precedes the start.
    """
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError(f"Invalid {field_name}: must be in YYYY-MM-DD format")


def to_iso(value: DateLike) -> Optional[str]:
    """Render a date-like value as an ISO ``YYYY-MM-DD`` string."""
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else None


def require_date(value: DateLike, field_name: str = 'date') -> date:
    """Parse a date that must be present."""
    parsed = parse_date(value, field_name)
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def require_range(start: DateLike, end: DateLike,
                  start_name: str = 'start_date',
                  end_name: str = 'end_date') -> Tuple[date, date]:
    """Parse an inclusive date range and reject an end before the start."""
    start_date = require_date(start, start_name)
    end_date = require_date(end, end_name)
    if end_date < start_date:
        raise ValueError(f"{end_name} cannot be earlier than {start_name}")
    return start_date, end_date


def days_in_month(year: int, month: int) -> int:
    """Number of days in a given month (handles February in leap years)."""
    return calendar.monthrange(year, month)[1]


def month_end(value: DateLike) -> date:
    """Last calendar day of the month containing ``value``."""
    d = require_date(value)
    return date(d.year, d.month, days_in_month(d.year, d.month))


def add_days(value: DateLike, days: int) -> date:
    """Add (or subtract) whole days."""
    return require_date(value) + timedelta(days=days)


def add_months(value: DateLike, months: int) -> date:
    """Add whole months, clamping to the last valid day of the target month.

    So 31 January plus one month is 28/29 February rather than 2 or 3 March,
    which keeps month-end invoices and period ends from drifting.
    """
    d = require_date(value)
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(d.day, days_in_month(year, month)))


def month_start(value: DateLike) -> date:
    """First calendar day of the month containing ``value``."""
    d = require_date(value)
    return date(d.year, d.month, 1)


def _year_end_for(d: date, year_end_month: int) -> int:
    """Calendar year in which the year containing ``d`` closes."""
    return d.year if d.month <= year_end_month else d.year + 1


def financial_year_bounds(reference: DateLike = None,
                          year_end_month: int = DEFAULT_YEAR_END_MONTH
                          ) -> Tuple[date, date]:
    """Return the (start, end) of the financial year containing ``reference``.

    For the default February year end this yields 1 March - 28/29 February,
    which is also the South African tax year. Pass a different
    ``year_end_month`` (1-12) to support businesses with other year ends.
    """
    if not 1 <= int(year_end_month) <= 12:
        raise ValueError("year_end_month must be between 1 and 12")
    ref = parse_date(reference) or today()
    year_end_month = int(year_end_month)

    end_year = _year_end_for(ref, year_end_month)
    end = date(end_year, year_end_month, days_in_month(end_year, year_end_month))

    start_month = (year_end_month % 12) + 1
    start_year = end_year - 1 if year_end_month < 12 else end_year
    start = date(start_year, start_month, 1)
    return start, end


def tax_year_bounds(reference: DateLike = None) -> Tuple[date, date]:
    """South African tax year (1 March - end of February) around ``reference``."""
    return financial_year_bounds(reference, DEFAULT_YEAR_END_MONTH)


def financial_year_label(start: date, end: date) -> str:
    """Human label for a financial year, e.g. "2026/03 - 2027/02"."""
    return f"{start:%Y/%m} - {end:%Y/%m}"


def iter_months(start: DateLike, count: int) -> Iterator[date]:
    """Yield the first day of each of ``count`` months from ``start``."""
    if count < 0:
        raise ValueError("count cannot be negative")
    cursor = month_start(start)
    for _ in range(count):
        yield cursor
        cursor = add_months(cursor, 1)


def month_key(value: DateLike) -> str:
    """``YYYY-MM`` bucket key for a date, matching transaction bucketing."""
    return f"{require_date(value):%Y-%m}"


def months_in_range(start: DateLike, end: DateLike) -> int:
    """Count of calendar months touched by an inclusive range (at least 1)."""
    first = month_start(start)
    last = month_start(end)
    if last < first:
        raise ValueError("end_date cannot be earlier than start_date")
    return (last.year - first.year) * 12 + (last.month - first.month) + 1


def last_day_business_safe(value: DateLike) -> date:
    """Approximate a month-end filing date.

    SARS accepts returns up to the last *business* day; this nudges a
    Saturday or Sunday deadline back to the preceding Friday so the stored
    due date never falls on a non-working day. Callers should still confirm
    the exact date with SARS.
    """
    end = month_end(value)
    while end.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        end -= timedelta(days=1)
    return end


def vat_periods(year_end_month: int = DEFAULT_YEAR_END_MONTH,
                interval: str = 'monthly',
                reference: DateLike = None) -> List[dict]:
    """Generate VAT submission periods for one financial year.

    Periods are aligned to the start of the financial year (1 March by
    default) the way SARS aligns VAT submissions, and each period is due on
    the last business day of the following month.
    """
    if interval not in VAT_INTERVAL_MONTHS:
        raise ValueError(
            f"Invalid vat interval: must be one of {', '.join(VAT_INTERVAL_MONTHS)}"
        )
    step = VAT_INTERVAL_MONTHS[interval]
    year_start, year_end = financial_year_bounds(reference, year_end_month)

    periods: List[dict] = []
    cursor = year_start
    while cursor <= year_end:
        # A step of 1 means the single month that starts at `cursor`, so step
        # forward by (step - 1) months and close the period on its last day.
        period_end = min(
            month_end(add_months(cursor, step - 1)),
            year_end,
        )
        # SARS accepts a return up to the last business day of the next month.
        due = last_day_business_safe(add_months(period_end, 1))
        periods.append({
            'period_start': cursor.isoformat(),
            'period_end': period_end.isoformat(),
            'due_date': due.isoformat(),
            'interval': interval,
        })
        cursor = add_months(cursor, step)
    return periods


def provisional_tax_deadline(year_end: DateLike) -> date:
    """Provisional tax return deadline: seven months after the year end.

    For a tax year ending 28 February 2026 this returns 30 September 2026.
    """
    return add_months(year_end, 7)


def annual_return_deadline(year_end: DateLike) -> date:
    """Income tax return deadline: within twelve months of the year end.

    Returns the last day of the twelfth month after the year end, e.g. 28
    February 2027 for a 28 February 2026 year end.
    """
    return month_end(add_months(year_end, 12))


def provisional_tax_periods(year_end_month: int = DEFAULT_YEAR_END_MONTH,
                            reference: DateLike = None,
                            periods_per_year: int = 2) -> List[dict]:
    """Build provisional tax periods (SA allows at least two per year).

    Each due date is seven months after the period end, the outer bound that
    also covers the final return for the year.
    """
    if periods_per_year < 2:
        raise ValueError("South African provisional tax requires at least 2 periods per year")
    year_start, year_end = financial_year_bounds(reference, year_end_month)
    months = max(1, months_in_range(year_start, year_end) // periods_per_year)

    periods: List[dict] = []
    cursor = year_start
    while cursor <= year_end:
        # Close the period on the last day of its final month so consecutive
        # periods tile the year without overlapping or leaving a day out.
        period_end = min(month_end(add_months(cursor, months - 1)), year_end)
        periods.append({
            'period_start': cursor.isoformat(),
            'period_end': period_end.isoformat(),
            'due_date': provisional_tax_deadline(period_end).isoformat(),
        })
        cursor = add_months(cursor, months)
    return periods


def describe_period(start: DateLike, end: DateLike) -> str:
    """Short human label for a date range, collapsing same-month ranges."""
    s, e = require_range(start, end)
    if s.year == e.year and s.month == e.month:
        return f"{MONTH_NAMES[s.month]} {s.year}"
    if s.year == e.year:
        return f"{s:%d %b} - {e:%d %b %Y}"
    return f"{s:%d %b %Y} - {e:%d %b %Y}"
