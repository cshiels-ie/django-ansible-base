import pytest

from ansible_base.lib.workload_identity import AAPMetricsServiceScope, SCOPE_REGISTRY


def test_scope_registered():
    assert "aap_metrics_collection" in SCOPE_REGISTRY
    assert SCOPE_REGISTRY["aap_metrics_collection"] is AAPMetricsServiceScope


def test_name():
    assert AAPMetricsServiceScope.name == "aap_metrics_collection"


def test_list_claims():
    assert AAPMetricsServiceScope.list_claims() == ["aap_metrics_target_service"]


def test_get_target_claim_names_to_sub_stubs():
    expected = {"aap_metrics_target_service": "service"}
    assert AAPMetricsServiceScope.get_target_claim_names_to_sub_stubs() == expected


@pytest.mark.parametrize(
    "claims, expected_sub",
    [
        ({"aap_metrics_target_service": "controller"}, "workload_type:aap_metrics_collection:service:controller"),
        ({"aap_metrics_target_service": "eda"}, "workload_type:aap_metrics_collection:service:eda"),
        ({"aap_metrics_target_service": "hub"}, "workload_type:aap_metrics_collection:service:hub"),
        ({}, "workload_type:aap_metrics_collection:service:"),
    ],
)
def test_generate_sub_claim(claims, expected_sub):
    assert AAPMetricsServiceScope.generate_sub_claim(claims) == expected_sub


def test_target_claim_constant_is_valid_claim():
    assert AAPMetricsServiceScope.CLAIM_TARGET_SERVICE in AAPMetricsServiceScope.list_claims()


def test_populate_claims_not_implemented():
    scope = AAPMetricsServiceScope()
    with pytest.raises(NotImplementedError):
        scope.populate_claims({})
