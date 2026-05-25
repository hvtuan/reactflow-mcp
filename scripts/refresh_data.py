#!/usr/bin/env python3
"""Detect drift between the bundled data layer and upstream React/Svelte Flow docs.

What it does:
1. Fetches reactflow.dev + svelteflow.dev sitemap.xml.
2. Extracts symbol names from `/api-reference/<group>/<name>` slugs.
3. Extracts Pro example names from `/pro/examples/<name>` slugs.
4. Diffs against the bundled `api_catalog.py`, `pro_examples.py`,
   and `svelte_equivalents.py`.
5. Emits a markdown report. Exits non-zero if drift is detected so the
   GitHub Action can branch on that.

Zero non-stdlib deps — uses urllib + regex. HTML→structured-data is fragile
so this is intentionally a *report*, not an auto-mutator. The reviewer (you
or an LLM) decides what to add.

Run:
    python scripts/refresh_data.py                      # stdout
    python scripts/refresh_data.py --out report.md      # write to file
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from urllib.error import URLError

# make the repo's src/ importable when running directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from reactflow_mcp.data.api_catalog import API_CATALOG  # noqa: E402
from reactflow_mcp.data.pro_examples import PRO_EXAMPLES  # noqa: E402
from reactflow_mcp.data.svelte_equivalents import (  # noqa: E402
    IDENTICAL as SVELTE_IDENTICAL,
    RENAMED as SVELTE_RENAMED,
    SVELTE_ONLY,
)

SITEMAP_RE = re.compile(r"<loc>(.*?)</loc>")
USER_AGENT = "reactflow-mcp-refresh/0.1 (+https://github.com/hvtuan/reactflow-mcp)"


def _fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _sitemap_urls(sitemap_url: str) -> list[str]:
    try:
        body = _fetch(sitemap_url)
    except URLError as e:
        print(f"::warning::failed to fetch {sitemap_url}: {e}", file=sys.stderr)
        return []
    return SITEMAP_RE.findall(body)


def _path_segments(url: str) -> list[str]:
    return [seg for seg in url.rstrip("/").split("/")[3:] if seg]


_GROUP_LANDING_SLUGS = {"index", "overview", "components", "hooks", "utils", "types", "enums"}


def _collect_api_symbols(urls: list[str]) -> set[str]:
    out: set[str] = set()
    for u in urls:
        segs = _path_segments(u)
        if not segs or segs[0] != "api-reference":
            continue
        if len(segs) == 2:
            # /api-reference/react-flow → 'ReactFlow' (root-level page)
            slug = segs[1]
            if slug in _GROUP_LANDING_SLUGS:
                continue
            out.add(_slug_to_symbol(slug, group="components"))
        elif len(segs) >= 3:
            slug = segs[-1]
            if slug in _GROUP_LANDING_SLUGS:
                continue
            out.add(_slug_to_symbol(slug, group=segs[1]))
    return out


def collect_react_api_symbols(urls: list[str]) -> set[str]:
    return _collect_api_symbols(urls)


def collect_svelte_api_symbols(urls: list[str]) -> set[str]:
    return _collect_api_symbols(urls)


def collect_pro_examples(urls: list[str]) -> set[str]:
    out: set[str] = set()
    for u in urls:
        segs = _path_segments(u)
        if len(segs) >= 3 and segs[0] == "pro" and segs[1] == "examples":
            slug = segs[-1]
            if slug in {"index", "overview"}:
                continue
            out.add(_slug_to_example_name(slug))
    return out


def _slug_to_symbol(slug: str, group: str) -> str:
    """`use-react-flow` → `useReactFlow`; `node-toolbar` → `NodeToolbar`; `add-edge` → `addEdge`."""
    parts = slug.split("-")
    if not parts:
        return slug
    # hook prefix
    if parts[0] == "use" or group == "hooks":
        return parts[0] + "".join(p.capitalize() for p in parts[1:])
    # utils stay camelCase
    if group == "utils":
        return parts[0] + "".join(p.capitalize() for p in parts[1:])
    # components, types, enums → PascalCase
    return "".join(p.capitalize() for p in parts)


def _slug_to_example_name(slug: str) -> str:
    return " ".join(p.capitalize() for p in slug.split("-"))


# ─────────── diff ───────────


def _normalize(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")


def diff_sets(upstream: set[str], local: set[str], label: str) -> dict:
    upstream_norm = {_normalize(s): s for s in upstream}
    local_norm = {_normalize(s): s for s in local}
    new_upstream = sorted([upstream_norm[k] for k in upstream_norm.keys() - local_norm.keys()])
    missing_local = sorted([local_norm[k] for k in local_norm.keys() - upstream_norm.keys()])
    return {
        "label": label,
        "upstream_count": len(upstream),
        "local_count": len(local),
        "new_upstream": new_upstream,
        "missing_local": missing_local,
    }


def render_report(diffs: list[dict]) -> tuple[str, bool]:
    # only count new_upstream as drift — local-only is too noisy (sitemap may
    # not enumerate every page, e.g. client-rendered example lists)
    any_drift = any(d["new_upstream"] for d in diffs if d["upstream_count"] > 0)
    lines = ["# reactflow-mcp data drift report\n"]
    lines.append("Generated by `scripts/refresh_data.py`.\n")
    if not any_drift:
        lines.append("✅ **No new upstream symbols detected.** Bundled data is up to date.")
    for d in diffs:
        lines.append(f"\n## {d['label']}")
        lines.append(f"_Upstream: {d['upstream_count']} · Local: {d['local_count']}_")
        if d["upstream_count"] == 0:
            lines.append("\n_Upstream sitemap returned no entries for this group "
                         "(likely client-rendered); skipping diff._")
            continue
        if d["new_upstream"]:
            lines.append("\n### 🆕 New upstream (not in local data)")
            for sym in d["new_upstream"]:
                lines.append(f"- `{sym}`")
        if d["missing_local"]:
            lines.append("\n### ❓ Local-only (likely benign — sitemap incomplete or renamed)")
            for sym in d["missing_local"]:
                lines.append(f"- `{sym}`")
        if not d["new_upstream"] and not d["missing_local"]:
            lines.append("\n_No drift in this group._")
    return "\n".join(lines) + "\n", any_drift


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, help="Write report to this file instead of stdout.")
    args = p.parse_args()

    react_urls = _sitemap_urls("https://reactflow.dev/sitemap.xml")
    svelte_urls = _sitemap_urls("https://svelteflow.dev/sitemap.xml")

    react_api_upstream = collect_react_api_symbols(react_urls)
    svelte_api_upstream = collect_svelte_api_symbols(svelte_urls)
    pro_examples_upstream = collect_pro_examples(react_urls)

    api_local = set(API_CATALOG.keys())
    svelte_local = set(SVELTE_IDENTICAL) | {entry["svelte"] for entry in SVELTE_RENAMED.values()} | set(SVELTE_ONLY.keys())
    pro_local = {ex["name"] for ex in PRO_EXAMPLES}

    diffs = [
        diff_sets(react_api_upstream, api_local, "React Flow API symbols"),
        diff_sets(svelte_api_upstream, svelte_local, "Svelte Flow API symbols"),
        diff_sets(pro_examples_upstream, pro_local, "Pro examples"),
    ]

    report, any_drift = render_report(diffs)

    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote report → {args.out}")
    else:
        print(report)

    return 1 if any_drift else 0


if __name__ == "__main__":
    sys.exit(main())
