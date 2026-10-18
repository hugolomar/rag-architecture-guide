"""Development suite: 14 cases for local iteration.

Every case fails with ``NotImplementedError`` until ``retrieve_fn`` is replaced
with the pipeline. That red run is the scaffolding baseline. Do not point this
module at the protected suite.
"""

import pytest

from evals.harness import load_dev_suite, parametrize_suite, run_evaluation_case


@pytest.mark.parametrize("case", parametrize_suite(load_dev_suite(), pytest.mark.dev))
def test_dev_case(case, retrieve_fn, generate_fn):
    """Score one development case through the phases its ``target_stage`` selects."""
    run_evaluation_case(case, retrieve_fn, generate_fn)
