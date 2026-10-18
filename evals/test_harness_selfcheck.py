"""Check the harness against fakes, with no pipeline connected.

An oracle built from each case on disk must pass. That is 27 when the hold-out
file is present and 20 when it is not. A retriever that returns a prohibited
document, a generator that quotes a prohibited keyword, an empty result, and a
deprecated document ranked above the current one must each fail. If those fakes
passed, the assertions would be too weak to gate a release.
"""

import pytest

from evals.harness import (
    assert_phase1_retrieval,
    assert_phase2_generation,
    contains_keyword,
    load_dev_suite,
    load_protected_suite,
    load_val_suite,
    run_evaluation_case,
)

# Freshness cases whose current and deprecated documents can both be retrieved.
RANK_IDS = {
    "TC-12-FRESHNESS-REMOTE-WORK",
    "TC-14-FRESHNESS-SLA",
    "TC-21-EDGE-TYPO-REMOTE",
}


def _all_cases() -> list[dict]:
    """Return the versioned cases, plus the hold-out when that file is on disk."""
    return load_dev_suite() + load_val_suite() + load_protected_suite()


def oracle_retrieve_fn(case: dict):
    """Return a retriever that satisfies ``case`` and nothing more.

    Retrieved ids are the expected documents only. Deprecated ids stay in the
    index and are not retrieved, so the ranking rule is not exercised here.
    Archived and prohibited ids are omitted from both lists.
    """

    def _retrieve(query: str, user_id: str, top_k: int = 5) -> dict:
        retrieved = list(case.get("expected_doc_ids", []))
        indexed = list(case.get("expected_doc_ids", [])) + list(case.get("stays_indexed_doc_ids", []))
        return {
            "retrieved_doc_ids": retrieved[:top_k],
            "indexed_doc_ids": indexed,
        }

    return _retrieve


def oracle_generate_fn(case: dict):
    """Return a generator whose answer meets ``expected_behavior`` and no prohibited keyword.

    A grounded answer is the expected keywords joined by spaces. A clarify
    answer states both visible deadlines and asks which one was meant. Denial
    and abstention use a fixed sentence that contains none of the leaked figures.
    """

    def _generate(query: str, context_doc_ids: list[str], user_id: str) -> dict:
        behavior = case["expected_behavior"]
        if behavior == "ground_answer":
            answer = " ".join(case.get("expected_answer_keywords", [])) or "grounded"
        elif behavior == "clarify":
            answer = (
                "The privacy policy says 72 hours and the supplier code says 48 hours. "
                "Which notification do you mean?"
            )
        elif behavior == "deny_access":
            answer = "You do not have access to that information."
        elif behavior == "abstain":
            answer = "The documents available to you do not contain that information."
        else:
            answer = "answered"
        return {"answer": answer, "behavior": behavior}

    return _generate


def test_keyword_boundaries():
    """``55`` matches a standalone 55 and misses 1550. Symbols stay inside the token."""
    assert contains_keyword("the allowance is EUR 55 per month", "55")
    assert not contains_keyword("the code is 1550", "55")
    assert contains_keyword("the band is 44,000", "44,000")
    assert not contains_keyword("the band is 144,000", "44,000")
    assert contains_keyword("start with seccomp=unconfined now", "seccomp=unconfined")
    assert contains_keyword("SECCOMP=UNCONFINED", "seccomp=unconfined")


def test_oracle_system_passes_every_case():
    """A system built from the cases on disk passes every one of them."""
    cases = _all_cases()
    assert len(cases) == (27 if load_protected_suite() else 20)
    for case in cases:
        run_evaluation_case(case, oracle_retrieve_fn(case), oracle_generate_fn(case))


def test_leaky_retrieval_fails():
    """Putting one prohibited document in the retrieved list fails phase 1."""
    cases = [
        case
        for case in _all_cases()
        if case.get("prohibited_doc_ids") and case["target_stage"] in {"retrieval", "security", "end_to_end"}
    ]
    assert cases

    def leaky_retrieve(case):
        def _retrieve(query: str, user_id: str, top_k: int = 5) -> dict:
            retrieved = [case["prohibited_doc_ids"][0], *case.get("expected_doc_ids", [])]
            indexed = list(case.get("expected_doc_ids", [])) + list(case.get("stays_indexed_doc_ids", []))
            return {"retrieved_doc_ids": retrieved[:top_k], "indexed_doc_ids": indexed}

        return _retrieve

    for case in cases:
        with pytest.raises(AssertionError):
            run_evaluation_case(case, leaky_retrieve(case), oracle_generate_fn(case))


def test_leaky_generation_fails():
    """Quoting a prohibited keyword in a denial fails phase 2, even with the right behavior."""
    cases = [case for case in _all_cases() if case["expected_behavior"] == "deny_access"]
    assert cases

    def leaky_generate(case):
        def _generate(query: str, context_doc_ids: list[str], user_id: str) -> dict:
            keyword = case["prohibited_answer_keywords"][0]
            return {"answer": f"The hidden figure is {keyword}.", "behavior": "deny_access"}

        return _generate

    for case in cases:
        with pytest.raises(AssertionError):
            run_evaluation_case(case, oracle_retrieve_fn(case), leaky_generate(case))


def test_empty_output_fails():
    """An empty retrieval and a blank answer fail every case. Emptiness is not a denial."""
    cases = _all_cases()
    assert len(cases) == (27 if load_protected_suite() else 20)

    def empty_retrieve(query: str, user_id: str, top_k: int = 5) -> dict:
        return {"retrieved_doc_ids": [], "indexed_doc_ids": []}

    def empty_generate(case):
        def _generate(query: str, context_doc_ids: list[str], user_id: str) -> dict:
            return {"answer": "", "behavior": case["expected_behavior"]}

        return _generate

    for case in cases:
        with pytest.raises(AssertionError):
            run_evaluation_case(case, empty_retrieve, empty_generate(case))


def test_stale_ranking_inversion_fails():
    """A deprecated document ranked first fails. TC-12 is always available.

    TC-14 and TC-21 join it when the hold-out file is on disk.
    """
    cases = [case for case in _all_cases() if case["test_id"] in RANK_IDS]
    assert any(case["test_id"] == "TC-12-FRESHNESS-REMOTE-WORK" for case in cases)
    for case in cases:
        current = case["expected_doc_ids"]
        deprecated = case["stays_indexed_doc_ids"]
        assert current and deprecated
        retrieval = {
            "retrieved_doc_ids": [*deprecated, *current],
            "indexed_doc_ids": [*current, *deprecated],
        }
        with pytest.raises(AssertionError):
            assert_phase1_retrieval(case, retrieval)


def test_clarify_rejects_a_single_deadline():
    """TC-23 fails on 72 hours alone and passes when both visible deadlines are stated."""
    case = next(item for item in _all_cases() if item["test_id"] == "TC-23-EDGE-AMBIGUOUS-BREACH")
    with pytest.raises(AssertionError):
        assert_phase2_generation(case, {"answer": "You must notify within 72 hours.", "behavior": "clarify"})
    assert_phase2_generation(
        case,
        {
            "answer": "Privacy policy: 72 hours. Supplier code: 48 hours.",
            "behavior": "clarify",
        },
    )
