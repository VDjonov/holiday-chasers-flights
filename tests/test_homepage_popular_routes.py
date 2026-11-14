"""Popular routes is the third homepage tab.

A deal refresh rewrites the homepage block from generate_pages. That rewrite
keeps the same crawlable links, updates the cards in place inside the
Popular routes tab, and never moves the block back outside that panel.
"""

import pathlib
import re
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("requests", types.ModuleType("requests"))

import generate_pages

TABS = "<!-- ═══ TABS ═══ -->"
MODAL = "<!-- ═══ BACKEND CONNECT MODAL ═══ -->"


def _hrefs(html):
    match = re.search(
        re.escape(generate_pages.POPULAR_START)
        + r"(.*?)"
        + re.escape(generate_pages.POPULAR_END),
        html,
        re.S,
    )
    block = match.group(1) if match else ""
    return re.findall(r'href="([^"]+)"', block)


def _without_block(html):
    match = generate_pages._popular_match(html)
    if not match:
        raise AssertionError("popular routes block missing")
    stripped = html[:match.start()] + html[match.end():]
    return re.sub(r"\n{3,}", "\n\n", stripped), match.group(0)


def _above_the_tabs(html):
    """The oldest order: the block sits between the hero and the tab bar."""
    stripped, block = _without_block(html)
    return stripped.replace(TABS, block + "\n\n" + TABS, 1)


def _below_the_tabs(html):
    """The previous order: the block sits after both tabs, before the modal."""
    stripped, block = _without_block(html)
    return stripped.replace(MODAL, block + "\n\n" + MODAL, 1)


def _assert_in_panel(test, html, hrefs):
    match = generate_pages._popular_match(html)
    test.assertIsNotNone(match)
    test.assertTrue(generate_pages._popular_is_in_routes_tab(html, match))
    test.assertEqual(_hrefs(html), hrefs)
    test.assertEqual(html.count(generate_pages.POPULAR_START), 1)
    test.assertEqual(html.count('id="tab-routes"'), 1)
    test.assertLess(html.find('id="tab-deals"'), match.start())
    test.assertLess(html.find('id="tab-plan"'), match.start())
    test.assertLess(html.find('id="tab-routes"'), match.start())
    close = html.find("</section>", match.end())
    test.assertGreater(close, match.end())
    test.assertLess(close, html.find(MODAL))
    test.assertIn("<a ", match.group(0))
    test.assertNotIn("<script", match.group(0))
    test.assertIn(
        '<button class="tab-btn active" data-tab="deals">', html)
    test.assertIn(
        '<button class="tab-btn" data-tab="routes">'
        '<span class="tab-ic">🧭</span> Popular routes</button>',
        html,
    )
    test.assertNotIn('class="tab-btn active" data-tab="routes"', html)
    test.assertNotIn('id="tab-routes" class="tab-content active"', html)


class PopularRoutesOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.hrefs = _hrefs(cls.doc)

    def test_live_homepage_keeps_links_inside_the_routes_tab(self):
        self.assertEqual(len(self.hrefs), 23)
        self.assertEqual(len(generate_pages.POPULAR_ROUTES), 23)
        self.assertEqual(
            self.hrefs,
            [href for href, _name, _label, _note in generate_pages.POPULAR_ROUTES],
        )
        bar = re.search(r'<div class="tab-seg">(.*?)</div>', self.doc, re.S)
        self.assertIsNotNone(bar)
        self.assertEqual(
            re.findall(r'data-tab="([^"]+)"', bar.group(1)),
            ["deals", "plan", "routes"],
        )
        _assert_in_panel(self, self.doc, self.hrefs)
        self.assertIn('<section id="tab-deals" class="tab-content active">', self.doc)
        self.assertIn('<section id="tab-routes" class="tab-content">', self.doc)

    def test_refresh_does_not_rewrite_a_page_already_in_the_tab(self):
        self.assertEqual(
            generate_pages.homepage_with_popular_routes(self.doc), self.doc)
        self.assertFalse(generate_pages.popular_routes_will_change())

    def test_refresh_updates_cards_in_place_inside_the_tab(self):
        stale = self.doc.replace("Hand-checked on ryanair.com", "STALE NOTE", 1)
        updated = generate_pages.homepage_with_popular_routes(stale)
        self.assertNotIn("STALE NOTE", updated)
        self.assertIn("Hand-checked on ryanair.com", updated)
        _assert_in_panel(self, updated, self.hrefs)
        self.assertEqual(generate_pages.homepage_with_popular_routes(updated), updated)

    def test_refresh_moves_an_old_block_into_the_tab(self):
        for old in (_below_the_tabs(self.doc), _above_the_tabs(self.doc)):
            old_match = generate_pages._popular_match(old)
            self.assertFalse(
                generate_pages._popular_is_in_routes_tab(old, old_match))
            moved = generate_pages.homepage_with_popular_routes(old)
            self.assertIsNotNone(moved)
            _assert_in_panel(self, moved, self.hrefs)
            self.assertEqual(
                generate_pages.homepage_with_popular_routes(moved), moved)
            # The panel shell stayed put; only the cards moved into it.
            self.assertLess(
                moved.find('id="tab-plan"'),
                moved.find('id="tab-routes"'),
            )

    def test_refresh_does_not_place_the_block_outside_a_missing_panel(self):
        old = _below_the_tabs(self.doc)
        old = re.sub(
            r'\n*<section id="tab-routes" class="tab-content">\s*</section>\n*',
            "\n",
            old,
            count=1,
        )
        self.assertIsNone(generate_pages._routes_tab_open(old))
        self.assertIsNone(generate_pages.homepage_with_popular_routes(old))
        self.assertEqual(old.count(generate_pages.POPULAR_START), 1)


if __name__ == "__main__":
    unittest.main()
