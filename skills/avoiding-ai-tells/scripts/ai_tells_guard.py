"""ai_tells_guard — validate the AI-tells catalog and scan drafts against it.

Two modes:

  lint  — check that references/ai-tells.md's table is well-formed: every row has 7
          cells within length caps, category/severity drawn from the enums, ISO dates,
          and — importantly — the `replacement` and `source` cells carry no URLs,
          markdown links, or agent-directed instruction shapes. That last check is a
          prompt-injection guard: an AI agent reads these cells verbatim when it scans
          a draft, so a cell must stay inert editorial text, never a live instruction
          or an external fetch.

  scan  — read a draft and report every literal AI-tell phrase from the catalog that
          appears in it, with the suggested replacement. Best-effort: it matches the
          quoted literal phrases in the `pattern` column (e.g. "leverage", "seamless").
          Descriptive / structural rows (metronomic cadence, sentence-DNA arcs) can't
          be matched mechanically and are counted as "needs manual review", not missed
          silently.

Usage:
  python3 scripts/ai_tells_guard.py lint [--table references/ai-tells.md]
  python3 scripts/ai_tells_guard.py scan DRAFT.md [--table references/ai-tells.md]

Exit codes:
  lint — 0 if the table is clean, 1 if any row violates the contract.
  scan — 0 if no `banned` tell was found, 1 if at least one `banned` tell appears
         (soft-flags are reported as warnings and do not fail the run), so `scan`
         is usable as a CI gate on a draft.
"""
import argparse
import os
import re
import sys

TABLE_HEADER = "| pattern | category | severity | replacement | source | added | last_verified |"
COLUMNS = ["pattern", "category", "severity", "replacement", "source", "added", "last_verified"]

CATEGORIES = {
    "opener", "filler-verb", "buzzword-adjective", "intensifier-adverb",
    "cadence-pattern", "closer", "structural-pattern", "punctuation",
}

SEVERITIES = {"banned", "soft-flag"}

# Caps sized ~25% above the longest conforming cell, so legitimate entries fit and
# paragraph-sized payloads don't.
CELL_CAPS = {
    "pattern": 170,
    "category": 24,
    "severity": 20,
    "replacement": 170,
    "source": 200,
    "added": 10,
    "last_verified": 10,
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

URL_PATTERNS = [
    (re.compile(r"https?://", re.I), "URL"),
    (re.compile(r"\bwww\.", re.I), "URL"),
    (re.compile(r"\]\("), "markdown link"),
]

# The replacement cell is read verbatim by an agent at draft time. Editorial
# imperatives ("cut", "name the specific scenario") are its normal shape; what must
# not appear is anything that points an agent elsewhere (URLs, links) or addresses
# the agent as an agent (instruction-override / tool-invocation shapes).
INSTRUCTION_PATTERNS = [
    (re.compile(r"\b(ignore|disregard|forget|override)\b[^.;|]*\b(previous|above|prior|earlier|all)?\s*(instructions?|prompts?|rules?|context)\b", re.I),
     "instruction-override shape"),
    (re.compile(r"\bsystem prompt\b", re.I), "instruction-override shape"),
    (re.compile(r"\byou (are|must|will|should) now\b", re.I), "agent-directed instruction shape"),
    (re.compile(r"\bact as\b", re.I), "agent-directed instruction shape"),
    (re.compile(r"\b(run|execute)\b[^.;|]*\b(command|script|code|shell)\b", re.I), "tool-invocation shape"),
    (re.compile(r"\b(curl|wget)\b", re.I), "tool-invocation shape"),
    (re.compile(r"\b(fetch|download|visit|browse to|navigate to)\b[^.;|]*\b(url|link|page|site|file)\b", re.I),
     "tool-invocation shape"),
    (re.compile(r"<\s*(script|system|img|iframe)\b", re.I), "markup"),
]

REPLACEMENT_BLOCKLIST = URL_PATTERNS + INSTRUCTION_PATTERNS

# A lone capital letter used as a placeholder (X, Y, Z in "It's not just X — it's Y").
# Phrases carrying one can't be matched literally, so scan skips them.
PLACEHOLDER_RE = re.compile(r"(?<![A-Za-z])[A-Z](?![A-Za-z])")


def _split_row(line):
    """Split a markdown table row into cells, honoring escaped pipes (\\|)."""
    body = line.strip()
    if not (body.startswith("|") and body.endswith("|")):
        return None
    body = body[1:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [c.replace("\\|", "|").strip() for c in cells]


def _table_span(lines):
    """(start, end) line indexes of the first canonical table (header through last
    contiguous pipe-line), or None if the header is absent."""
    for i, ln in enumerate(lines):
        if ln.strip() == TABLE_HEADER:
            end = i + 1
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            return i, end
    return None


def parse_table(text, label):
    """Extract the canonical table as an ordered {pattern: row-dict}.

    Returns (rows, errors). A missing table is an error (the guard exists to watch it).
    """
    lines = text.splitlines()
    span = _table_span(lines)
    if span is None:
        return None, [f"{label}: canonical table header not found "
                      f"(expected exactly: {TABLE_HEADER})"]
    start, end = span

    rows, errors = {}, []
    # start + 1 is the |---|---| separator; rows start after it.
    for lineno, ln in enumerate(lines[start + 2:end], start=start + 3):
        cells = _split_row(ln)
        if cells is None or len(cells) != len(COLUMNS):
            errors.append(f"{label} line {lineno}: row does not have exactly "
                          f"{len(COLUMNS)} cells")
            continue
        row = dict(zip(COLUMNS, cells))
        row["_line"] = lineno
        if row["pattern"] in rows:
            errors.append(f"{label} line {lineno}: duplicate pattern cell "
                          f"{row['pattern']!r}")
            continue
        rows[row["pattern"]] = row
    return rows, errors


def lint_row(row, label):
    errors = []
    where = f"{label} line {row['_line']}"
    for col in COLUMNS:
        val = row[col]
        if not val:
            errors.append(f"{where}: empty `{col}` cell")
            continue
        cap = CELL_CAPS[col]
        if len(val) > cap:
            errors.append(f"{where}: `{col}` cell is {len(val)} chars (cap {cap})")
    if row["category"] and row["category"] not in CATEGORIES:
        errors.append(f"{where}: unknown category {row['category']!r} "
                      f"(known: {', '.join(sorted(CATEGORIES))})")
    if row["severity"] and row["severity"] not in SEVERITIES:
        errors.append(f"{where}: unknown severity {row['severity']!r} "
                      f"(known: {', '.join(sorted(SEVERITIES))})")
    for col in ("added", "last_verified"):
        if row[col] and not DATE_RE.match(row[col]):
            errors.append(f"{where}: `{col}` is not a YYYY-MM-DD date: {row[col]!r}")
    for rx, kind in REPLACEMENT_BLOCKLIST:
        if rx.search(row["replacement"]):
            errors.append(f"{where}: `replacement` cell contains a {kind} "
                          f"(matched {rx.pattern!r}) — replacement cells are read "
                          f"verbatim by an agent and must stay editorial")
    for rx, kind in URL_PATTERNS:
        if rx.search(row["source"]):
            errors.append(f"{where}: `source` cell contains a {kind} — sources "
                          f"are citations by name, never links")
    return errors


def literal_phrases(pattern_cell):
    """Extract the literally-matchable phrases from a `pattern` cell: the
    double-quoted substrings, minus any carrying a placeholder capital (X/Y/Z) or a
    bracketed slot ([anything]). Returns [] for descriptive/structural rows with no
    quoted literal — those need manual review."""
    phrases = []
    for q in re.findall(r'"([^"]+)"', pattern_cell):
        # A single quoted cell may carry " / "-separated alternates
        # ("delve" / "delve into"; "world ... / digital landscape / ...").
        for alt in q.split(" / "):
            alt = alt.strip()
            if not alt or "[" in alt or PLACEHOLDER_RE.search(alt):
                continue
            phrases.append(alt)
    return phrases


def scan_draft(rows, draft_text):
    """Return (hits, unscannable_count). hits = list of dicts with line, phrase,
    severity, replacement. unscannable_count = rows with no literal phrase to match."""
    lines = draft_text.splitlines()
    hits, unscannable = [], 0
    for row in rows.values():
        phrases = literal_phrases(row["pattern"])
        if not phrases:
            unscannable += 1
            continue
        for phrase in phrases:
            rx = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.I)
            for lineno, ln in enumerate(lines, start=1):
                if rx.search(ln):
                    hits.append({
                        "line": lineno,
                        "phrase": phrase,
                        "severity": row["severity"],
                        "replacement": row["replacement"],
                    })
    hits.sort(key=lambda h: (h["line"], h["phrase"]))
    return hits, unscannable


def cmd_lint(args):
    with open(args.table, encoding="utf-8") as f:
        text = f.read()
    rows, errors = parse_table(text, "table")
    if rows is None:
        for e in errors:
            print(f"error: {e}")
        return 1
    for row in rows.values():
        errors.extend(lint_row(row, "table"))
    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"\nai-tells lint: FAIL ({len(errors)} violation(s))")
        return 1
    print(f"ai-tells lint: OK ({len(rows)} rows)")
    return 0


def cmd_scan(args):
    with open(args.table, encoding="utf-8") as f:
        rows, errors = parse_table(f.read(), "table")
    if rows is None:
        for e in errors:
            print(f"error: {e}")
        return 1
    with open(args.draft, encoding="utf-8") as f:
        draft = f.read()
    hits, unscannable = scan_draft(rows, draft)

    banned = [h for h in hits if h["severity"] == "banned"]
    soft = [h for h in hits if h["severity"] == "soft-flag"]
    for h in hits:
        tag = "BANNED  " if h["severity"] == "banned" else "soft-flag"
        print(f"{args.draft}:{h['line']}: {tag}  {h['phrase']!r} -> {h['replacement']}")
    print(
        f"\nai-tells scan: {len(banned)} banned, {len(soft)} soft-flag "
        f"across {len({h['line'] for h in hits})} line(s); "
        f"{unscannable} structural/descriptive pattern(s) need manual review "
        f"(not machine-checkable)."
    )
    return 1 if banned else 0


def default_table_path():
    """references/ai-tells.md relative to this script's parent skill folder."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "references", "ai-tells.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI-tells catalog guard + draft scanner")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_lint = sub.add_parser("lint", help="validate the ai-tells.md table")
    p_lint.add_argument("--table", default=default_table_path())
    p_lint.set_defaults(func=cmd_lint)

    p_scan = sub.add_parser("scan", help="scan a draft against the catalog")
    p_scan.add_argument("draft", help="path to the draft file to scan")
    p_scan.add_argument("--table", default=default_table_path())
    p_scan.set_defaults(func=cmd_scan)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
