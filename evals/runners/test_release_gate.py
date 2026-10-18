"""Protected suite: the release gate.

The hold-out file is not versioned. Locally it lives at
``evals/.secrets/protected_set.json``. A release job injects another copy with
``RAG_PROTECTED_SUITE_PATH``. This module is not on the default ``testpaths``.

When the file is missing, the module skips, so a normal ``pytest`` run stays
green. ``RAG_PROTECTED_REQUIRED=1`` turns that absence into a failure. That is
the setting the release job uses.
"""

import os

import pytest

from evals.harness import load_protected_suite, parametrize_suite, run_evaluation_case

_cases = load_protected_suite()

if not _cases and os.getenv("RAG_PROTECTED_REQUIRED") != "1":
    pytest.skip(
        "Protected benchmark suite omitted locally "
        "(requires RAG_PROTECTED_SUITE_PATH or evals/.secrets/protected_set.json)",
        allow_module_level=True,
    )


if not _cases:

    def test_protected_suite_is_required():
        """A release job with ``RAG_PROTECTED_REQUIRED=1`` must supply the hold-out file."""
        pytest.fail("RAG_PROTECTED_REQUIRED=1 but the protected suite file was not found")

else:

    @pytest.mark.parametrize("case", parametrize_suite(_cases, pytest.mark.release_gate))
    def test_release_gate_case(case, retrieve_fn, generate_fn):
        """Score one protected case through the phases its ``target_stage`` selects."""
        run_evaluation_case(case, retrieve_fn, generate_fn)
