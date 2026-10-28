#!/usr/bin/env python3
"""Inventory and search canonical AOSP documentation without mirroring manuals.

Only public HTTPS pages under source.android.com/docs are fetched. Article text
is used for fingerprints and technical-term discovery, and optionally cached
outside the skill for investigation. Fetching is not semantic verification.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE = "https://source.android.com"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "references" / "sources"
ROOTS = ["/docs", "/docs/setup", "/docs/core", "/docs/security",
         "/docs/compatibility", "/docs/devices", "/docs/automotive",
         "/docs/whatsnew"]
PARSER_VERSION = 2


def canonical(url):
    p = urlsplit(url)
    if p.scheme != "https" or p.netloc != "source.android.com":
        return None
    if p.path != "/docs" and not p.path.startswith("/docs/"):
        return None
    # Translations are duplicates of the canonical English technical source.
    if "/intl/" in p.path or "/_" in p.path:
        return None
    return urlunsplit(("https", p.netloc, p.path.rstrip("/"), "", ""))


class ScopedRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = canonical(urljoin(req.full_url, newurl))
        if not target:
            raise HTTPError(req.full_url, code, "redirect outside documentation scope", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, target)


class ArticleParser(HTMLParser):
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.links = set()
        self.title = []
        self.text = []
        self.depth = 0
        self.article_depth = None
        self.in_title = False
        self.hidden = 0
        self.updated = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        # Track div nesting, not every HTML tag: void tags may be explicitly
        # self-closing and optional p/li end tags cannot be counted as a stack.
        if tag == "div":
            self.depth += 1
        if tag == "a" and a.get("href"):
            link = canonical(urljoin(self.url, a["href"]))
            if link:
                self.links.add(link)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and a.get("itemprop") == "dateModified":
            self.updated = a.get("content", "")
        if tag == "div" and "devsite-article-body" in a.get("class", "").split():
            self.article_depth = self.depth
        if tag in {"script", "style", "nav"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "nav"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "div":
            if self.article_depth == self.depth:
                self.article_depth = None
            self.depth = max(0, self.depth - 1)

    def handle_data(self, data):
        updated = re.search(r"Last updated\s+(\d{4}-\d{2}-\d{2})\s+UTC", data)
        if updated:
            self.updated = updated.group(1)
        if self.in_title:
            self.title.append(data)
        if self.article_depth is not None and not self.hidden:
            self.text.append(data)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(url, cache_dir, timeout):
    opener = build_opener(ScopedRedirects())
    record = {"url": url, "fetched_at": now(), "status": "unavailable"}
    links = set()
    for attempt in range(2):
        try:
            request = Request(url, headers={"User-Agent": "AOSP-domain-catalog/1.0", "Accept": "text/html"})
            with opener.open(request, timeout=timeout) as response:
                final_url = canonical(response.url)
                content_type = response.headers.get("Content-Type", "")
                if not final_url:
                    raise ValueError("response is outside documentation scope")
                if "text/html" not in content_type:
                    record.update(status="non_html", final_url=final_url, content_type=content_type, parser_version=PARSER_VERSION,
                                  title=urlsplit(final_url).path.rsplit("/", 1)[-1])
                    return record, links
                data = response.read(8_000_001)
                if len(data) > 8_000_000:
                    raise ValueError("page exceeds 8 MB limit")
            parser = ArticleParser(final_url)
            parser.feed(data.decode("utf-8", errors="replace"))
            text = re.sub(r"\s+", " ", " ".join(parser.text)).strip()
            title = " ".join(" ".join(parser.title).split()).split(" | ")[0]
            title = " ".join(title.split()[:20])[:160]
            # Keep technical identifiers, rather than copying prose excerpts.
            terms = Counter(re.findall(r"\b(?:[A-Z][A-Z0-9_]{1,}|[a-z]+_[a-z_]+|[A-Z][a-z]+[A-Z][A-Za-z]+)\b", text))
            record.update(status="body_extracted" if text else "metadata_only", parser_version=PARSER_VERSION,
                          title=title, final_url=final_url,
                          article_sha256=hashlib.sha256(text.encode()).hexdigest(),
                          body_characters=len(text), technical_terms=[t for t, _ in terms.most_common(24)],
                          source_updated=parser.updated,
                          section=urlsplit(final_url).path.split("/")[2] if "/docs/" in final_url else "overview")
            links = parser.links
            if cache_dir is not None:
                cache_dir.mkdir(parents=True, exist_ok=True)
                key = hashlib.sha256(url.encode()).hexdigest()
                (cache_dir / (key + ".json")).write_text(json.dumps(
                    {"record": record, "links": sorted(links), "article_text": text}, ensure_ascii=False))
            return record, links
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            record["error"] = str(exc)[:240]
            record["http_status"] = getattr(exc, "code", None)
            if isinstance(exc, HTTPError):
                exc.close()
            if isinstance(exc, HTTPError) and exc.code not in {429, 500, 502, 503, 504}:
                break
            if attempt == 0:
                time.sleep(1)
    return record, links


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def atomic_write(path, text):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def write_snapshot(output, records, pending, started, args):
    output.mkdir(parents=True, exist_ok=True)
    rows = sorted(records.values(), key=lambda r: r["url"])
    citations = {}
    knowledge_files = sorted(output.parent.glob("*.md"))
    for page in knowledge_files:
        for url in re.findall(r'https?://[^\s)<>\]]+', page.read_text()):
            normalized = canonical(url) or url
            citations.setdefault(normalized, set()).add(page.name)
    for row in rows:
        row.pop("cited_in", None)
        cited_in = citations.get(row.get("final_url", row["url"]), set()) | citations.get(row["url"], set())
        if cited_in:
            row["cited_in"] = sorted(cited_in)
    atomic_write(output / "catalog.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    stats = Counter(r["status"] for r in rows)
    coverage = {
        "schema_version": 1, "scope": "canonical English HTML reachable under https://source.android.com/docs",
        "discovery_method": "recursive links from official documentation navigation; not proof of orphan-page coverage",
        "seeds": [BASE + path for path in ROOTS], "started_at": started, "updated_at": now(),
        "discovered_pages": len(records) + len(pending), "recorded_pages": len(records),
        "unique_final_pages": len({r["final_url"] for r in rows if r.get("final_url")}),
        "redirected_addresses": sum(r.get("final_url", r["url"]) != r["url"] for r in rows),
        "status_counts": dict(stats), "pending_pages": sorted(pending),
        "section_counts": dict(sorted(Counter(r.get("section", "unknown") for r in rows).items())),
        "body_extracted_means": "HTTP article body retrieved and structurally parsed; not semantic review or validated correctness",
        "curated_sources": "sources cited in domain reference files; catalog entries alone do not imply distillation",
        "knowledge_files": [p.name for p in knowledge_files],
        "distinct_cited_sources": len(citations),
        "catalog_addresses_cited_in_knowledge": sum(bool(r.get("cited_in")) for r in rows),
        "excluded": ["translation duplicates", "generated /reference API pages (linked via reference landing pages)",
                     "external sites and source repositories", "unlinked or inaccessible pages"],
        "limits": {"workers": args.workers, "max_pages": args.max_pages, "timeout_seconds": args.timeout},
    }
    atomic_write(output / "coverage.json", json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")


def sync(args):
    output = Path(args.output)
    records = {r["url"]: r for r in read_rows(output / "catalog.jsonl")} if args.resume else {}
    pending = {BASE + path for path in ROOTS}
    previous = output / "coverage.json"
    if args.resume and previous.exists():
        pending.update(json.loads(previous.read_text()).get("pending_pages", []))
    if args.refresh:
        pending.update(records)
        records = {}
    if args.retry_failed:
        pending.update(u for u, r in records.items() if r["status"] == "unavailable")
        records = {u: r for u, r in records.items() if r["status"] != "unavailable"}
    pending.update(u for u, r in records.items()
                   if r["status"] != "unavailable" and r.get("parser_version") != PARSER_VERSION)
    records = {u: r for u, r in records.items()
               if r["status"] == "unavailable" or r.get("parser_version") == PARSER_VERSION}
    pending.difference_update(records)
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    if cache_dir:
        for p in cache_dir.glob("*.json"):
            try:
                cached = json.loads(p.read_text())
                pending.update(cached.get("links", []))
            except (ValueError, OSError):
                continue
        pending.difference_update(records)
    started = now()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        while pending and (not args.max_pages or done < args.max_pages):
            batch_size = min(args.workers * 3, args.max_pages - done) if args.max_pages else args.workers * 3
            batch = sorted(pending)[:batch_size]
            pending.difference_update(batch)
            futures = {pool.submit(fetch, url, cache_dir, args.timeout): url for url in batch}
            for future in as_completed(futures):
                record, links = future.result()
                records[record["url"]] = record
                pending.update(links - records.keys() - set(batch))
                done += 1
            write_snapshot(output, records, pending, started, args)
            counts = Counter(r["status"] for r in records.values())
            print(json.dumps({"recorded": len(records), "pending": len(pending), "states": dict(counts)}), flush=True)
    write_snapshot(output, records, pending, started, args)


def search(args):
    terms = re.findall(r"[a-z0-9]+", args.query.lower())
    rows = read_rows(Path(args.catalog))
    scored = []
    for row in rows:
        title = row.get("title", "").lower()
        url = row["url"].lower()
        identifiers = " ".join(row.get("technical_terms", [])).lower()
        fields = (title, url, identifiers)
        token_sets = [set(re.findall(r"[a-z0-9]+", field)) for field in fields]
        matches = [[term in tokens or (len(term) > 3 and term in field)
                    for field, tokens in zip(fields, token_sets)] for term in terms]
        coverage = sum(any(flags) for flags in matches)
        score = 100 * coverage + sum(5 * flags[0] + 3 * flags[1] + flags[2] for flags in matches)
        if score:
            scored.append((score, row))
    emitted = set()
    for score, row in sorted(scored, key=lambda pair: (-pair[0], pair[1]["url"])):
        identity = row.get("final_url", row["url"])
        if identity in emitted:
            continue
        emitted.add(identity)
        print(json.dumps({"score": score, "url": row["url"], "title": row.get("title"),
                          "status": row["status"], "fetched_at": row.get("fetched_at"),
                          "cited_in": row.get("cited_in", [])}, ensure_ascii=False))
        if len(emitted) >= args.limit:
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    update = sub.add_parser("sync", help="Read-only public-site crawl; writes only the chosen catalog/cache")
    update.add_argument("--output", default=str(DEFAULT_OUTPUT))
    update.add_argument("--cache-dir", help="Optional transient article cache; keep outside distributable skill")
    update.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    update.add_argument("--timeout", type=float, default=20)
    update.add_argument("--max-pages", type=int, default=0, help="0 processes all discovered pages")
    update.add_argument("--resume", action="store_true")
    update.add_argument("--refresh", action="store_true", help="Re-fetch recorded pages as well as discovering new pages")
    update.add_argument("--retry-failed", action="store_true")
    update.set_defaults(func=sync)
    query = sub.add_parser("search", help="Offline search of titles, URL paths and technical identifiers")
    query.add_argument("query")
    query.add_argument("--catalog", default=str(DEFAULT_OUTPUT / "catalog.jsonl"))
    query.add_argument("--limit", type=int, default=8)
    query.set_defaults(func=search)
    args = parser.parse_args()
    if getattr(args, "max_pages", 0) < 0:
        parser.error("--max-pages must be nonnegative")
    if getattr(args, "limit", 1) < 1 or getattr(args, "timeout", 1) <= 0:
        parser.error("--limit and --timeout must be positive")
    args.func(args)


if __name__ == "__main__":
    main()
