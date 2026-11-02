from app.routes.reviews import execute_contradiction_audit, ContradictionRequest, build_fallback_comparison

def test_execute_contradiction_audit():
    # 1. Test with default/empty guidelines
    req = ContradictionRequest(brand_id="ASTRA", guidelines=[])
    res = execute_contradiction_audit(req)
    assert res["status"] in ("success", "degraded_fallback")
    assert res["active_guidelines_count"] >= 4
    assert len(res["conflicts"]) >= 2
    assert res["conflicts"][0]["conflict_id"] == "CONF-01"
    assert "Organic" in res["conflicts"][0]["rule_a"]
    assert "Methylparaben" in res["conflicts"][0]["rule_b"]

    # 2. Test with None payload (graceful fallback)
    res_none = execute_contradiction_audit(None)
    assert res_none["status"] in ("success", "degraded_fallback")
    assert len(res_none["conflicts"]) >= 2


def test_build_fallback_comparison():
    fallback = build_fallback_comparison(None, "Testing resilient fallback")
    assert fallback["status"] == "degraded_fallback"
    assert "best_variant" in fallback
    assert "matrix" in fallback
    assert len(fallback["results"]) >= 2
    assert fallback["metrics"]["score_delta"] > 0
