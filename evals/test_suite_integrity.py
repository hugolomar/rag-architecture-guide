"""Check the suites against the manifest and the user catalog.

These tests do not call ``retrieve_fn`` or ``generate_fn``. They pass while the
pipeline is still a stub. A failure means a case and ``data/manifest.json`` or
``data/users.json`` have diverged.
"""

import json
from pathlib import Path

from evals.harness import iter_case_doc_ids, load_dev_suite, load_protected_suite, load_val_suite

ROOT = Path(__file__).resolve().parents[1]


def _cases() -> list[dict]:
    """Return the versioned cases, plus the hold-out when that file is on disk."""
    return load_dev_suite() + load_val_suite() + load_protected_suite()


def _manifest() -> dict[str, dict]:
    """Return manifest records keyed by ``doc_id``."""
    records = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    return {record["doc_id"]: record for record in records}


def _users() -> dict[str, dict]:
    """Return user records keyed by ``user_id``.

    The catalog field is ``groups``. Cases copy that list into ``user_groups``.
    """
    records = json.loads((ROOT / "data" / "users.json").read_text(encoding="utf-8"))
    return {record["user_id"]: record for record in records}


def test_suite_lengths_and_unique_ids():
    """Development and validation are 14 and 6. The hold-out, when present, adds 7.

    No ``test_id`` is reused across the cases that are on disk.
    """
    dev = load_dev_suite()
    val = load_val_suite()
    protected = load_protected_suite()
    assert len(dev) == 14
    assert len(val) == 6
    if protected:
        assert len(protected) == 7
    ids = [case["test_id"] for case in dev + val + protected]
    assert len(ids) == (27 if protected else 20)
    assert len(set(ids)) == len(ids)


def test_every_doc_id_exists_in_the_manifest():
    """Every document named by a case is a row in ``data/manifest.json``."""
    manifest = _manifest()
    missing = [
        f"{case['test_id']} {field} {doc_id}"
        for case in _cases()
        for field, doc_id in iter_case_doc_ids(case)
        if doc_id not in manifest
    ]
    assert missing == []


def test_lifecycle_ids_match_manifest_status():
    """Deprecated ids are the ones that stay indexed. Archived ids are the ones removed."""
    manifest = _manifest()
    for case in _cases():
        for doc_id in case.get("stays_indexed_doc_ids", []):
            assert manifest[doc_id]["status"] == "deprecated", case["test_id"]
        for doc_id in case.get("absent_from_index_doc_ids", []):
            assert manifest[doc_id]["status"] == "archived", case["test_id"]


def test_users_match_the_catalog():
    """Each case copies ``user_id``, ``user_principal_name``, and ``groups`` unchanged."""
    users = _users()
    for case in _cases():
        user = users[case["user_id"]]
        assert user["user_principal_name"] == case["user_principal_name"], case["test_id"]
        assert user["groups"] == case["user_groups"], case["test_id"]


def test_expected_docs_are_visible_to_the_user():
    """A document the answer must use is one this user's groups are allowed to read."""
    manifest = _manifest()
    for case in _cases():
        groups = set(case["user_groups"])
        for doc_id in case.get("expected_doc_ids", []):
            allowed = set(manifest[doc_id]["allowed_groups"])
            assert groups.intersection(allowed), f"{case['test_id']} cannot read {doc_id}"


def test_deny_access_cases_name_prohibited_keywords():
    """A denial names the strings that count as a leak. An empty list would pass a leak."""
    for case in _cases():
        if case["expected_behavior"] == "deny_access":
            assert case.get("prohibited_answer_keywords"), case["test_id"]
