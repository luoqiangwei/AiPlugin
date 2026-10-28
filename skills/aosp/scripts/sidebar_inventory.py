#!/usr/bin/env python3
"""Record the actual expandable AOSP sidebar and its local knowledge routes.

The navigation contains headings without URLs. Extract the first complete
menu=_book tree, including collapsed descendants, rather than inferring the
sidebar from URL prefixes or treating citations as semantic completion.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener

from docs_catalog import ScopedRedirects

BASE = "https://source.android.com"
SKILL = Path(__file__).resolve().parents[1]
SOURCES = SKILL / "references" / "sources"
SEEDS = ["/docs/setup", "/docs/security", "/docs/core/architecture",
         "/docs/core/connect", "/docs/core/audio", "/docs/core/perf",
         "/docs/core/tests", "/docs/core/data", "/docs/compatibility",
         "/docs/compatibility/cts", "/docs/devices", "/docs/automotive/ivi",
         "/docs/automotive/sdv", "/docs/whatsnew"]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


class SidebarParser(HTMLParser):
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.tree = []
        self.items = []
        self.ul_depth = 0
        self.active = False
        self.finished = False
        self.label_depth = 0
        self.label_parts = []
        self.in_lower_tabs = False
        self.tabs = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "devsite-tabs" and "lower-tabs" in a.get("class", "").split():
            self.in_lower_tabs = True
        if self.in_lower_tabs and tag == "a" and a.get("href"):
            p = urlsplit(urljoin(self.url, a["href"]))
            if p.scheme == "https" and p.netloc == "source.android.com" and (p.path == "/docs" or p.path.startswith("/docs/")):
                self.tabs.add(p._replace(query="", fragment="").geturl().rstrip("/"))
        if tag == "ul" and not self.active and not self.finished and a.get("menu") == "_book":
            self.active = True
        if not self.active:
            return
        if tag == "ul":
            self.ul_depth += 1
        if tag == "li":
            node = {"label": "", "url": None, "children": []}
            (self.items[-1]["children"] if self.items else self.tree).append(node)
            self.items.append(node)
        if tag == "a" and a.get("href") and self.items and not self.items[-1]["url"]:
            u = urljoin(self.url, a["href"])
            p = urlsplit(u)
            self.items[-1]["url"] = p._replace(query="", fragment="").geturl().rstrip("/")
        if tag == "span" and "devsite-nav-text" in a.get("class", "").split() and self.items:
            self.label_depth = 1
            self.label_parts = []
        elif self.label_depth and tag not in VOID:
            self.label_depth += 1

    def handle_data(self, data):
        if self.active and self.label_depth:
            self.label_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "devsite-tabs":
            self.in_lower_tabs = False
        if not self.active:
            return
        if self.label_depth and tag not in VOID:
            self.label_depth -= 1
            if not self.label_depth and self.items:
                self.items[-1]["label"] = " ".join(" ".join(self.label_parts).split())
        if tag == "li" and self.items:
            self.items.pop()
        if tag == "ul":
            self.ul_depth -= 1
            if self.ul_depth == 0:
                self.active = False
                self.finished = True


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node["children"])


def annotate(nodes, catalog, routes):
    for node in nodes:
        url = node["url"]
        record = catalog.get(url, {})
        candidates = set(record.get("cited_in", []))
        matched = []
        if url:
            path = urlsplit(url).path.rstrip("/")
            node["source_kind"] = ("linked_pdf" if path.endswith(".pdf") else
                                   "release_data_json" if path.endswith(".json") else
                                   "docs_article" if path == "/docs" or path.startswith("/docs/") else
                                   "reference_or_external")
            for rule in routes:
                prefix = rule["prefix"].rstrip("/")
                if path == prefix or path.startswith(prefix + "/"):
                    matched.append(rule)
            if matched:
                longest = max(len(r["prefix"]) for r in matched)
                for rule in matched:
                    if len(rule["prefix"]) == longest:
                        candidates.update(rule["knowledge_files"])
            node["catalog_status"] = record.get("status", "not_cataloged" if node["source_kind"] == "docs_article"
                                                 else "outside_article_catalog")
            node["directly_cited_in"] = sorted(record.get("cited_in", []))
        annotate(node["children"], catalog, routes)
        for child in node["children"]:
            if not url:
                candidates.update(child["knowledge_candidates"])
        node["knowledge_candidates"] = sorted(candidates)
        node["semantic_status"] = "partial_topic_route" if candidates else "no_local_route"


def read_sidebar(path, html_dir, timeout):
    url = BASE + path
    cache = html_dir / (hashlib.sha256(url.encode()).hexdigest() + ".html") if html_dir else None
    try:
        if cache and cache.exists():
            raw = cache.read_bytes()
            retrieved_at = datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
            cache_used = True
        else:
            with build_opener(ScopedRedirects()).open(
                    Request(url, headers={"User-Agent": "AOSP-sidebar-inventory/1.0"}), timeout=timeout) as response:
                if urlsplit(response.url).hostname != "source.android.com":
                    raise ValueError("navigation redirected outside official host")
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError("navigation exceeds 8 MB")
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(raw)
            retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cache_used = False
        parser = SidebarParser(url)
        parser.feed(raw.decode("utf-8", errors="replace"))
        if (not parser.finished or not parser.tree) and not parser.tabs:
            raise ValueError("complete menu=_book tree not found")
        return {"source_url": url, "status": "navigation_extracted" if parser.finished else "landing_without_sidebar",
                "source_retrieved_at": retrieved_at, "html_sha256": hashlib.sha256(raw).hexdigest(),
                "cache_used": cache_used, "navigation_tabs": sorted(parser.tabs),
                "tree": parser.tree if parser.finished else []}
    except (OSError, ValueError) as exc:
        return {"source_url": url, "status": "unavailable", "error": str(exc)[:240], "tree": []}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html-dir", type=Path, help="Optional temporary HTML cache outside the skill")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--routes", type=Path, default=SOURCES / "sidebar-routes.json")
    ap.add_argument("--output", type=Path, default=SOURCES / "sidebar.json")
    args = ap.parse_args()
    if args.timeout <= 0:
        ap.error("timeout must be positive")
    catalog = {r["url"]: r for r in map(json.loads, (SOURCES / "catalog.jsonl").read_text().splitlines())}
    routes = json.loads(args.routes.read_text())["routes"]
    missing_files = sorted({name for rule in routes for name in rule["knowledge_files"]
                            if not (SKILL / "references" / name).is_file()})
    if missing_files:
        ap.error("knowledge route files do not exist: " + ", ".join(missing_files))
    scheduled = set(SEEDS)
    pending = sorted(scheduled)
    sections = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch = list(pool.map(lambda path: read_sidebar(path, args.html_dir, args.timeout), pending))
            sections.extend(batch)
            pending = []
            for section in batch:
                for tab in section.get("navigation_tabs", []):
                    path = urlsplit(tab).path
                    if path not in scheduled and path != "/docs":
                        scheduled.add(path)
                        pending.append(path)
            pending.sort()
    for section in sections:
        annotate(section["tree"], catalog, routes)
    nodes = [node for section in sections for node in walk(section["tree"])]
    urls = {n["url"] for n in nodes if n["url"]}
    data = {"schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "method": "Follow official lower navigation tabs recursively; extract first complete menu=_book HTML tree per section; retain collapsed headings/children; exclude duplicate desktop/mobile trees; record landing pages without sidebars separately",
            "semantic_status_means": "Knowledge candidates are routes into partial topic explanations, never proof that every leaf statement is distilled. Direct citation is provenance only. See topic-coverage.md for depth boundaries.",
            "sections": sections, "unique_navigation_urls": len(urls),
            "unrouted_urls": sorted({n["url"] for n in nodes if n["url"] and not n["knowledge_candidates"]}),
            "uncataloged_docs_urls": sorted(u for u in urls if u.startswith(BASE + "/docs") and u not in catalog),
            "unavailable_sections": [s["source_url"] for s in sections if s["status"] == "unavailable"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(args.output)
    print(json.dumps({k: data[k] for k in ("unique_navigation_urls", "unrouted_urls", "uncataloged_docs_urls", "unavailable_sections")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
