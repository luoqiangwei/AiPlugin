#!/usr/bin/env python3
"""Meaningful navigation-tree invariants, independent of the live site."""

import unittest
from sidebar_inventory import SidebarParser, annotate, walk


class SidebarTests(unittest.TestCase):
    def parse(self, html):
        p = SidebarParser("https://source.android.com/docs/core/architecture")
        p.feed(html)
        return p

    def test_collapsed_heading_retains_descendants_and_only_one_menu(self):
        html = '''<ul menu="_book"><li class="devsite-nav-expandable">
        <div role="button"><span class="devsite-nav-text">Kernel</span></div>
        <ul hidden><li><a href="/docs/core/architecture/kernel/gki?hl=zh-cn#intro">
        <span class="devsite-nav-text">GKI <b>modules</b><br/></span></a></li></ul>
        </li></ul><ul menu="_book"><li><span class="devsite-nav-text">Duplicate</span></li></ul>'''
        p = self.parse(html)
        self.assertTrue(p.finished)
        self.assertEqual(len(list(walk(p.tree))), 2)
        self.assertEqual(p.tree[0]["label"], "Kernel")
        self.assertIsNone(p.tree[0]["url"])
        self.assertEqual(p.tree[0]["children"][0]["label"], "GKI modules")
        self.assertEqual(p.tree[0]["children"][0]["url"],
                         "https://source.android.com/docs/core/architecture/kernel/gki")

    def test_longest_route_and_direct_provenance_are_separate_from_depth(self):
        p = self.parse('''<ul menu="_book"><li><span class="devsite-nav-text">Architecture</span>
          <ul><li><a href="/docs/core/architecture/kernel/gki"><span class="devsite-nav-text">GKI</span></a></li>
          <li><a href="/docs/core/new"><span class="devsite-nav-text">New</span></a></li></ul></li></ul>''')
        routes = [{"prefix": "/docs/core/architecture", "knowledge_files": ["general.md"]},
                  {"prefix": "/docs/core/architecture/kernel", "knowledge_files": ["kernel.md"]}]
        catalog = {p.tree[0]["children"][0]["url"]: {"status": "body_extracted", "cited_in": ["native.md"]}}
        annotate(p.tree, catalog, routes)
        gki, new = p.tree[0]["children"]
        self.assertEqual(gki["knowledge_candidates"], ["kernel.md", "native.md"])
        self.assertEqual(gki["directly_cited_in"], ["native.md"])
        self.assertEqual(gki["semantic_status"], "partial_topic_route")
        self.assertEqual(new["semantic_status"], "no_local_route")
        self.assertEqual(new["catalog_status"], "not_cataloged")
        self.assertEqual(p.tree[0]["knowledge_candidates"], ["kernel.md", "native.md"])

    def test_prefix_boundary_does_not_hide_uncovered_sibling(self):
        p = self.parse('''<ul menu="_book"><li><a href="/docs/core/audio-new">
          <span class="devsite-nav-text">Different topic</span></a></li></ul>''')
        annotate(p.tree, {}, [{"prefix": "/docs/core/audio", "knowledge_files": ["audio.md"]}])
        self.assertEqual(p.tree[0]["knowledge_candidates"], [])

    def test_incomplete_navigation_is_detectable(self):
        p = self.parse('<ul menu="_book"><li><span class="devsite-nav-text">Partial</span></li>')
        self.assertFalse(p.finished)

    def test_lower_tabs_discover_other_navigation_books_not_footer_links(self):
        p = self.parse('''<devsite-tabs class="lower-tabs"><a href="/docs/security/features">Features</a>
          <tab><a href="/docs/security/test/fuzz-sanitize?hl=en">Testing</a></tab>
          <a href="https://other.example/docs">External</a><a href="/docs-extra">Not docs</a></devsite-tabs>
          <footer><a href="/docs/setup">Footer</a></footer>''')
        self.assertEqual(p.tabs, {"https://source.android.com/docs/security/features",
                                  "https://source.android.com/docs/security/test/fuzz-sanitize"})
        self.assertFalse(p.finished)


if __name__ == "__main__":
    unittest.main()
