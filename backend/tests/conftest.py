"""Pytest compatibility markers for legacy benchmark expectations.

P0.1 intentionally removed fabricated fallback haircut recommendations. The
legacy benchmark still calls VisagismAnalyzer without measured context or an
LLM result and expects haircut names to be present. That expectation no longer
matches the fail-closed P0.1 contract, so mark only that single legacy assertion
as expected to fail until the benchmark itself is rewritten around grounded
inputs.
"""

import pytest


def pytest_collection_modifyitems(items):
    legacy_node = (
        "tests/test_visagism_benchmark.py::"
        "TestHaircuts::test_at_least_five_haircuts"
    )
    for item in items:
        if item.nodeid.endswith(legacy_node):
            item.add_marker(
                pytest.mark.xfail(
                    reason=(
                        "Legacy benchmark expects fabricated fallback cuts; "
                        "P0.1 correctly returns no ungrounded recommendations"
                    ),
                    strict=False,
                )
            )
