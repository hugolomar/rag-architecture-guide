"""Validation suite: 6 cases scored on every pull request.

A failure here is a regression and blocks the merge. The protected suite is
not imported. Tuning a prompt against these six cases is how the validation
set stops being a hold-out; treat a repeated failure as a reason to add a new
case, not to edit these until they pass for the wrong reason.
"""

import pytest

from evals.harness import load_val_suite, parametrize_suite, run_evaluation_case


@pytest.mark.parametrize("case", parametrize_suite(load_val_suite(), pytest.mark.validation))
def test_val_case(case, retrieve_fn, generate_fn):
    """Score one validation case through the phases its ``target_stage`` selects."""
    run_evaluation_case(case, retrieve_fn, generate_fn)
