"""Load the evaluation suites and score retrieval and generation.

Nothing in this module calls a model or reads an index. A runner supplies
``retrieve_fn`` and ``generate_fn``. Until the pipeline exists those callables
raise ``NotImplementedError``; an empty result is not a stand-in, because a
deny case would pass without a filter ever running.

Phase 1 scores document ids. It runs for ``retrieval``, ``security``, and
``end_to_end``. Phase 2 scores the answer text. It runs for ``generation``,
``security``, and ``end_to_end``. A ``retrieval`` case stops after phase 1.
A ``generation`` case never asks the retriever, and receives
``expected_doc_ids`` as its context.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

# Repository root. Suite paths are resolved from here, not from the shell cwd.
ROOT = Path(__file__).resolve().parents[1]

# target_stage values that have a retrieval half and a generation half.
PHASE1_STAGES = {"retrieval", "security", "end_to_end"}
PHASE2_STAGES = {"generation", "security", "end_to_end"}

# Case fields that name documents. The integrity tests walk this tuple.
_DOC_FIELDS = (
    "expected_doc_ids",
    "prohibited_doc_ids",
    "stays_indexed_doc_ids",
    "absent_from_index_doc_ids",
)


def _resolve(path_str: str) -> Path:
    """Return an absolute path. Relative paths are rooted at the repository."""
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _load_suite(path_str: str, expected_len: int) -> list[dict]:
    """Read a suite file and refuse it when the case count has drifted.

    The lengths are part of the split in note 03. A silent extra case would
    move a question from one suite into another without a failing check.
    """
    path = _resolve(path_str)
    cases = json.loads(path.read_text(encoding="utf-8"))
    if len(cases) != expected_len:
        raise AssertionError(f"{path} has {len(cases)} cases, expected {expected_len}")
    return cases


def load_dev_suite() -> list[dict]:
    """Return the 14 development cases used while changing the pipeline."""
    return _load_suite("evals/suites/dev_set.json", 14)


def load_val_suite() -> list[dict]:
    """Return the 6 validation cases scored on every pull request."""
    return _load_suite("evals/suites/val_set.json", 6)


def load_protected_suite() -> list[dict]:
    """Return the 7 hold-out cases, or an empty list when the file is absent.

    The default path is ``evals/.secrets/protected_set.json``.
    ``RAG_PROTECTED_SUITE_PATH`` replaces it. A missing file is not an error:
    local runs score the versioned suites only. A file that exists with a
    count other than 7 is an error. A release job sets ``RAG_PROTECTED_REQUIRED``
    and treats the empty list as a failed gate; that check lives in the runner.
    """
    path = _resolve(os.getenv("RAG_PROTECTED_SUITE_PATH", "evals/.secrets/protected_set.json"))
    if not path.is_file():
        return []
    cases = json.loads(path.read_text(encoding="utf-8"))
    if len(cases) != 7:
        raise AssertionError(f"{path} has {len(cases)} cases, expected 7")
    return cases


def contains_keyword(text: str, keyword: str) -> bool:
    """Return whether ``keyword`` occurs in ``text`` as its own token.

    The comparison is case-insensitive. A boundary is required only on an end
    of the keyword that is alphanumeric, so ``55`` does not match ``155``
    while ``44,000`` and ``seccomp=unconfined`` still match.
    """
    if keyword == "":
        return False
    pattern = re.escape(keyword)
    if keyword[0].isalnum():
        pattern = rf"(?<![0-9A-Za-z]){pattern}"
    if keyword[-1].isalnum():
        pattern = rf"{pattern}(?![0-9A-Za-z])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def assert_phase1_retrieval(case: dict, retrieval_result: dict, top_k: int = 3) -> None:
    """Score document ids. Raise ``AssertionError`` on the first broken rule.

    ``retrieval_result["retrieved_doc_ids"]`` is an ordered list, most relevant
    first, no longer than ``top_k``. ``indexed_doc_ids`` is every document
    currently stored, in any order.

    Rules, in order:

    - No ``prohibited_doc_ids`` entry appears in the retrieved list.
    - For a retrieval, security, or end-to-end case, every ``expected_doc_ids``
      entry was retrieved.
    - Every ``stays_indexed_doc_ids`` entry is still in the index. These are
      the deprecated documents.
    - Every ``absent_from_index_doc_ids`` entry is gone from the index and
      from the retrieved list. These are the archived documents.
    - When a current document and its deprecated partner are both retrieved,
      the current document ranks first.
    """
    test_id = case.get("test_id", "<unknown>")
    retrieved = retrieval_result["retrieved_doc_ids"]
    indexed = retrieval_result["indexed_doc_ids"]
    if not isinstance(retrieved, list):
        raise AssertionError(f"{test_id}: retrieved_doc_ids must be an ordered list")

    if len(retrieved) > top_k:
        raise AssertionError(f"{test_id}: retrieved {len(retrieved)} documents, top_k is {top_k}")

    for doc_id in case.get("prohibited_doc_ids", []):
        if doc_id in retrieved:
            raise AssertionError(f"{test_id}: prohibited document {doc_id} was retrieved")

    if case["target_stage"] in PHASE1_STAGES:
        for doc_id in case.get("expected_doc_ids", []):
            if doc_id not in retrieved:
                raise AssertionError(f"{test_id}: expected document {doc_id} was not retrieved")

    for doc_id in case.get("stays_indexed_doc_ids", []):
        if doc_id not in indexed:
            raise AssertionError(f"{test_id}: deprecated document {doc_id} is missing from the index")

    for doc_id in case.get("absent_from_index_doc_ids", []):
        if doc_id in indexed or doc_id in retrieved:
            raise AssertionError(f"{test_id}: archived document {doc_id} is still in the index or the results")

    for current_id in case.get("expected_doc_ids", []):
        if current_id not in retrieved:
            continue
        current_rank = retrieved.index(current_id)
        for deprecated_id in case.get("stays_indexed_doc_ids", []):
            if deprecated_id in retrieved and not current_rank < retrieved.index(deprecated_id):
                raise AssertionError(
                    f"{test_id}: deprecated {deprecated_id} outranks current {current_id}"
                )


def _asks_clarifying_question(answer: str) -> bool:
    """Return whether the answer asks the user to choose, rather than picking a deadline.

    A question mark is the signal. TC-23 passes this way or by stating both
    visible deadlines, 72 hours and 48 hours.
    """
    return "?" in answer


def assert_phase2_generation(case: dict, gen_result: dict) -> None:
    """Score the answer text. Raise ``AssertionError`` on the first broken rule.

    ``gen_result["answer"]`` is the text shown to the user.
    ``gen_result["behavior"]`` is one of ``ground_answer``, ``deny_access``,
    ``abstain``, and ``clarify``, and it must equal the case.

    A prohibited keyword fails every behavior, including a denial. Denial and
    abstention must also say something: a blank string would hide whether the
    system refused or simply returned nothing. ``clarify`` fails when the
    answer states a single deadline and does not ask which notification was meant.
    """
    test_id = case.get("test_id", "<unknown>")
    answer = gen_result.get("answer", "")
    behavior = gen_result.get("behavior")

    for keyword in case.get("prohibited_answer_keywords", []):
        if contains_keyword(answer, keyword):
            raise AssertionError(f"{test_id}: answer contains prohibited keyword {keyword!r}")

    expected = case["expected_behavior"]
    if expected == "ground_answer":
        if behavior != "ground_answer":
            raise AssertionError(f"{test_id}: behavior {behavior!r} is not ground_answer")
        for keyword in case.get("expected_answer_keywords", []):
            if not contains_keyword(answer, keyword):
                raise AssertionError(f"{test_id}: answer is missing keyword {keyword!r}")
    elif expected == "deny_access":
        if behavior != "deny_access":
            raise AssertionError(f"{test_id}: behavior {behavior!r} is not deny_access")
        if not str(answer).strip():
            raise AssertionError(f"{test_id}: deny_access returned an empty answer")
    elif expected == "abstain":
        if behavior != "abstain":
            raise AssertionError(f"{test_id}: behavior {behavior!r} is not abstain")
        if not str(answer).strip():
            raise AssertionError(f"{test_id}: abstain returned an empty answer")
    elif expected == "clarify":
        if behavior != "clarify":
            raise AssertionError(f"{test_id}: behavior {behavior!r} is not clarify")
        states_both = contains_keyword(answer, "72 hours") and contains_keyword(answer, "48 hours")
        if not (states_both or _asks_clarifying_question(answer)):
            raise AssertionError(
                f"{test_id}: clarify collapsed to a single deadline without asking which notification is meant"
            )
    else:
        raise AssertionError(f"{test_id}: unknown expected_behavior {expected!r}")


def run_evaluation_case(case: dict, retrieve_fn, generate_fn) -> None:
    """Run the phases selected by ``case["target_stage"]``.

    ``retrieve_fn(query, user_id, top_k=3)`` resolves the user itself. The case
    does not hand over ``user_groups``. It returns ``retrieved_doc_ids`` and
    ``indexed_doc_ids``. The harness passes ``top_k=3``, the API default.

    ``generate_fn(query, context_doc_ids, user_id)`` returns ``answer`` and
    ``behavior``. A generation-only case passes ``expected_doc_ids`` as the
    context, because retrieval did not run. Security and end-to-end cases pass
    the documents phase 1 actually returned.
    """
    stage = case["target_stage"]
    retrieval = None
    if stage in PHASE1_STAGES:
        retrieval = retrieve_fn(case["query"], case["user_id"], top_k=3)
        assert_phase1_retrieval(case, retrieval)

    if stage in PHASE2_STAGES:
        if stage == "generation":
            context = list(case.get("expected_doc_ids", []))
        else:
            context = list(retrieval["retrieved_doc_ids"])
        generated = generate_fn(case["query"], context, case["user_id"])
        assert_phase2_generation(case, generated)


def parametrize_suite(cases: list[dict], suite_mark):
    """Build pytest parameters, one per case, with the marks declared in ``pytest.ini``.

    Each parameter carries the suite mark (``dev``, ``validation``, or
    ``release_gate``), the case's ``target_stage``, and its ``category``.
    ``--strict-markers`` rejects a stage or category that the ini does not name.
    """
    return [
        pytest.param(
            case,
            id=case["test_id"],
            marks=[
                suite_mark,
                getattr(pytest.mark, case["target_stage"]),
                getattr(pytest.mark, case["category"]),
            ],
        )
        for case in cases
    ]


def iter_case_doc_ids(case: dict):
    """Yield ``(field_name, doc_id)`` for every document the case mentions."""
    for field in _DOC_FIELDS:
        for doc_id in case.get(field, []):
            yield field, doc_id
