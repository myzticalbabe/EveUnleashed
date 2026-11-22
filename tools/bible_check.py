#!/usr/bin/env python3
"""Check a canon corpus written in biblical form; render it, index it, generate it.

WHY A CHECKER AT ALL
--------------------
A Bible-shaped document earns its authority from citation: a verse exists so
another verse can lean on it. That only works if a reference resolves, and it
only stays honest if the thing it cites has not been quietly changed. So the
corpus is data -- `docs/bible/bible.json` -- and this tool is its apparatus:
numbering that must be contiguous, citations that must land, statutes that must
name both the rule they come from and the check that proves they are kept, and a
hard refusal of any figure whose command is not written beside it.

WHAT IT REFUSES, AND WHY EACH REFUSAL IS A WAY THE TEXT WOULD LIE
----------------------------------------------------------------
* **A dangling citation.** "As it is written in Genesis 4:9" is a claim; if the
  verse is not there, the claim is unfalsifiable and the reader cannot tell a
  quotation from an invention. A citation may also name a document instead of a
  verse, and then the document must exist.
* **A number with no command.** Any digit in a verse body, an annotation, a gloss
  or an introduction paragraph demands a `source` naming a path in this
  repository. This is the rule `docs/index.md` already states for prose -- every
  number names the command that produced it -- made mechanical, because a
  scripture quoting an unmeasured figure is the most quotable possible form of a
  false one.
* **A statute with no check.** A law with nothing executing it is a proverb. It
  belongs in the wisdom book, and the validator says so instead of letting a
  commandment masquerade as a gate.
* **A statute whose rule is not in canon.** The corpus narrates canon; it does
  not legislate. A statute must cite a RULE that exists in `MANDATES.md`, so the
  Bible cannot become a second source of truth.
* **A heading carrying a figure.** A pericope heading is a label, not a claim,
  and it has no field to name a command with.
* **A name.** Refused substrings and contact shapes are rejected outright, on the
  same line `Project_Nurse_Ratchet/DISCLOSURE_POLICY.md` draws: methodology
  ships, people do not.
* **Growth without a cap.** Books, chapters per book, verses per chapter and
  annotations per verse are all capped. A canon of sixty-six books is a parody
  with a bibliography; an uncapped corpus is how a catalogue becomes a liability.
* **A `complete` corpus with a verse that does no work.** When the corpus
  declares itself complete, every verse must be cited, cite, or carry a statute,
  an annotation or a variant -- and every book must have an introduction. `seed`
  and `drafting` make no such claim, so nothing is enforced there.

TWO GENERATED FILES, BOTH DRIFT-CHECKED
--------------------------------------
`--genealogy` reads `src/` with `ast` and counts cross-package imports, because
"and A begat B" is an import edge and a genealogy a reader can re-run is the one
part of a scripture that cannot be embellished. `--render` writes the readable
edition: headings in place, notes and apparatus beside the verse they annotate,
a marginal column naming who cites whom, and the glossary at the back.

Both are committed, and `--check` compares each against a fresh rendering. A
generated file nobody re-checks is a second source of truth: the mesh ledger in
this tree went stale exactly that way, and a published number that no longer
matches its own data is worse than no number.

Usage:
  python tools/bible_check.py                     # counts and warnings
  python tools/bible_check.py --check              # exit 1 on any defect (the gate)
  python tools/bible_check.py --index              # who cites whom, and the orphans
  python tools/bible_check.py --render             # print the readable edition
  python tools/bible_check.py --render --write      # regenerate BOOK_OF_THE_TREE.md
  python tools/bible_check.py --genealogy           # print the generations
  python tools/bible_check.py --genealogy --write   # regenerate GENEALOGY.md
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

#: The rule-resolution predicate is shared with `bible_theme.py`, so the two
#: gates cannot disagree about whether a rule exists. A tool loaded by path has
#: no sibling on `sys.path` unless it puts its own directory there.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import canon_rules

REPO = Path(__file__).resolve().parents[1]
BIBLE_DIR = REPO / "docs" / "bible"
CORPUS = BIBLE_DIR / "bible.json"
GENEALOGY = BIBLE_DIR / "GENEALOGY.md"
EDITION = BIBLE_DIR / "BOOK_OF_THE_TREE.md"
MANDATES = REPO / "MANDATES.md"
SRC = REPO / "src"

SCHEMA = "azazael/bible@1"
STATUSES = ("seed", "drafting", "complete")

#: A genre per book, because the Bible is an anthology and a single register for
#: twelve books is pastiche. Each name here is a job, not a mood.
GENRES = (
    "etiology",
    "law",
    "history",
    "chronicle",
    "wisdom",
    "lament",
    "prophecy",
    "gospel",
    "epistle",
    "apocalypse",
    "genealogy",
    "domain",
)
#: Placement of a verse inside a domain book: the ``practice`` block is rendered
#: as a titled apparatus under the verse, never inline, so a reader can read the
#: narrative and then choose to read the instruction.

#: Declared ceilings. `limits` in the corpus may tighten these and may never
#: exceed them: a cap the author can raise is not a cap.
#: Raised 2026-11-01 when books became domains. There are 11 declared domains
#: today (sentinel, cain, eve_rani, hives, gosp, ml, shards, dev, edge0, wraith,
#: oxman) plus the four canonical registers, so the old ceiling of 24 left six
#: books of headroom for a corpus meant to absorb every environment. 32 is still
#: a retirement-forcing cap: the twelve domains of this fleet fit twice over.
HARD_MAX_BOOKS = 32
HARD_MAX_CHAPTERS = 60
HARD_MAX_VERSES = 200
HARD_MAX_ANNOTATIONS = 12

DEFAULT_LIMITS = {
    "max_books": 20,
    "max_chapters_per_book": 12,
    "max_verses_per_chapter": 60,
    "max_annotations_per_verse": 6,
}
CEILINGS = {
    "max_books": HARD_MAX_BOOKS,
    "max_chapters_per_book": HARD_MAX_CHAPTERS,
    "max_verses_per_chapter": HARD_MAX_VERSES,
    "max_annotations_per_verse": HARD_MAX_ANNOTATIONS,
}

#: The disclosure line, in the same terms the package's manifest refuses.
REFUSED_SUBSTRINGS = (
    "bcc_audit",
    "REINVESTIGATION",
    "FETCH_LOG",
    "edge_proof_ledger",
    "identity_tiebreak",
    "new_sources_log",
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\d-])\d{3}[-.\s]\d{3}[-.\s]\d{4}(?![\d-])")
DIGIT_RE = re.compile(r"[0-9]")
#: Any repository-relative path, not just the six directories this tree happens
#: to keep tools in: `Project_Nurse_Ratchet/README.md` is the provenance of a
#: defect recorded in that package, and a checker that could not name it would
#: push the author to cite the wrong file instead. The lookbehind refuses to
#: begin inside a URL, so `https://host/x.md` cannot masquerade as a local path.
PATH_RE = re.compile(
    r"(?<![\w/:.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
    r"\.(?:py|json|md|js|ps1|sh|yml|yaml)"
)
REF_RE = re.compile(r"^([a-z][a-z0-9_]*)\s+([0-9]+):([0-9]+)$")
RULE_RE = re.compile(r"\bRULE\s+[0-9][0-9A-Za-z-]*")

#: The annotated-edition layer. An Oxford-style Bible is not a bare text: it
#: carries a book introduction, pericope headings, footnotes sorted by kind, and a
#: glossary. The kinds matter because a textual note and a historical note fail
#: differently -- one is a reading, the other is a claim about the world -- and a
#: reader is entitled to know which they are reading.
ANNOTATION_KINDS = ("textual", "historical", "translation", "editorial", "cross")

TOP_KEYS = {
    "schema",
    "title",
    "status",
    "updated",
    "limits",
    "note",
    "books",
    "glossary",
    "edition",
    "configs",
}
BOOK_KEYS = {"id", "name", "subtitle", "genre", "domain", "introduction", "chapters"}
#: A book may be *about* a declared domain, and then it must name one that
#: exists: a guide organised by domain is only organised if every book's subject
#: is a real, measurable tree rather than a heading someone liked.
DOMAINS_MODULE = "tools/domain_trees.py"
#: The practical apparatus. It is separate from `annotations` because a note is
#: commentary and a practice is instruction: symptom, cause, the command that
#: detects it, the remedy, and the harnessed records that support the claim.
PRACTICE_KEYS = {"symptom", "cause", "detection", "remedy", "evidence"}
MIN_EVIDENCE = 3
CHAPTER_KEYS = {"number", "sections", "verses"}
VERSE_KEYS = {
    "number",
    "text",
    "cites",
    "source",
    "statute",
    "practice",
    "variants",
    "annotations",
    "note",
}
STATUTE_KEYS = {"rule", "check", "why"}
VARIANT_KEYS = {"reading", "text", "source"}
ANNOTATION_KEYS = {"kind", "note", "source"}
SECTION_KEYS = {"before_verse", "heading"}
INTRODUCTION_KEYS = {"paragraphs", "sources"}
GLOSSARY_KEYS = {"term", "gloss", "see", "source"}
EDITION_KEYS = {"name", "basis"}


class CorpusError(Exception):
    """Malformed corpus. Never downgraded to a warning."""


def load(path: Path = CORPUS) -> dict:
    if not path.exists():
        raise CorpusError(f"{path} is absent; there is no corpus to check")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{path.name} is not valid JSON: {exc}") from exc


def _paths_in(text: str) -> list[str]:
    return PATH_RE.findall(text or "")


def _provenance_problems(source, where: str, repo: Path) -> list[str]:
    """A figure must name a command that exists. Verbs alone do not count.

    `python some_tool.py` with no path is a memory of a command; a path that
    resolves is a command someone can run. Paths under `logs/` are exempt from
    existence because reports are rotated and the corpus may cite one that has
    since been replaced -- but the token must still be written down.
    """
    if not isinstance(source, str) or not source.strip():
        return [
            f"{where}: a number needs `source`: the command or path that produced it"
        ]
    tokens = _paths_in(source)
    if not tokens:
        return [
            f"{where}: source names no repository path ({source!r}); a figure with no "
            "re-runnable command is a claim, not evidence"
        ]
    problems = []
    for token in tokens:
        head = token.split("/", 1)[0]
        if head == "logs":
            continue
        if not (Path(repo) / token.split("#", 1)[0]).exists():
            problems.append(f"{where}: source path does not exist here: {token}")
    return problems


def _text_problems(text, where: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(text, str) or not text.strip():
        return [f"{where}: text is empty"]
    if not re.search(r"[A-Za-z]", text):
        problems.append(f"{where}: text carries no words")
    lowered = text.lower()
    for token in REFUSED_SUBSTRINGS:
        if token.lower() in lowered:
            problems.append(
                f"{where}: refused substring {token!r} -- methodology ships, people "
                "do not"
            )
    if EMAIL_RE.search(text):
        problems.append(f"{where}: an email address is refused")
    if PHONE_RE.search(text):
        problems.append(f"{where}: a phone number is refused")
    return problems


def _prose_block_problems(paragraphs, sources, where: str, repo: Path) -> list[str]:
    """An introduction or a gloss is prose, but it still may not assert a figure
    for free: the moment it carries a digit, the block must name its sources."""
    problems: list[str] = []
    if not isinstance(paragraphs, list) or not paragraphs:
        return [f"{where}: paragraphs must be a non-empty list"]
    carries_digit = False
    for index, paragraph in enumerate(paragraphs):
        problems.extend(_text_problems(paragraph, f"{where} paragraph {index + 1:d}"))
        if isinstance(paragraph, str) and DIGIT_RE.search(paragraph):
            carries_digit = True
    if sources is not None and not isinstance(sources, list):
        problems.append(f"{where}: sources must be a list")
        sources = []
    if carries_digit:
        if not sources:
            problems.append(
                f"{where}: a paragraph carries a figure, so the block must name "
                "`sources` -- or spell the number out"
            )
        for source in sources or []:
            problems.extend(_provenance_problems(source, where, repo))
    return problems


def _statute_problems(
    statute,
    where: str,
    repo: Path,
    canon: dict[str, dict] | None,
    canon_text: str | None = None,
) -> list[str]:
    if not isinstance(statute, dict):
        return [f"{where}: statute must be an object with `rule` and `check`"]
    problems: list[str] = []
    unknown = set(statute) - STATUTE_KEYS
    if unknown:
        problems.append(f"{where}: unknown statute key(s) {sorted(unknown)}")
    rule = statute.get("rule")
    if not isinstance(rule, str) or not RULE_RE.search(rule):
        problems.append(f'{where}: statute.rule must name a RULE (e.g. "RULE 0B")')
    elif canon is None:
        problems.append(
            f"{where}: MANDATES.md is unreadable -- the rule {rule!r} cannot be "
            "verified against canon"
        )
    else:
        # A heading with a body, not a mention anywhere in the file: `RULE 0B-D`
        # appears in two `Related:` lines, and that is what the substring test
        # was reading as a law.
        defect = canon_rules.rule_problem(rule, canon, canon_text)
        if defect:
            problems.append(f"{where}: {defect}")
    check = statute.get("check")
    if not isinstance(check, str) or not check.strip():
        problems.append(
            f"{where}: statute.check is empty -- a law with nothing executing "
            "it is a proverb, not a statute"
        )
    else:
        tokens = _paths_in(check)
        if not tokens:
            problems.append(
                f"{where}: statute.check names no repository path ({check!r})"
            )
        for token in tokens:
            if not (Path(repo) / token.split("#", 1)[0]).exists():
                problems.append(f"{where}: statute.check does not exist here: {token}")
    return problems


def _resolve_citation(
    citation: str, index: dict[str, dict[int, dict[int, dict]]], repo: Path
) -> str | None:
    """Return a problem string, or None when the citation lands."""
    match = REF_RE.match(citation)
    if match:
        book_id, chapter_text, verse_text = match.groups()
        chapter, verse = int(chapter_text), int(verse_text)
        if book_id not in index:
            return f"cites unknown book {book_id!r}"
        if chapter not in index[book_id] or verse not in index[book_id][chapter]:
            return f"cites {citation}, which does not exist"
        return None
    if PATH_RE.fullmatch(citation):
        if (repo / citation).exists():
            return None
        return f"cites {citation}, which does not exist in this repository"
    return (
        f'citation {citation!r} must read "<book> <chapter>:<verse>" or name a '
        "repository path"
    )


def declared_domains(repo: Path = REPO) -> set | None:
    """The domain ids declared in `tools/domain_trees.py`, read by AST.

    Read, not imported: importing the atlas tool drags its whole census in, and a
    checker that scans a filesystem to decide whether a *name* is legitimate is
    doing far more work than the question needs. Returns None when the file is
    unreadable, which is reported rather than treated as "no domains".
    """
    path = Path(repo) / DOMAINS_MODULE
    if not path.exists():
        return None
    # Unreadable is raised, not returned as a default: a caller that turns
    # "could not read" into "reads like nothing" is how a missing declaration
    # becomes a silent pass, and the scanner is right to refuse that shape.
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        raise CorpusError(f"{DOMAINS_MODULE} could not be parsed: {exc}") from exc
    for node in tree.body:
        # Both forms are in use in this tree: a bare assignment and an annotated
        # one (`DOMAINS: Dict[str, ...] = {`). Reading only the first reported
        # every domain as unverifiable while the declaration sat in plain sight.
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign):
            names = [t for t in node.targets if isinstance(t, ast.Name)]
            target, value = (names[0] if names else None), node.value
        else:
            continue
        if not isinstance(target, ast.Name) or target.id != "DOMAINS":
            continue
        if isinstance(value, ast.Dict):
            keys = [
                key.value
                for key in value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            ]
            return set(keys)
    return None


def harvest_ids(repo: Path = REPO) -> set | None:
    """Ids available to cite. None when the ledger is absent, which is a defect."""
    path = Path(repo) / "docs" / "bible" / "harvest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CorpusError(f"docs/bible/harvest.json could not be read: {exc}") from exc
    return {record.get("id") for record in data.get("records", []) if record.get("id")}


def _practice_problems(practice, where: str, repo: Path, ids: set | None) -> list[str]:
    """A practice is instruction: an observation, its cause, its detection, its fix.

    The evidence rule is the one that makes the corpus a guide rather than a
    collection of opinions: a practice that cannot name three harnessed records
    is somebody's impression, and it belongs in a footnote, not in a canon.
    """
    if not isinstance(practice, dict):
        return [f"{where}: practice must be an object"]
    problems: list[str] = []
    unknown = set(practice) - PRACTICE_KEYS
    if unknown:
        problems.append(f"{where}: unknown practice key(s) {sorted(unknown)}")
    for key in ("symptom", "cause", "detection", "remedy"):
        value = practice.get(key)
        problems.extend(_text_problems(value, f"{where} practice.{key}"))
        if isinstance(value, str) and DIGIT_RE.search(value):
            problems.append(
                f"{where}: practice.{key} carries a figure; a practice states the "
                "shape of a failure, and the record that measured it is "
                "cited in `evidence`"
            )
    detection = practice.get("detection")
    if isinstance(detection, str) and detection.strip():
        tokens = _paths_in(detection)
        if not tokens:
            problems.append(
                f"{where}: practice.detection names no repository path -- "
                "what command would show this is happening?"
            )
        for token in tokens:
            if not (Path(repo) / token.split("#", 1)[0]).exists():
                problems.append(
                    f"{where}: practice.detection does not exist here: {token}"
                )
    evidence = practice.get("evidence")
    if not isinstance(evidence, list) or len(set(evidence)) < MIN_EVIDENCE:
        problems.append(
            f"{where}: practice.evidence must cite at least {MIN_EVIDENCE:d} harvest records; "
            "a rule distilled from fewer is an anecdote"
        )
        evidence = evidence if isinstance(evidence, list) else []
    if ids is None:
        problems.append(
            f"{where}: docs/bible/harvest.json is absent, so no citation can "
            "be checked -- run tools/bible_harvest.py --write"
        )
    else:
        for record_id in evidence:
            if record_id not in ids:
                problems.append(
                    f"{where}: practice.evidence cites {record_id!r}, which the harvest "
                    "ledger does not contain"
                )
    return problems


CONFIG_KINDS = ("text", "json", "path")
CONFIG_SCOPES = ("repo", "host")


def _config_problems(configs, repo: Path) -> tuple[list[str], list[str]]:
    """The `configs` layer: the settings the corpus's instructions depend on.

    A canon of instruction with no configuration is a sermon. Every rule in this
    corpus that says "run the suite", "filter at the floor", "cap the books" is
    only true while a specific value holds somewhere in the tree, and those
    values drift silently: the floor threshold lives in two tools, the book cap
    lives in the corpus and in the checker, and a copied constant that disagrees
    with its twin produces two correct-looking answers.

    So each entry names a file, a value, and optionally the *other* files that
    must carry the same value (`mirrors`). A mirror that has drifted is a hard
    failure: that is the single-source-of-truth defect, caught where it starts
    rather than after two answers disagree.

    `scope: host` entries describe this machine (an interpreter path) and are
    reported as warnings elsewhere, the same distinction `box_profile.py` and
    `tools/platform_claims.py` make between unknown and absent.
    """
    problems: list[str] = []
    warnings: list[str] = []
    seen = set()
    for index, config in enumerate(configs):
        where = f"configs[{index:d}]"
        if not isinstance(config, dict):
            problems.append(f"{where}: must be an object")
            continue
        cid = config.get("id")
        if not isinstance(cid, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", cid or ""):
            problems.append(f"{where}: id must be a lowercase slug")
        elif cid in seen:
            problems.append(f"{where}: duplicate id {cid!r}")
        else:
            seen.add(cid)
        if isinstance(cid, str) and cid:
            where = f"configs[{cid}]"

        if (
            not isinstance(config.get("name"), str)
            or not config.get("name", "").strip()
        ):
            problems.append(f"{where}: name is empty -- say what the setting is for")
        scope = config.get("scope", "repo")
        if scope not in CONFIG_SCOPES:
            problems.append(f"{where}: scope must be one of {CONFIG_SCOPES}")
        kind = config.get("kind")
        if kind not in CONFIG_KINDS:
            problems.append(f"{where}: kind must be one of {CONFIG_KINDS}")
            continue

        detail = config.get("detail", "")
        for text in (config.get("governs"), config.get("remedy")):
            if not isinstance(text, str) or not text.strip():
                problems.append(
                    f"{where}: `governs` and `remedy` are both required -- a "
                    "setting with no consequence and no repair is trivia"
                )
                break
        remedy_problems = _provenance_problems(
            config.get("remedy"), where + ".remedy", repo
        )
        problems.extend(p for p in remedy_problems if "does not exist" in p)

        files = []
        if config.get("file"):
            files.append((config["file"], False))
        for mirror in config.get("mirrors") or []:
            files.append((mirror, True))
        if not files and kind != "path":
            problems.append(f"{where}: names no `file`")

        value = config.get("value")
        if kind in ("text", "json") and value is None:
            problems.append(f"{where}: a {kind} config needs `value`")

        if kind == "path":
            # A path config names a thing, not a line in a file: the interpreter,
            # a directory, a store. Checked once, outside the file loop.
            text = str(value)
            if not ((Path(repo) / text).exists() or Path(text).exists()):
                message = f"{where}: declared path does not exist here: {text}"
                if scope == "host":
                    warnings.append("HOST-DIFFERS " + message)
                else:
                    problems.append(message)
            continue

        for rel, is_mirror in files:
            rel = str(rel)
            path = Path(repo) / rel
            label = f"{where}.mirrors[{rel}]" if is_mirror else where
            if not path.exists():
                problems.append(f"{label}: file does not exist: {rel}")
                continue
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                problems.append(f"{label}: unreadable: {rel} ({exc})")
                continue

            if kind == "text":
                anchor = config.get("anchor")
                needle = str(value)
                if anchor:
                    hit = any(
                        needle in line and anchor in line for line in raw.splitlines()
                    )
                    if not hit:
                        message = (
                            f"{label}: no line in {rel} carries {needle!r} with {anchor!r} -- the value "
                            "drifted from the corpus"
                        )
                    else:
                        continue
                elif needle in raw:
                    continue
                else:
                    message = f"{label}: {needle!r} not found in {rel}"
                if scope == "host":
                    warnings.append("HOST-DIFFERS " + message)
                else:
                    problems.append(message)
            elif kind == "json":
                try:
                    document = json.loads(raw)
                except json.JSONDecodeError as exc:
                    problems.append(f"{label}: {rel} is not JSON ({exc})")
                    continue
                key = config.get("key")
                if not isinstance(key, str) or not key.strip():
                    problems.append(f"{label}: a json config needs `key`")
                    continue
                node = document
                for part in key.split("."):
                    if isinstance(node, dict) and part in node:
                        node = node[part]
                    else:
                        node = None
                        break
                if node is None:
                    problems.append(f"{label}: {rel} has no key {key!r}")
                elif not _same_scalar(node, value):
                    problems.append(
                        f"{label}: {rel}[{key}] is {node!r}, the corpus says {value!r}"
                    )

        if detail:
            _text_problems(detail, where + ".detail")
    return problems, warnings


def _same_scalar(left, right) -> bool:
    """Compare a declared value with what the file holds, numerically when both
    sides are numbers so that 20 and "20" are the same setting and 0.70 vs 0.7 is
    the same threshold."""
    try:
        return float(left) == float(right)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(left).strip() == str(right).strip()


def validate(data: dict, repo: Path = REPO) -> dict:
    """Validate, and RETURN the diagnostics. Never mutate the corpus.

    A validator with a side effect is not a predicate: two runs over the same
    dict would disagree about what it says, and a test that reuses a fixture
    would inherit the first reading's counts.
    """
    problems: list[str] = []
    warnings: list[str] = []
    canon_text = (
        MANDATES.read_text(encoding="utf-8", errors="replace")
        if MANDATES.exists()
        else None
    )
    canon = canon_rules.rule_blocks(canon_text) if canon_text is not None else None
    try:
        domains = declared_domains(repo)
    except CorpusError as exc:
        problems.append(str(exc))
        domains = None
    try:
        evidence_ids = harvest_ids(repo)
    except CorpusError as exc:
        problems.append(str(exc))
        evidence_ids = None

    unknown = set(data) - TOP_KEYS
    if unknown:
        problems.append(f"unknown top-level key(s) {sorted(unknown)}")
    if data.get("schema") != SCHEMA:
        problems.append(
            "schema must be {!r}, found {!r}".format(SCHEMA, data.get("schema"))
        )
    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        problems.append("title is empty")
    status = data.get("status")
    if status not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("updated", ""))):
        problems.append("updated must be YYYY-MM-DD")

    # A COPY: filling in a default must not edit the corpus it is judging.
    limits = dict(data.get("limits") or {})
    if not isinstance(data.get("limits", {}), dict):
        problems.append("limits must be an object")
    unknown = set(limits) - set(CEILINGS)
    if unknown:
        problems.append(f"unknown limits key(s) {sorted(unknown)}")
    for name, ceiling in sorted(CEILINGS.items()):
        value = limits.get(name, DEFAULT_LIMITS[name])
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            problems.append(f"limits.{name} must be a positive integer")
            limits[name] = DEFAULT_LIMITS[name]
        elif value > ceiling:
            problems.append(
                f"limits.{name} may not exceed {ceiling:d}; a cap the author can raise "
                "is not a cap"
            )
            limits[name] = ceiling

    # The configuration layer. Absent is a warning rather than a failure, because
    # a corpus can be written before its settings are pinned; present and drifted
    # is a failure, because the corpus's own instructions then describe a tree
    # that does not exist.
    configs = data.get("configs")
    if configs is None:
        warnings.append(
            "no `configs` section: this corpus states rules without "
            "pinning the settings that make them true"
        )
        configs = []
    elif not isinstance(configs, list):
        problems.append("configs must be a list")
        configs = []
    else:
        config_problems, config_warnings = _config_problems(configs, repo)
        problems.extend(config_problems)
        warnings.extend(config_warnings)

    edition = data.get("edition")
    if edition is not None:
        if not isinstance(edition, dict):
            problems.append("edition must be an object")
        else:
            unknown = set(edition) - EDITION_KEYS
            if unknown:
                problems.append(f"unknown edition key(s) {sorted(unknown)}")
            for key in sorted(EDITION_KEYS):
                if (
                    not isinstance(edition.get(key), str)
                    or not edition.get(key, "").strip()
                ):
                    problems.append(f"edition.{key} is empty")

    glossary = data.get("glossary", [])
    if not isinstance(glossary, list):
        problems.append("glossary must be a list")
        glossary = []
    for index, entry in enumerate(glossary):
        where = f"glossary[{index:d}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: must be an object")
            continue
        unknown = set(entry) - GLOSSARY_KEYS
        if unknown:
            problems.append(f"{where}: unknown key(s) {sorted(unknown)}")
        for key in ("term", "gloss"):
            if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                problems.append(f"{where}: {key} is empty")
        problems.extend(_text_problems(entry.get("gloss"), f"{where} gloss"))
        if isinstance(entry.get("gloss"), str) and DIGIT_RE.search(entry["gloss"]):
            problems.extend(_provenance_problems(entry.get("source"), where, repo))

    books = data.get("books")
    if not isinstance(books, list) or not books:
        problems.append("books must be a non-empty list")
        books = []
    if isinstance(limits.get("max_books"), int) and len(books) > limits["max_books"]:
        problems.append(
            "{:d} books declared, limit is {:d} -- retire one to add one".format(
                len(books), limits["max_books"]
            )
        )

    index: dict[str, dict[int, dict[int, dict]]] = {}
    citations: list[tuple[str, str]] = []  # (verse ref, citation)
    seen_text: dict[str, list[str]] = {}

    for position, book in enumerate(books):
        where = f"books[{position:d}]"
        if not isinstance(book, dict):
            problems.append(f"{where}: must be an object")
            continue
        unknown = set(book) - BOOK_KEYS
        if unknown:
            problems.append(f"{where}: unknown key(s) {sorted(unknown)}")
        identifier = book.get("id")
        if not isinstance(identifier, str) or not re.match(
            r"^[a-z][a-z0-9_]*$", identifier
        ):
            problems.append(f"{where}: id must be lower_snake_case")
            continue
        where = f"book {identifier!r}"
        if identifier in index:
            problems.append(f"{where}: duplicate book id")
            continue
        for key in ("name", "subtitle"):
            if not isinstance(book.get(key), str) or not book.get(key, "").strip():
                problems.append(f"{where}: {key} is empty")
        if book.get("genre") not in GENRES:
            problems.append(f"{where}: genre must be one of {GENRES}")
        if "domain" in book:
            domain = book["domain"]
            if domains is None:
                problems.append(
                    f"{where}: {DOMAINS_MODULE} is unreadable, so the declared domain {domain!r} "
                    "cannot be verified"
                )
            elif domain not in domains:
                problems.append(
                    "{}: domain {!r} is not declared in {} (declared: {})".format(
                        where, domain, DOMAINS_MODULE, ", ".join(sorted(domains))
                    )
                )
        if status == "complete" and "introduction" not in book:
            problems.append(
                f"{where}: a complete canon gives every book an introduction"
            )
        introduction = book.get("introduction")
        if introduction is not None:
            if not isinstance(introduction, dict):
                problems.append(f"{where}: introduction must be an object")
            else:
                unknown = set(introduction) - INTRODUCTION_KEYS
                if unknown:
                    problems.append(
                        f"{where}: unknown introduction key(s) {sorted(unknown)}"
                    )
                problems.extend(
                    _prose_block_problems(
                        introduction.get("paragraphs"),
                        introduction.get("sources", []),
                        f"{where} introduction",
                        repo,
                    )
                )
        chapters = book.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            problems.append(f"{where}: chapters must be a non-empty list")
            continue
        if (
            isinstance(limits.get("max_chapters_per_book"), int)
            and len(chapters) > limits["max_chapters_per_book"]
        ):
            problems.append(
                "{}: {:d} chapters, limit is {:d}".format(
                    where, len(chapters), limits["max_chapters_per_book"]
                )
            )
        index[identifier] = {}
        for chapter_position, chapter in enumerate(chapters):
            cwhere = f"{where} chapter {chapter_position + 1:d}"
            if not isinstance(chapter, dict):
                problems.append(f"{cwhere}: must be an object")
                continue
            unknown = set(chapter) - CHAPTER_KEYS
            if unknown:
                problems.append(f"{cwhere}: unknown key(s) {sorted(unknown)}")
            number = chapter.get("number")
            if number != chapter_position + 1:
                problems.append(
                    f"{cwhere}: chapter numbering must be contiguous from 1; "
                    f"found {number!r} at position {chapter_position + 1:d}"
                )
                continue
            verses = chapter.get("verses")
            if not isinstance(verses, list) or not verses:
                problems.append(f"{cwhere}: verses must be a non-empty list")
                continue
            if (
                isinstance(limits.get("max_verses_per_chapter"), int)
                and len(verses) > limits["max_verses_per_chapter"]
            ):
                problems.append(
                    "{}: {:d} verses, limit is {:d}".format(
                        cwhere, len(verses), limits["max_verses_per_chapter"]
                    )
                )
            sections = chapter.get("sections", [])
            if not isinstance(sections, list):
                problems.append(f"{cwhere}: sections must be a list")
                sections = []
            previous = 0
            for section_position, section in enumerate(sections):
                swhere = f"{cwhere} section {section_position + 1:d}"
                if not isinstance(section, dict):
                    problems.append(f"{swhere}: must be an object")
                    continue
                unknown = set(section) - SECTION_KEYS
                if unknown:
                    problems.append(f"{swhere}: unknown key(s) {sorted(unknown)}")
                start = section.get("before_verse")
                if (
                    not isinstance(start, int)
                    or isinstance(start, bool)
                    or not 1 <= start <= len(verses)
                ):
                    problems.append(
                        f"{swhere}: before_verse must name a verse in this chapter "
                        f"(1..{len(verses):d})"
                    )
                elif start <= previous:
                    problems.append(
                        f"{swhere}: sections must ascend; {start:d} follows {previous:d}"
                    )
                else:
                    previous = start
                heading = section.get("heading")
                problems.extend(_text_problems(heading, f"{swhere} heading"))
                if isinstance(heading, str) and DIGIT_RE.search(heading):
                    problems.append(
                        f"{swhere}: a heading is a label, not a claim -- a figure "
                        "belongs in a verse, where it must name its "
                        "command"
                    )
            if status == "complete" and (
                not sections or sections[0].get("before_verse") != 1
            ):
                problems.append(
                    f"{cwhere}: a complete canon opens every chapter with a "
                    "section heading at verse 1"
                )
            index[identifier][number] = {}
            for verse_position, verse in enumerate(verses):
                vwhere = f"{where} chapter {number:d} verse {verse_position + 1:d}"
                if not isinstance(verse, dict):
                    problems.append(f"{vwhere}: must be an object")
                    continue
                unknown = set(verse) - VERSE_KEYS
                if unknown:
                    problems.append(f"{vwhere}: unknown key(s) {sorted(unknown)}")
                if verse.get("number") != verse_position + 1:
                    problems.append(
                        "{}: verse numbering must be contiguous from 1; "
                        "found {!r}".format(vwhere, verse.get("number"))
                    )
                    continue
                text = verse.get("text")
                problems.extend(_text_problems(text, vwhere))
                index[identifier][number][verse_position + 1] = verse
                if isinstance(text, str):
                    key = " ".join(text.split()).lower()
                    seen_text.setdefault(key, []).append(
                        f"{identifier} {number:d}:{verse_position + 1:d}"
                    )
                if isinstance(text, str) and DIGIT_RE.search(text):
                    problems.extend(
                        _provenance_problems(verse.get("source"), vwhere, repo)
                    )
                citations_list = verse.get("cites", [])
                if not isinstance(citations_list, list):
                    problems.append(f"{vwhere}: cites must be a list")
                    citations_list = []
                for citation in citations_list:
                    if not isinstance(citation, str):
                        problems.append(
                            f"{vwhere}: citation {citation!r} is not a string"
                        )
                        continue
                    citations.append(
                        (
                            f"{identifier} {number:d}:{verse_position + 1:d}",
                            citation,
                        )
                    )
                if "statute" in verse:
                    problems.extend(
                        _statute_problems(
                            verse["statute"], vwhere, repo, canon, canon_text
                        )
                    )
                if "practice" in verse:
                    problems.extend(
                        _practice_problems(
                            verse["practice"], vwhere, repo, evidence_ids
                        )
                    )
                variants = verse.get("variants", [])
                if not isinstance(variants, list):
                    problems.append(f"{vwhere}: variants must be a list")
                    variants = []
                for variant_position, variant in enumerate(variants):
                    xwhere = f"{vwhere} variant {variant_position + 1:d}"
                    if not isinstance(variant, dict):
                        problems.append(f"{xwhere}: must be an object")
                        continue
                    unknown = set(variant) - VARIANT_KEYS
                    if unknown:
                        problems.append(f"{xwhere}: unknown key(s) {sorted(unknown)}")
                    if (
                        not isinstance(variant.get("reading"), str)
                        or not variant.get("reading", "").strip()
                    ):
                        problems.append(
                            f"{xwhere}: reading is empty (name the manuscript "
                            "or the source of the variant)"
                        )
                    problems.extend(_text_problems(variant.get("text"), xwhere))
                    if (
                        not isinstance(variant.get("source"), str)
                        or not variant.get("source", "").strip()
                    ):
                        problems.append(
                            f"{xwhere}: a variant must say where its reading comes "
                            "from; that is the whole point of an apparatus"
                        )
                annotations = verse.get("annotations", [])
                if not isinstance(annotations, list):
                    problems.append(f"{vwhere}: annotations must be a list")
                    annotations = []
                if (
                    isinstance(limits.get("max_annotations_per_verse"), int)
                    and len(annotations) > limits["max_annotations_per_verse"]
                ):
                    problems.append(
                        "{}: {:d} annotations, limit is {:d} -- a verse with a "
                        "page of notes has stopped being annotated".format(
                            vwhere,
                            len(annotations),
                            limits["max_annotations_per_verse"],
                        )
                    )
                for note_position, annotation in enumerate(annotations):
                    nwhere = f"{vwhere} annotation {note_position + 1:d}"
                    if not isinstance(annotation, dict):
                        problems.append(f"{nwhere}: must be an object")
                        continue
                    unknown = set(annotation) - ANNOTATION_KEYS
                    if unknown:
                        problems.append(f"{nwhere}: unknown key(s) {sorted(unknown)}")
                    if annotation.get("kind") not in ANNOTATION_KINDS:
                        problems.append(
                            f"{nwhere}: kind must be one of {ANNOTATION_KINDS} -- a reader is "
                            "entitled to know whether a note is a reading "
                            "or a claim"
                        )
                    problems.extend(
                        _text_problems(annotation.get("note"), f"{nwhere} note")
                    )
                    if isinstance(annotation.get("note"), str) and DIGIT_RE.search(
                        annotation["note"]
                    ):
                        problems.extend(
                            _provenance_problems(annotation.get("source"), nwhere, repo)
                        )

    # Citations and glossary pointers resolve after the whole index exists, so a
    # verse may cite forward: the canon is read as a whole, not streamed.
    for source_ref, citation in citations:
        problem = _resolve_citation(citation, index, repo)
        if problem:
            problems.append(f"{source_ref} {problem}")
    for position, entry in enumerate(glossary):
        reference = entry.get("see") if isinstance(entry, dict) else None
        if not isinstance(reference, str):
            continue
        problem = _resolve_citation(reference, index, repo)
        if problem:
            problems.append(
                "glossary[{:d}]: see {}".format(
                    position, problem.replace("cites ", "", 1)
                )
            )

    for key, refs in seen_text.items():
        if len(refs) > 1:
            warnings.append(
                "the same verse text appears {:d} times ({}) -- usually a "
                "paste, occasionally a refrain".format(len(refs), ", ".join(refs))
            )

    cited_by = reference_index(books)
    if status == "complete":
        for identifier, chapters in index.items():
            for number, verses in chapters.items():
                for verse_number, verse in verses.items():
                    ref = f"{identifier} {number:d}:{verse_number:d}"
                    if (
                        cited_by.get(ref)
                        or verse.get("cites")
                        or "statute" in verse
                        or verse.get("annotations")
                        or verse.get("variants")
                    ):
                        continue
                    problems.append(
                        f"{ref}: a complete canon has no verse that does no "
                        "work -- cite it, or give it a note, a statute or "
                        "an apparatus"
                    )

    if problems:
        raise CorpusError(
            "{} failed {:d} check(s):\n  - {}".format(
                CORPUS.name, len(problems), "\n  - ".join(problems)
            )
        )

    verses_flat = [
        verse
        for book in books
        for chapter in book.get("chapters", [])
        for verse in chapter.get("verses", [])
    ]
    return {
        "books": len(books),
        "chapters": sum(len(book.get("chapters", [])) for book in books),
        "verses": len(verses_flat),
        "citations": len(citations),
        "statutes": sum(1 for verse in verses_flat if "statute" in verse),
        "variants": sum(len(verse.get("variants", []) or []) for verse in verses_flat),
        "annotations": sum(
            len(verse.get("annotations", []) or []) for verse in verses_flat
        ),
        "sections": sum(
            len(chapter.get("sections", []) or [])
            for book in books
            for chapter in book.get("chapters", [])
        ),
        "glossary": len(glossary),
        "introductions": sum(1 for book in books if "introduction" in book),
        "configs": len(configs),
        "orphans": sorted(ref for ref, refs in cited_by.items() if not refs),
        "warnings": warnings,
    }


def iter_verses(books: Sequence[dict]):
    """Yield (ref, verse) in corpus order."""
    for book in books:
        for chapter in book.get("chapters", []):
            for verse in chapter.get("verses", []):
                yield (
                    "{} {:d}:{:d}".format(
                        book["id"], chapter["number"], verse["number"]
                    ),
                    verse,
                )


def reference_index(books: Sequence[dict]) -> dict[str, list[str]]:
    """Who cites each verse: the marginal column of a study Bible.

    Also the honest source for the orphan question -- a verse nothing points at
    is doing no work in a canon whose whole purpose is to be cited.
    """
    cited_by: dict[str, list[str]] = {}
    for ref, verse in iter_verses(books):
        cited_by.setdefault(ref, [])
        for citation in verse.get("cites", []) or []:
            if isinstance(citation, str) and REF_RE.match(citation):
                normalized = " ".join(citation.split())
                if normalized != ref:
                    cited_by.setdefault(normalized, []).append(ref)
    return cited_by


# --------------------------------------------------------------------------- #
# The readable edition                                                        #
# --------------------------------------------------------------------------- #


def render_edition(data: dict, corpus_label: str = "docs/bible/bible.json") -> str:
    """Deterministic markdown: headings in place, notes beside their verse.

    Inline notes rather than markdown footnote ids, because ids collide across
    chapters and a section-scoped marker is what a reader wants. Nothing here is
    timestamped: the edition must be byte-identical on a re-run, or the drift
    check would fail on a clock.

    ``corpus_label`` is the path the edition claims to have been generated from.
    It is a parameter because the header was hard-coded to the canon, and an
    edition of a second corpus that names the first corpus as its source is a
    false provenance line -- the kind of defect a reader cannot detect from the
    file itself.
    """
    cited_by = reference_index(data.get("books", []))
    lines = ["# {}".format(data.get("title", "Untitled"))]
    edition = data.get("edition")
    if isinstance(edition, dict):
        lines.extend(
            ["", "*{}*".format(edition.get("name", "")), "", edition.get("basis", "")]
        )
    lines.extend(
        [
            "",
            "Status: **{}** · updated {}.".format(
                data.get("status"), data.get("updated")
            ),
            "",
            f"_Generated from `{corpus_label}` by "
            "`python tools/bible_check.py --render --write`. Do not edit this "
            "file: edit the corpus._",
        ]
    )
    for book in data.get("books", []):
        lines.extend(["", "## {}".format(book.get("name", book.get("id"))), ""])
        # An unset subtitle would print a bare "### ", which reads as a defect
        # in the edition rather than as an omission in the corpus.
        if book.get("subtitle"):
            lines.extend(["### {}".format(book["subtitle"]), ""])
        register = book.get("genre") or ""
        if book.get("domain"):
            register = (
                "{} · domain `{}`".format(register, book["domain"])
                if register
                else "domain `{}`".format(book["domain"])
            )
        if register:
            lines.extend([f"*{register}*", ""])
        introduction = book.get("introduction")
        if isinstance(introduction, dict):
            lines.append("")
            for paragraph in introduction.get("paragraphs", []):
                lines.extend([paragraph, ""])
            sources = introduction.get("sources") or []
            if sources:
                lines.append("*Sources: {}*".format("; ".join(sources)))
                lines.append("")
        for chapter in book.get("chapters", []):
            number = chapter.get("number")
            lines.extend(["", "#### {} {:d}".format(book.get("name", ""), number), ""])
            headings = {
                section.get("before_verse"): section.get("heading")
                for section in chapter.get("sections", []) or []
            }
            for verse in chapter.get("verses", []):
                verse_number = verse.get("number")
                if verse_number in headings:
                    lines.extend([f"##### {headings[verse_number]}", ""])
                trailing = []
                if verse.get("cites"):
                    trailing.append("see " + ", ".join(verse["cites"]))
                if isinstance(verse.get("statute"), dict):
                    statute = verse["statute"]
                    trailing.append(
                        "statute {} → `{}`".format(
                            statute.get("rule"), statute.get("check")
                        )
                    )
                suffix = (" *({})*".format("; ".join(trailing))) if trailing else ""
                lines.append(
                    "**{:d}** {}{}".format(verse_number, verse.get("text", ""), suffix)
                )
                notes = (verse.get("annotations") or []) + (verse.get("variants") or [])
                if notes:
                    lines.append("")  # a blockquote after a bare line is a trap
                for annotation in verse.get("annotations", []) or []:
                    source = annotation.get("source")
                    lines.append(
                        "> **{}** — {}{}".format(
                            annotation.get("kind"),
                            annotation.get("note"),
                            (f" (`{source}`)") if source else "",
                        )
                    )
                for variant in verse.get("variants", []) or []:
                    lines.append(
                        "> **Apparatus** — *{}*: {} ({})".format(
                            variant.get("reading"),
                            variant.get("text"),
                            variant.get("source"),
                        )
                    )
                practice = verse.get("practice")
                if isinstance(practice, dict):
                    lines.extend(
                        [
                            "",
                            "**Practice** — *{}*".format(practice.get("symptom")),
                            "",
                            "- *cause*: {}".format(practice.get("cause")),
                            "- *detect*: `{}`".format(practice.get("detection")),
                            "- *remedy*: {}".format(practice.get("remedy")),
                            "- *evidence*: {}".format(
                                ", ".join(practice.get("evidence", []))
                            ),
                        ]
                    )
                lines.append("")
            marginal = [
                "{:d} — cited by {}".format(int(ref.split(":")[1]), ", ".join(refs))
                for ref, refs in sorted(
                    (
                        (ref, refs)
                        for ref, refs in cited_by.items()
                        if ref.startswith("{} {:d}:".format(book.get("id"), number))
                        and refs
                    ),
                    key=lambda pair: int(pair[0].split(":")[1]),
                )
            ]
            if marginal:
                lines.extend(["_Marginal: {}._".format("; ".join(marginal)), ""])
    glossary = data.get("glossary") or []
    if glossary:
        lines.extend(["", "## Glossary", ""])
        for entry in glossary:
            see = (" (see {})".format(entry["see"])) if entry.get("see") else ""
            lines.append(
                "- **{}** — {}{}".format(entry.get("term"), entry.get("gloss"), see)
            )
    lines.append("")
    # One blank line between blocks, never three: the gap is generated by
    # composition, so it must not depend on which branch wrote the last line.
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def render_index(data: dict) -> str:
    """Who cites whom, and which verses nothing points at."""
    books = data.get("books", [])
    cited_by = reference_index(books)
    lines = ["# Index of references", ""]
    for ref, verse in iter_verses(books):
        refs = cited_by.get(ref, [])
        cites = verse.get("cites", []) or []
        if not refs and not cites:
            continue
        lines.append(
            "{:<18} {}".format(
                ref, ("cited by " + ", ".join(refs)) if refs else "cited by nothing"
            )
        )
    orphans = [
        ref
        for ref, _verse in iter_verses(books)
        if not cited_by.get(ref)
        and not _verse.get("cites")
        and "statute" not in _verse
        and not _verse.get("annotations")
        and not _verse.get("variants")
    ]
    lines.extend(["", "## Verses that do no work", ""])
    lines.extend([f"- {ref}" for ref in orphans] or ["none"])
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Generations: the import graph, which cannot be embellished                   #
# --------------------------------------------------------------------------- #


def import_graph(root: Path = SRC) -> tuple[dict[str, dict[str, int]], list[str]]:
    """Top-level packages under `root`, and how often one imports another."""
    if not root.is_dir():
        return {}, []
    packages = sorted(
        {
            path.parts[0]
            for path in (
                p.relative_to(root)
                for p in root.rglob("*.py")
                if "__pycache__" not in p.parts
            )
            if len(path.parts) > 1
        }
    )
    known = set(packages)
    edges: dict[str, dict[str, int]] = {package: {} for package in packages}
    unreadable: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root)
        if len(relative.parts) < 2:
            continue
        source = relative.parts[0]
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            unreadable.append(str(relative).replace("\\", "/"))
            continue
        targets: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # relative: stays inside the package
                    continue
                if node.module:
                    targets.append(node.module)
        for target in targets:
            head = target.split(".", 1)[0]
            if head in known and head != source:
                edges[source][head] = edges[source].get(head, 0) + 1
    return edges, unreadable


def render_genealogy(
    edges: dict[str, dict[str, int]], unreadable: Sequence[str]
) -> str:
    total_edges = sum(sum(level.values()) for level in edges.values())
    houses = len(edges)
    lines = [
        "# The generations of the tree",
        "",
        'Generated, never composed: each "begat" below is an import edge found by',
        "reading `src/` with `ast`. Re-run it and the numbers must be the same.",
        "",
        "```bash",
        "python tools/bible_check.py --genealogy --write",
        "```",
        "",
        f"{houses:d} houses, {total_edges:d} edges between them.",
        "",
    ]
    for house in sorted(edges, key=lambda name: (-len(edges[name]), name)):
        children = edges[house]
        if not children:
            lines.append(f"And **{house}** begat no other house.")
            continue
        ordered = sorted(children, key=lambda name: (-children[name], name))
        named = [f"**{child}**" for child in ordered[:3]]
        if len(ordered) > 3:
            rest = len(ordered) - 3
            lines.append(
                "And **{}** begat {}, and of the rest there were {:d}.".format(
                    house, ", ".join(named), rest
                )
            )
        elif len(ordered) == 1:
            lines.append(f"And **{house}** begat {named[0]}.")
        else:
            lines.append(
                "And **{}** begat {} and {}.".format(
                    house, ", ".join(named[:-1]), named[-1]
                )
            )
    lines.extend(["", "| house | begat | edges out |", "|---|---|---|"])
    for house in sorted(edges):
        children = (
            ", ".join(
                sorted(edges[house], key=lambda name: (-edges[house][name], name))
            )
            or "--"
        )
        lines.append(f"| {house} | {children} | {sum(edges[house].values()):d} |")
    if unreadable:
        lines.extend(
            [
                "",
                "Unreadable on this run (not counted): {}.".format(
                    ", ".join(unreadable)
                ),
            ]
        )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The gate                                                                    #
# --------------------------------------------------------------------------- #


def _drift(path: Path, expected: str) -> str | None:
    if not path.exists():
        return f"{path.name} is absent; run the command in its header to create it"
    if path.read_text(encoding="utf-8", errors="replace") != expected:
        return (
            f"{path.name} is stale relative to this run; regenerate it (the file is "
            "generated, so editing it is not a fix)"
        )
    return None


def _label(path: Path) -> str:
    """The corpus path as a reader would type it, for a provenance line."""
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return Path(path).as_posix()


def edition_path(corpus_path: Path) -> Path:
    """The generated edition that belongs to a corpus.

    A second corpus generated into the first corpus's edition would fail every
    drift check by construction, and a `--write` would overwrite the canon with
    it. Deriving the name from the corpus keeps one generated file per corpus,
    and keeps the canonical path byte-identical to the one every earlier
    reference names.
    """
    corpus_path = Path(corpus_path)
    if corpus_path.resolve() == Path(CORPUS).resolve():
        return EDITION
    return corpus_path.parent / (corpus_path.stem.upper() + "_BIBLE.md")


def generated_drift(
    root: Path, data: dict, corpus_path: Path | None = None
) -> list[str]:
    """Every generated file compared against what this run would write now.

    Split out of check() so the comparison can be exercised without a real
    corpus on disk: a drift check that only runs against HEAD cannot be shown
    to fire, and one that has never fired is unknown rather than working.

    ``corpus_path`` defaults to the canon, because that is the corpus the
    genealogy and the book edition belong to. When it names a different corpus,
    only that corpus's own edition is compared: holding an alternate corpus to
    the canon's generated file compares two different documents and calls the
    difference staleness.
    """
    problems: list[str] = []
    canonical = (
        corpus_path is None or Path(corpus_path).resolve() == Path(CORPUS).resolve()
    )
    expected_files = [
        (
            Path(root) / "docs" / "bible" / "GENEALOGY.md",
            render_genealogy(*import_graph(Path(root) / "src")),
        )
    ]
    if canonical:
        expected_files.append(
            (
                Path(root) / "docs" / "bible" / "BOOK_OF_THE_TREE.md",
                render_edition(data),
            )
        )
    else:
        label = _label(Path(corpus_path))
        expected_files.append(
            (edition_path(Path(corpus_path)), render_edition(data, label))
        )
    for path, expected in expected_files:
        problem = _drift(path, expected)
        if problem:
            problems.append(problem)
    return problems


def check(root: Path = REPO, corpus_path: Path = CORPUS) -> tuple[bool, list[str]]:
    """Validate the corpus AND both generated files. Messages, not a bare bool."""
    try:
        data = load(corpus_path)
        diagnostics = validate(data, root)
    except CorpusError as exc:
        return False, [str(exc)]
    messages: list[str] = []
    problems = generated_drift(root, data, corpus_path)
    # The harvest ledger is generated too. A corpus that cites evidence from a
    # ledger nobody regenerated is the same defect as a stale genealogy: the
    # citations still parse and no longer describe the sources.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bible_harvest

        stale_paths, newer = bible_harvest.stale(root)
        problems.extend("harvest: " + message for message in stale_paths)
        if newer:
            messages.append(
                f"harvest: {newer:d} observation(s) recorded since the snapshot "
                "(re-run tools/bible_harvest.py --write to fold them in)"
            )
    except ImportError as exc:  # pragma: no cover - wiring
        messages.append(f"harvest: ledger not checked ({exc})")
    for warning in diagnostics["warnings"]:
        messages.append("warning: " + warning)
    if problems:
        return False, problems + messages
    messages.insert(
        0,
        "{} -- {}: {:d} book(s), {:d} chapter(s), {:d} verse(s), {:d} "
        "citation(s), {:d} statute(s), {:d} variant(s), {:d} annotation(s), "
        "{:d} section(s), {:d} gloss(es), {:d} introduction(s), {:d} "
        "config(s); generated files current".format(
            data.get("title"),
            data.get("status"),
            diagnostics["books"],
            diagnostics["chapters"],
            diagnostics["verses"],
            diagnostics["citations"],
            diagnostics["statutes"],
            diagnostics["variants"],
            diagnostics["annotations"],
            diagnostics["sections"],
            diagnostics["glossary"],
            diagnostics["introductions"],
            diagnostics["configs"],
        ),
    )
    return True, messages


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check", action="store_true", help="exit 1 on any defect (the gate)"
    )
    group.add_argument(
        "--genealogy",
        action="store_true",
        help="derive the generations from the import graph",
    )
    group.add_argument(
        "--render", action="store_true", help="print the readable edition"
    )
    group.add_argument(
        "--index",
        action="store_true",
        help="who cites whom, and the verses that do no work",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the generated file instead of printing it",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--corpus", default=str(CORPUS))
    args = parser.parse_args(argv)

    corpus_path = Path(args.corpus).resolve()
    if args.genealogy:
        edges, unreadable = import_graph()
        text = render_genealogy(edges, unreadable)
        if args.write:
            GENEALOGY.parent.mkdir(parents=True, exist_ok=True)
            GENEALOGY.write_text(text, encoding="utf-8", newline="\n")
            print(
                f"wrote {GENEALOGY.relative_to(REPO)} ({len(edges):d} houses, {sum(sum(level.values()) for level in edges.values()):d} edges)"
            )
            return 0
        sys.stdout.write(text)
        return 0

    try:
        data = load(corpus_path)
        diagnostics = validate(data, REPO)
    except CorpusError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.check:
        ok, messages = check(REPO, corpus_path)
        for message in messages:
            print(message)
        print("clean" if ok else "FAILED")
        return 0 if ok else 1
    if args.render:
        text = render_edition(data, _label(corpus_path))
        if args.write:
            target = edition_path(corpus_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            print(
                f"wrote {target.relative_to(REPO)} ({len(text.splitlines()):d} lines)"
            )
            return 0
        sys.stdout.write(text)
        return 0
    if args.index:
        sys.stdout.write(render_index(data))
        return 0
    if args.json:
        print(
            json.dumps(
                {
                    "title": data.get("title"),
                    "status": data.get("status"),
                    "summary": diagnostics,
                },
                indent=1,
            )
        )
        return 0

    print(
        "{} -- {}, {:d} book(s), {:d} chapter(s), {:d} verse(s), {:d} citation(s), "
        "{:d} statute(s), {:d} variant(s), {:d} annotation(s), {:d} section(s), "
        "{:d} gloss(es), {:d} introduction(s)".format(
            data.get("title"),
            data.get("status"),
            diagnostics["books"],
            diagnostics["chapters"],
            diagnostics["verses"],
            diagnostics["citations"],
            diagnostics["statutes"],
            diagnostics["variants"],
            diagnostics["annotations"],
            diagnostics["sections"],
            diagnostics["glossary"],
            diagnostics["introductions"],
        )
    )
    for warning in diagnostics["warnings"]:
        print("warning: " + warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
