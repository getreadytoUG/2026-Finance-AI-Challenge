import httpx

from app.features.policy_matcher import youth_center_client
from app.features.policy_matcher.youth_center_client import (
    RawYouthPolicy,
    _parse_youth_policy_xml,
    fetch_policies,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<youthPolicyList>
  <youthPolicy>
    <plcyNm>청년 월세 지원</plcyNm>
    <plcyExplnCn>월 20만원씩 최대 12개월 지원</plcyExplnCn>
    <aplyUrlAddr>https://example.com/apply/1</aplyUrlAddr>
    <aplyYmd>20260101 ~ 20261231</aplyYmd>
    <sprtTrgtMinAge>19</sprtTrgtMinAge>
    <sprtTrgtMaxAge>34</sprtTrgtMaxAge>
    <earnMinAmt></earnMinAmt>
    <earnMaxAmt>26000000</earnMaxAmt>
    <mrgSttsCd></mrgSttsCd>
    <zipCd>서울</zipCd>
  </youthPolicy>
  <youthPolicy>
    <plcyNm>신혼부부 전세임대주택</plcyNm>
    <plcyExplnCn>시세 대비 저렴한 전세임대</plcyExplnCn>
    <aplyUrlAddr>https://example.com/apply/2</aplyUrlAddr>
    <aplyYmd></aplyYmd>
    <sprtTrgtMinAge></sprtTrgtMinAge>
    <sprtTrgtMaxAge></sprtTrgtMaxAge>
    <earnMinAmt></earnMinAmt>
    <earnMaxAmt></earnMaxAmt>
    <mrgSttsCd>기혼</mrgSttsCd>
    <zipCd></zipCd>
  </youthPolicy>
</youthPolicyList>
"""


def test_parse_youth_policy_xml_parses_full_record():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    first = policies[0]
    assert first.policy_name == "청년 월세 지원"
    assert first.description == "월 20만원씩 최대 12개월 지원"
    assert first.apply_url == "https://example.com/apply/1"
    assert first.application_period == "20260101 ~ 20261231"
    assert first.min_age == 19
    assert first.max_age == 34
    assert first.min_income_krw is None
    assert first.max_income_krw == 26_000_000
    assert first.marital_status == ""
    assert first.region_code == "서울"


def test_parse_youth_policy_xml_defaults_missing_fields_to_none_or_empty():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    second = policies[1]
    assert second.marital_status == "기혼"
    assert second.min_age is None
    assert second.max_age is None
    assert second.application_period == "상시"
    assert second.region_code == ""


def test_parse_youth_policy_xml_returns_all_items():
    policies = _parse_youth_policy_xml(SAMPLE_XML)
    assert len(policies) == 2


def test_fetch_policies_calls_api_with_key_and_query_and_parses_response(monkeypatch):
    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return httpx.Response(status_code=200, text=SAMPLE_XML, request=httpx.Request("GET", url))

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    policies = fetch_policies(query="서울")

    assert captured["url"] == "https://www.youthcenter.go.kr/opi/youthPlcyList.do"
    assert captured["params"]["openApiVlak"] == "test-key"
    assert captured["params"]["query"] == "서울"
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
