import httpx

from app.features.policy_matcher import youth_center_client
from app.features.policy_matcher.youth_center_client import (
    RawYouthPolicy,
    _parse_youth_policy_json,
    fetch_policies,
)

SAMPLE_PAYLOAD = {
    "resultCode": 200,
    "resultMessage": "성공적으로 데이터를 가지고 왔습니다.",
    "result": {
        "pagging": {"totCount": 2, "pageNum": 1, "pageSize": 100},
        "youthPolicyList": [
            {
                "plcyNo": "P202601",
                "plcyNm": "청년 월세 지원",
                "plcyExplnCn": "월 20만원씩 최대 12개월 지원",
                "aplyUrlAddr": "https://example.com/apply/1",
                "aplyYmd": "20260101 ~ 20261231",
                "sprtTrgtMinAge": "19",
                "sprtTrgtMaxAge": "34",
                "earnMinAmt": "0",
                "earnMaxAmt": "26000000",
                "mrgSttsCd": "",
                "zipCd": "11110,11140",
            },
            {
                "plcyNo": "",
                "plcyNm": "신혼부부 전세임대주택",
                "plcyExplnCn": "시세 대비 저렴한 전세임대",
                "aplyUrlAddr": "https://example.com/apply/2",
                "aplyYmd": "",
                "sprtTrgtMinAge": "0",
                "sprtTrgtMaxAge": "0",
                "earnMinAmt": "0",
                "earnMaxAmt": "0",
                "mrgSttsCd": "기혼",
                "zipCd": "",
            },
        ],
    },
}


def test_parse_youth_policy_json_parses_full_record():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    first = policies[0]
    assert first.policy_id == "P202601"
    assert first.policy_name == "청년 월세 지원"
    assert first.description == "월 20만원씩 최대 12개월 지원"
    assert first.apply_url == "https://example.com/apply/1"
    assert first.application_period == "20260101 ~ 20261231"
    assert first.min_age == 19
    assert first.max_age == 34
    assert first.min_income_krw is None
    assert first.max_income_krw == 26_000_000
    assert first.marital_status == ""
    assert first.region_code == "11110,11140"


def test_parse_youth_policy_json_treats_zero_sentinel_as_no_limit():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    second = policies[1]
    assert second.policy_id == ""
    assert second.marital_status == "기혼"
    assert second.min_age is None
    assert second.max_age is None
    assert second.min_income_krw is None
    assert second.max_income_krw is None
    assert second.application_period == "상시"
    assert second.region_code == ""


def test_parse_youth_policy_json_returns_all_items():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    assert len(policies) == 2


def test_fetch_policies_calls_api_with_key_and_parses_response(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return httpx.Response(
            status_code=200, json=SAMPLE_PAYLOAD, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    policies = fetch_policies()

    assert captured["url"] == "https://www.youthcenter.go.kr/go/ythip/getPlcy"
    assert captured["params"]["apiKeyNm"] == "test-key"
    assert captured["params"]["rtnType"] == "json"
    assert len(policies) == 2
    assert policies[0].policy_name == "청년 월세 지원"


def test_fetch_policies_raises_runtime_error_and_skips_request_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "")

    def fake_get(*args, **kwargs):
        raise AssertionError("should not call httpx.get")

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    try:
        fetch_policies()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_fetch_policies_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    def fake_get(url, params, timeout):
        return httpx.Response(status_code=500, text="server error", request=httpx.Request("GET", url))

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    try:
        fetch_policies()
        assert False, "expected httpx.HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
