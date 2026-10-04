"""Tests for the Finance page markup and its JavaScript wiring.

These cover the page itself rather than the JSON API: that every section is
present and reachable, and that the endpoints the page calls actually exist.
The second check is what stops a renamed or mis-typed route from reaching the
browser, where it would only show up as a failed click.
"""

import pathlib
import re

import pytest

from .conftest import authenticate

SECTIONS = [
    'dashboard', 'position', 'ledger', 'compliance', 'statements',
    'records', 'forecast', 'transactions', 'budgets', 'accounts',
    'reports', 'import-export',
]

MODALS = [
    'contactModal', 'receivableModal', 'paymentModal', 'payableModal',
    'taxModal', 'payrollModal', 'forecastModal',
]

API_BASE = '/api/finance'


def _page_html(client) -> str:
    authenticate(client, 'fin_page_1')
    response = client.get('/finance')
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _inline_script(html: str) -> str:
    """The page's own script block, without the external CDN tags."""
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    assert scripts, 'the finance page should inline its JavaScript'
    return '\n'.join(scripts)


def _route_paths(app) -> set:
    """Blueprint route paths, relative to the API base, with ids flattened."""
    paths = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith(API_BASE):
            continue
        path = rule.rule[len(API_BASE):] or '/'
        path = re.sub(r'<[^>]+>', '{p}', path)
        paths.add(path.rstrip('/') or '/')
    return paths


def _called_paths(script: str) -> set:
    """Endpoints the page builds for the API helpers, relative and flattened."""
    found = set()

    literals = re.findall(
        r"(?:apiRequest|postJson|putJson|deleteAt)\(\s*'([^']+)'", script)
    literals += re.findall(
        r"(?:apiRequest|postJson|putJson|deleteAt)\(\s*`([^`]+)`", script)
    literals += re.findall(r"API_BASE\}/([A-Za-z\-/]*)", script)
    literals += re.findall(r"API_BASE\}/([A-Za-z\-/]*)\$\{", script)

    for raw in literals:
        path = raw.split('?')[0]
        if not path.startswith('/'):
            path = '/' + path
        path = re.sub(r'\$\{[^}]+\}', '{p}', path)
        if '${' in path or not path:
            continue
        found.add(path.rstrip('/') or '/')

    return found


# Some paths are built from a variable that is always one of these values.
# Expanding them keeps the endpoint check exact without listing every route.
DYNAMIC_SEGMENTS = ('receivable', 'payable')


class TestFinancePageMarkup:
    def test_page_loads(self, client, app_instance):
        assert 'finance-nav' in _page_html(client)

    def test_every_section_has_a_container(self, client, app_instance):
        html = _page_html(client)
        for section in SECTIONS:
            assert f'id="{section}-section"' in html, \
                f'missing container for the {section} section'

    def test_every_section_has_a_tab(self, client, app_instance):
        html = _page_html(client)
        for section in SECTIONS:
            assert f'data-section="{section}"' in html, \
                f'missing tab button for the {section} section'

    def test_tabs_cover_exactly_the_sections(self, client, app_instance):
        """A tab pointing at a missing container is a dead control."""
        html = _page_html(client)
        tabs = set(re.findall(r'data-section="([a-z\-]+)"', html))
        assert tabs == set(SECTIONS)

    def test_modals_present(self, client, app_instance):
        html = _page_html(client)
        for modal in MODALS:
            assert f'id="{modal}"' in html, f'missing {modal}'

    def test_forms_declare_validation(self, client, app_instance):
        html = _page_html(client)
        for form in ('contact-form', 'receivable-form', 'payable-form',
                     'payment-form', 'tax-form', 'payroll-form',
                     'forecast-form', 'entity-profile-form'):
            assert f'id="{form}"' in html, f'missing {form}'
            block = html.split(f'id="{form}"', 1)[1].split('>', 1)[0]
            assert 'data-validate' in block, \
                f'{form} should opt into client-side validation'


class TestFinancePageScripts:
    def test_page_defines_show_section(self, client, app_instance):
        script = _inline_script(_page_html(client))
        assert 'function showSection' in script

    def test_tab_click_handlers_resolve(self, client, app_instance):
        """Every inline onclick/onchange must name a defined function."""
        html = _page_html(client)
        script = _inline_script(html)
        called = set(re.findall(r'on(?:click|change)="([A-Za-z0-9_]+)\(', html))
        defined = set(re.findall(
            r'function ([A-Za-z0-9_]+)\s*\(', script))
        missing = sorted(called - defined)
        assert not missing, f'undefined handlers in finance.html: {missing}'

    def test_no_duplicate_function_definitions(self, client, app_instance):
        """Overlapping edits once silently dropped a function; guard it."""
        script = _inline_script(_page_html(client))
        names = re.findall(r'^\s*(?:async )?function ([A-Za-z0-9_]+)\s*\(',
                           script, re.M)
        duplicates = sorted({n for n in names if names.count(n) > 1})
        assert not duplicates, f'duplicate definitions: {duplicates}'

    def test_helpers_the_page_depends_on_exist(self, client, app_instance):
        script = _inline_script(_page_html(client))
        for helper in ('getAccountName', 'getCategoryBadge', 'formatCurrency',
                       'renderCharts', 'escapeHtml', 'showToast'):
            assert re.search(rf'function {helper}\s*\(', script), \
                f'{helper} is called by the page but never defined'

    def test_called_endpoints_all_exist(self, client, app_instance):
        """The check that catches a JS call to a route that was renamed."""
        script = _inline_script(_page_html(client))
        routes = _route_paths(app_instance)

        unknown = []
        for path in sorted(_called_paths(script)):
            if path in routes:
                continue
            # /{p}/{p}/payment resolves once the variable segment is expanded
            expanded = [path.replace('{p}', value, 1)
                        for value in DYNAMIC_SEGMENTS]
            if not any(candidate in routes for candidate in expanded):
                unknown.append(path)

        assert not unknown, (
            f'finance.html calls endpoints the API does not serve: {unknown}')

    def test_seed_schedule_uses_the_seeded_route(self, client, app_instance):
        """Guards the one route that has a GET twin at a shorter path."""
        script = _inline_script(_page_html(client))
        assert "'/tax-schedule/seed'" in script
        assert "'/tax-schedule'" not in script

    def test_user_text_is_escaped_before_rendering(self, client, app_instance):
        """Contact names and descriptions reach innerHTML via innerHTML."""
        script = _inline_script(_page_html(client))
        table = script.split('function renderEntryTable', 1)[1]
        table = table.split('\n        function ', 1)[0]
        assert 'escapeHtml(entry.contact_name)' in table
        assert '${entry.contact_name}' not in table.replace(
            'escapeHtml(entry.contact_name)', '')


class TestFinancePageNavigation:
    """The nav is two tablists deep. Every level has to be wired, or whole
    groups of sections exist but cannot be opened."""

    def test_listener_targets_exist(self, client, app_instance):
        """getElementById(x).addEventListener throws on null and takes the rest
        of the init block with it. A renamed id fails silently in review and
        loudly in the browser."""
        html = _page_html(client)
        script = _inline_script(html)
        receivers = set(re.findall(
            r"getElementById\('([^']+)'\)\s*\n?\s*\.addEventListener", script))
        ids = set(re.findall(r'id="([^"]+)"', html))
        missing = sorted(receivers - ids)
        assert not missing, (
            f'finance.html binds listeners to missing element ids: {missing}')

    def test_query_selector_targets_exist(self, client, app_instance):
        html = _page_html(client)
        script = _inline_script(html)
        selectors = re.findall(
            r"querySelector(?:All)?\('([.#][A-Za-z0-9_-]+)'\)", script)
        ids = set(re.findall(r'id="([^"]+)"', html))
        classes = set()
        for attr in re.findall(r'class="([^"]*)"', html):
            classes.update(c for c in attr.split() if c)
        missing = []
        for selector in set(selectors):
            if selector.startswith('#') and selector[1:] not in ids:
                missing.append(selector)
            elif selector.startswith('.') and selector[1:] not in classes:
                missing.append(selector)
        assert not missing, (
            f'finance.html queries selectors that match nothing: {missing}')

    def test_group_tabs_are_wired(self, client, app_instance):
        """data-group is only useful if something reads it."""
        html = _page_html(client)
        script = _inline_script(html)
        groups = set(re.findall(r'data-group="([a-z\-]+)"', html))
        assert groups, 'the finance nav should group its sections'
        unread = sorted(g for g in groups if f"'{g}'" not in script
                        and f'dataset.group' not in script)
        assert not unread, f'group tabs nothing reads: {unread}'

    def test_every_tab_row_belongs_to_a_declared_group(self, client, app_instance):
        """A tab row with no group behind it can never be revealed."""
        html = _page_html(client)
        groups = set(re.findall(r'data-group="([a-z\-]+)"', html))
        rows = set(re.findall(r'class="section-tabs"[^>]*data-tabs="([a-z\-]+)"',
                              html))
        orphans = sorted(rows - groups)
        assert not orphans, f'tab rows with no group tab: {orphans}'

    def test_every_section_reachable_through_the_nav(self, client, app_instance):
        """Walk the nav as a user would: each group's row must be declared, and
        every section must sit in one of them."""
        html = _page_html(client)
        rows = dict(re.findall(
            r'class="section-tabs"[^>]*data-tabs="([a-z\-]+)"(.*?)</div>', html,
            re.S))
        sections = set(re.findall(r'data-section="([a-z\-]+)"', html))
        reachable = set()
        for body in rows.values():
            reachable.update(re.findall(r'data-section="([a-z\-]+)"', body))
        missing = sorted(sections - reachable)
        assert not missing, f'sections not in any tab row: {missing}'

    def test_tablists_support_arrow_keys(self, client, app_instance):
        """role=tablist promises arrow-key navigation. Without it the row is
        mouse-only."""
        script = _inline_script(_page_html(client))
        for key in ('ArrowRight', 'ArrowLeft', 'Home', 'End'):
            assert key in script, f'tablist should handle {key}'

    def test_every_tabpanel_is_labelled_by_a_real_tab(self, client, app_instance):
        html = _page_html(client)
        ids = set(re.findall(r'id="([^"]+)"', html))
        panels = re.findall(
            r'id="([a-z\-]+-section)"[^>]*role="tabpanel"[^>]*'
            r'aria-labelledby="([^"]+)"', html)
        assert panels, 'the active panel should declare role=tabpanel'
        dangling = sorted(lab for _, lab in panels if lab not in ids)
        assert not dangling, f'aria-labelledby points at missing ids: {dangling}'

    def test_show_section_toggles_the_hidden_attribute(self, client, app_instance):
        """Inactive panels ship with [hidden]. .active outranks it visually, but
        a screen reader still treats visible content as hidden."""
        html = _page_html(client)
        script = _inline_script(html)
        fn = script.split('function showSection', 1)[1]
        fn = fn.split('\n        function ', 1)[0]
        assert 'hidden' in fn, \
            'showSection must clear [hidden] on the panel it opens'

    def test_jumping_to_a_section_also_switches_group(self, client, app_instance):
        """The header shortcut and the dashboard 'View all' button both call
        showSection directly from another group."""
        html = _page_html(client)
        script = _inline_script(html)
        fn = script.split('function showSection', 1)[1]
        fn = fn.split('\n        function ', 1)[0]
        assert 'showGroup' in fn, \
            'showSection should move the group row when the section is in ' \
            'another group'

    def test_switching_group_keeps_the_requested_section(self, client, app_instance):
        """showGroup picks its own first tab by default, which dropped the section
        the caller asked for: jumping to Import/export landed on Tax and payroll."""
        script = _inline_script(_page_html(client))
        fn = script.split('function showSection', 1)[1]
        fn = fn.split('\n        function ', 1)[0]
        assert re.search(r'showGroup\(\s*group\s*,\s*section\s*\)', fn), \
            'showSection should hand the requested section to showGroup'


class TestStickyNavClearance:
    """The top nav and the section nav are both sticky. If the section nav does
    not offset itself, it slides underneath and swallows the clicks meant for
    its own tabs."""

    CSS = pathlib.Path(__file__).resolve().parent.parent / 'static' / 'style.css'

    def test_section_nav_clears_the_top_nav(self):
        css = self.CSS.read_text()
        rule = re.search(r'\.finance-nav\s*\{([^}]*)\}', css)
        assert rule, 'the finance nav rule should exist'
        assert 'position: sticky' in rule.group(1)
        top = re.search(r'top:\s*([^;]+);', rule.group(1))
        assert top, 'a sticky nav needs an explicit top offset'
        assert '--top-nav-h' in top.group(1), \
            f'the section nav sticks at {top.group(1)!r}, which puts it under ' \
            'the equally sticky .top-nav'

    def test_section_nav_stacks_below_the_top_nav(self):
        css = self.CSS.read_text()
        nav = re.search(r'\.top-nav\s*\{([^}]*)\}', css).group(1)
        nav_z = int(re.search(r'z-index:\s*(\d+)', nav).group(1))
        fin = re.search(r'\.finance-nav\s*\{([^}]*)\}', css).group(1)
        fin_z = int(re.search(r'z-index:\s*(\d+)', fin).group(1))
        assert fin_z < nav_z, \
            'the section nav must not paint over the top navigation'

    def test_panels_scroll_clear_of_both_sticky_bars(self):
        css = self.CSS.read_text()
        assert 'scroll-margin-top' in css, \
            'a scrolled-to section would otherwise sit under the sticky navs'