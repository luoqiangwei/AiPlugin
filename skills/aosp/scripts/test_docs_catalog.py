"""Offline regression checks for public-doc scope, extraction and resumability."""

from argparse import Namespace
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import docs_catalog as catalog


class CatalogTests(unittest.TestCase):
    def test_scope_and_translation_deduplication(self):
        self.assertEqual(catalog.canonical("https://source.android.com/docs/core?hl=zh-cn#ipc"),
                         "https://source.android.com/docs/core")
        for url in ("https://example.com/docs", "https://source.android.com.evil.test/docs",
                    "http://source.android.com/docs", "https://source.android.com/reference/hal"):
            self.assertIsNone(catalog.canonical(url))

    def test_external_redirect_is_rejected_before_following(self):
        handler = catalog.ScopedRedirects()
        request = Request("https://source.android.com/docs")
        with self.assertRaises(HTTPError) as caught:
            handler.redirect_request(request, None, 302, "Found", {}, "https://example.com/docs")
        caught.exception.close()

    def test_embedded_void_tags_do_not_truncate_cdd_like_articles(self):
        parser = catalog.ArticleParser("https://source.android.com/docs/example")
        parser.feed('<nav>navigation</nav><div class="devsite-article-body clearfix">'
                    '<meta name="translation" value="human"/><p>CE<br/>DE<p>unlock'
                    '<div><p>nested</p></div><style>hidden css</style>tail</div>'
                    '<footer>not article</footer>')
        self.assertEqual(" ".join(parser.text), "CE DE unlock nested tail")

    def test_only_documentation_links_are_discovered(self):
        parser = catalog.ArticleParser("https://source.android.com/docs/core/example")
        parser.feed('<a href="../security?hl=en#x">ok</a><a href="https://example.com/docs">external</a>'
                    '<a href="/reference/hal">api reference</a>')
        self.assertEqual(parser.links, {"https://source.android.com/docs/security"})

    def test_cyclic_graph_is_bounded_and_resume_finishes_pending_pages(self):
        root = "https://source.android.com/docs"
        graph = {root: {root + "/a", root + "/b"}, root + "/a": {root}, root + "/b": {root + "/a"}}
        calls = []

        def fake_fetch(url, cache_dir, timeout):
            calls.append(url)
            return {"url": url, "final_url": url, "status": "body_extracted",
                    "parser_version": catalog.PARSER_VERSION}, graph[url]

        with tempfile.TemporaryDirectory() as temporary:
            args = Namespace(output=temporary, resume=False, refresh=False, retry_failed=False,
                             cache_dir=None, workers=1, timeout=1, max_pages=1)
            with patch.object(catalog, "ROOTS", ["/docs"]), patch.object(catalog, "fetch", fake_fetch), redirect_stdout(io.StringIO()):
                catalog.sync(args)
                first = json.loads((Path(temporary) / "coverage.json").read_text())
                self.assertEqual(first["recorded_pages"], 1)
                self.assertEqual(len(first["pending_pages"]), 2)
                args.resume, args.max_pages = True, 0
                catalog.sync(args)
            final = json.loads((Path(temporary) / "coverage.json").read_text())
            self.assertEqual(final["pending_pages"], [])
            self.assertEqual(final["recorded_pages"], 3)
            self.assertEqual(len(calls), len(set(calls)))

    def test_refresh_revisits_existing_pages(self):
        root = "https://source.android.com/docs"
        with tempfile.TemporaryDirectory() as temporary:
            args = Namespace(output=temporary, resume=False, refresh=False, retry_failed=False,
                             cache_dir=None, workers=1, timeout=1, max_pages=0)
            fake = ({"url": root, "final_url": root, "status": "body_extracted",
                     "parser_version": catalog.PARSER_VERSION}, set())
            with patch.object(catalog, "ROOTS", ["/docs"]), patch.object(catalog, "fetch", return_value=fake) as fetch, redirect_stdout(io.StringIO()):
                catalog.sync(args)
                args.resume = True
                catalog.sync(args)
                self.assertEqual(fetch.call_count, 1)
                args.refresh = True
                catalog.sync(args)
                self.assertEqual(fetch.call_count, 2)

    def test_citation_coverage_tracks_current_knowledge_not_old_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "sources"
            note = root / "topic.md"
            url = "https://source.android.com/docs/core/example"
            records = {url: {"url": url, "final_url": url, "status": "body_extracted"}}
            args = Namespace(workers=1, max_pages=0, timeout=1)
            note.write_text("[Source](" + url + ")")
            catalog.write_snapshot(output, records, set(), "start", args)
            self.assertEqual(catalog.read_rows(output / "catalog.jsonl")[0]["cited_in"], ["topic.md"])
            note.write_text("No longer cited.")
            catalog.write_snapshot(output, records, set(), "start", args)
            self.assertNotIn("cited_in", catalog.read_rows(output / "catalog.jsonl")[0])

    def test_search_prefers_mechanism_coverage_and_deduplicates_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "catalog.jsonl"
            ota = "https://source.android.com/docs/core/ota/virtual_ab"
            rows = [
                {"url": "https://source.android.com/docs/core/tests/lab", "title": "Virtual devices in lab", "status": "body_extracted"},
                {"url": ota, "final_url": ota, "title": "Virtual A/B", "technical_terms": ["SnapshotManager"], "status": "body_extracted"},
                {"url": ota + "/alias", "final_url": ota, "title": "Virtual A/B", "technical_terms": ["SnapshotManager"], "status": "body_extracted"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows))
            output = io.StringIO()
            with redirect_stdout(output):
                catalog.search(Namespace(query="virtual ab snapshot", catalog=str(path), limit=8))
            hits = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(hits[0]["url"], ota)
            self.assertEqual(len(hits), 2)


if __name__ == "__main__":
    unittest.main()
