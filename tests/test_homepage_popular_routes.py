"""Popular routes stays below the deal board and Plan a trip.

A deal refresh rewrites the homepage block from generate_pages. That rewrite
must keep the same crawlable links and must not put the block back above the
tabs.
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


def _above_the_tabs(html):
    """The old order: the block sits between the hero and the tab bar."""
    match = generate_pages._popular_match(html)
    if not match:
        raise AssertionError("popular routes block missing")
    block = match.group(0)
    stripped = html[:match.start()] + html[match.end():]
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.replace(TABS, block + "\n\n" + TABS, 1)


class PopularRoutesOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.hrefs = _hrefs(cls.doc)

    def test_live_homepage_keeps_links_below_both_tabs(self):
        self.assertEqual(len(self.hrefs), len(generate_pages.POPULAR_ROUTES))
        self.assertEqual(
            self.hrefs,
            [href for href, _name, _label, _note in generate_pages.POPULAR_ROUTES],
        )
        match = generate_pages._popular_match(self.doc)
        self.assertIsNotNone(match)
        self.assertTrue(generate_pages._popular_is_below_tabs(self.doc, match))
        self.assertLess(self.doc.find('id="tab-deals"'), match.start())
        self.assertLess(self.doc.find('id="tab-plan"'), match.start())
        self.assertIn("<a ", match.group(0))
        self.assertNotIn("<script", match.group(0))

    def test_refresh_does_not_rewrite_a_page_already_in_order(self):
        self.assertEqual(
            generate_pages.homepage_with_popular_routes(self.doc), self.doc)
        self.assertFalse(generate_pages.popular_routes_will_change())

    def test_refresh_moves_an_old_block_back_below_the_tabs(self):
        old = _above_the_tabs(self.doc)
        old_match = generate_pages._popular_match(old)
        self.assertFalse(generate_pages._popular_is_below_tabs(old, old_match))
        moved = generate_pages.homepage_with_popular_routes(old)
        self.assertIsNotNone(moved)
        moved_match = generate_pages._popular_match(moved)
        self.assertTrue(generate_pages._popular_is_below_tabs(moved, moved_match))
        self.assertEqual(_hrefs(moved), self.hrefs)
        self.assertEqual(generate_pages.homepage_with_popular_routes(moved), moved)
        self.assertLess(moved.find('id="tab-plan"'), moved_match.start())
        self.assertLess(
            moved_match.end(), moved.find(generate_pages.POPULAR_ANCHOR))


if __name__ == "__main__":
    unittest.main()
