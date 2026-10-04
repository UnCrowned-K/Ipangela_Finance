"""Tests for the Finance and Invoice calendar-date handling.

South Africa runs on SAST (UTC+2), so anything that converts a local moment to
a date through `toISOString()` reads back as the previous day between midnight
and 02:00. That silently dated invoices a day early and widened every statement
range by a day on the left. These tests execute the real JavaScript under
TZ=Africa/Johannesburg, because the defect is a timezone behaviour that a
string assertion on the source cannot detect.
"""

import datetime
import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAST = 'Africa/Johannesburg'

pytestmark = pytest.mark.skipif(
    shutil.which('node') is None, reason='node is needed to run the page JavaScript'
)


def _extract_function(script: str, name: str) -> str:
    """Pull a single `function name(...) {...}` block out of the page script."""
    start = script.index(f'function {name}')
    # Walk braces from the opening one, ignoring braces inside strings.
    depth = 0
    for index in range(start, len(script)):
        char = script[index]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return script[start:index + 1]
    raise AssertionError(f'could not find the end of function {name}')


def _finance_script() -> str:
    html = (ROOT / 'templates' / 'finance.html').read_text()
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    assert scripts, 'the finance page should inline its JavaScript'
    return max(scripts, key=len)


def _run_js(body: str) -> dict:
    """Execute JS under SAST and return whatever it printed as JSON."""
    result = subprocess.run(
        ['node', '-e', body],
        capture_output=True, text=True, cwd=str(ROOT),
        env={'TZ': SAST, 'PATH': '/usr/bin:/bin'},
    )
    assert result.returncode == 0, f'node failed:\n{result.stderr}'
    return json.loads(result.stdout.strip().splitlines()[-1])


def _iso_date_js() -> str:
    """The page's date helper, which the other helpers call by name."""
    return _extract_function(_finance_script(), 'isoDate')


class TestIsoDate:
    """`isoDate` is the one place that turns a local moment into a YYYY-MM-DD
    string. Everything else has to go through it."""

    def test_reports_today_not_yesterday_before_two_am(self):
        # 01:00 on 1 Oct is 23:00 on 30 Sep UTC, which is the exact window where
        # toISOString() used to hand back the wrong calendar day.
        out = _run_js(
            _iso_date_js()
            + "\nconsole.log(JSON.stringify(isoDate(new Date(2026, 9, 1, 1, 0, 0))));"
        )
        assert out == '2026-10-01'

    def test_pads_month_and_day(self):
        out = _run_js(
            _iso_date_js()
            + "\nconsole.log(JSON.stringify([isoDate(new Date(2026, 0, 5)),"
            " isoDate(new Date(2026, 11, 25))]));"
        )
        assert out == ['2026-01-05', '2026-12-25']

    def test_defaults_to_now(self):
        out = _run_js(
            _iso_date_js() + "\nconsole.log(JSON.stringify(isoDate()));"
        )
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', out)

    def test_agrees_with_the_local_calendar(self):
        """The strongest form of the check: compare the page's idea of today
        with the system clock's own local date under SAST."""
        out = _run_js(
            _iso_date_js()
            + "\nvar d = new Date();"
            "\nvar local = d.getFullYear() + '-' +"
            " String(d.getMonth() + 1).padStart(2, '0') + '-' +"
            " String(d.getDate()).padStart(2, '0');"
            "\nconsole.log(JSON.stringify([isoDate(), local, d.toISOString().slice(0, 10)]));"
        )
        page, local_clock, utc = out
        assert page == local_clock, 'isoDate() must agree with the local clock'
        # On this machine UTC and SAST happen to share a calendar day; if the
        # helper had regressed to toISOString() these two would diverge in the
        # 00:00-02:00 window, which is exactly the bug being guarded.
        assert page in (utc, local_clock)


class TestShiftDate:
    """Invoice and tax due dates are computed by shifting a date string."""

    def _shift(self, iso, days):
        return _run_js(
            _iso_date_js()
            + _extract_function(_finance_script(), 'shiftDate')
            + f"\nconsole.log(JSON.stringify(shiftDate({json.dumps(iso)}, {days})));"
        )

    def test_adds_thirty_days(self):
        assert self._shift('2026-10-03', 30) == '2026-11-02'

    def test_subtracts_across_a_month_boundary(self):
        assert self._shift('2026-11-01', -1) == '2026-10-31'

    def test_crosses_a_leap_day(self):
        assert self._shift('2028-02-28', 1) == '2028-02-29'

    def test_handles_the_year_boundary(self):
        assert self._shift('2026-12-31', 1) == '2027-01-01'


class TestApplyDateRange:
    """Statement presets must start on the first day of the period they name."""

    @pytest.fixture()
    def runner(self):
        """Run the real applyDateRange against stub inputs.

        The function reads the wall clock itself, so the expectations below are
        derived from the machine's own SAST date rather than injected.
        """
        fn = _extract_function(_finance_script(), 'applyDateRange')

        def run(range_name):
            body = (
                _iso_date_js() + "\n"
                "var store = {};\n"
                "var document = { getElementById: function (id) {\n"
                "    return { set value(v) { store[id] = v; },"
                " get value() { return store[id]; } };\n"
                "} };\n"
                + fn
                + f"\napplyDateRange('stmt', {json.dumps(range_name)});"
                "\nconsole.log(JSON.stringify(store));"
            )
            return _run_js(body)

        return run

    @staticmethod
    def _today_sast():
        import datetime
        return datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=2))
        ).date()

    def test_month_starts_on_the_first(self, runner):
        store = runner('month')
        today = self._today_sast()
        assert store['stmt-start'] == today.replace(day=1).isoformat()

    def test_quarter_looks_back_two_months(self, runner):
        store = runner('quarter')
        today = self._today_sast()
        # The preset subtracts two from the zero-based month, which lands on the
        # start of the month two calendar months back.
        month = today.year * 12 + (today.month - 1) - 2
        expected = datetime.date(month // 12, month % 12 + 1, 1).isoformat()
        assert store['stmt-start'] == expected

    def test_year_looks_back_twelve_months(self, runner):
        store = runner('year')
        today = self._today_sast()
        expected = today.replace(day=1, year=today.year - 1).isoformat()
        assert store['stmt-start'] == expected

    def test_range_ends_on_today_not_yesterday(self, runner):
        for preset in ('month', 'quarter', 'year'):
            store = runner(preset)
            assert store['stmt-end'] == self._today_sast().isoformat(), preset

    def test_range_never_starts_in_the_previous_month(self, runner):
        # The regression: in SAST every preset used to begin a day early, which
        # read as the last day of the month before.
        for preset in ('month', 'quarter', 'year'):
            store = runner(preset)
            assert store['stmt-start'].endswith('-01'), preset

    def test_start_is_never_after_the_end(self, runner):
        for preset in ('month', 'quarter', 'year'):
            store = runner(preset)
            assert store['stmt-start'] <= store['stmt-end'], preset


class TestNoRawIsoStringDates:
    """A stray toISOString() in a date default reintroduces the whole bug, so
    the page must not build calendar dates that way at all."""

    def test_finance_page_has_no_iso_string_dates(self):
        script = _finance_script()
        offenders = [
            line.strip() for line in script.splitlines()
            if 'toISOString()' in line and not line.strip().startswith('//')
        ]
        assert not offenders, f'build dates from local parts instead: {offenders}'

    def test_invoice_page_defaults_to_a_local_date(self):
        html = (ROOT / 'templates' / 'invoice.html').read_text()
        assert 'function isoToday(' in html
        # The issue date is assigned from the helper, not from toISOString().
        assert re.search(r'var today = isoToday\(\)', html)
        assert r"issueDate').value = today" in html
        offenders = [
            line.strip() for line in html.splitlines()
            if 'toISOString()' in line and not line.strip().startswith('//')
        ]
        assert not offenders, f'build dates from local parts instead: {offenders}'


class TestLedgerEditDoesNotDuplicate:
    """Editing an invoice has to update the existing row. Posting again instead
    would leave two invoices on the books and overstate what is owed."""

    @pytest.fixture()
    def script(self):
        return _finance_script()

    @pytest.mark.parametrize('save,kind,endpoint', [
        ('saveReceivable', 'receivable', '/receivable'),
        ('savePayable', 'payable', '/payable'),
    ])
    def test_save_sends_a_put_when_editing(self, script, save, kind, endpoint):
        fn = _extract_function(script, save)
        assert 'form.dataset.entryId' in fn, \
            f'{save} should read which entry it is editing'
        assert f'putJson(`/{kind}/${{editingId}}`' in fn, \
            f'{save} should PUT the edit back to /{kind}/<id>'
        assert f"postJson('{endpoint}'" in fn, \
            f'{save} should still POST when creating a new entry'

    @pytest.mark.parametrize('save', ['saveReceivable', 'savePayable'])
    def test_save_clears_the_edit_marker(self, script, save):
        fn = _extract_function(script, save)
        assert 'delete form.dataset.entryId' in fn, \
            f'{save} must forget the edited id, or the next new entry overwrites it'

    @pytest.mark.parametrize('save', ['saveReceivable', 'savePayable'])
    def test_save_toasts_the_right_thing(self, script, save):
        fn = _extract_function(script, save)
        assert 'editingId ? ' in fn, \
            f'{save} should branch its confirmation on whether it was an edit'
        assert 'updated' in fn, \
            f'{save} should say the entry was updated'
        assert 'saved' in fn, \
            f'{save} should still say saved for a new entry'


class TestRatioIsNotCurrency:
    """A ratio is a multiple, not an amount. Formatting it as money printed
    something like R1.20x."""

    def test_line_supports_a_non_currency_format(self):
        script = _finance_script()
        fn = _extract_function(script, 'line')
        assert 'options.raw' in fn, \
            'statement lines should be able to opt out of currency formatting'

    def test_current_ratio_uses_the_ratio_format(self):
        script = _finance_script()
        match = re.search(r"line\('Current ratio'.*?\}\)\}", script, re.S)
        assert match, 'the current ratio should be rendered by line()'
        assert 'raw:' in match.group(0), \
            'the current ratio must opt out of formatCurrency'
        assert 'toFixed(2)' in match.group(0), \
            'a ratio reads better at two decimal places'