import httpx

from app.features.policy_matcher import youth_center_client
from app.features.policy_matcher.youth_center_client import (
    RawYouthPolicy,
    _bounded_income_krw_or_none,
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
                "pvsnInstGroupCd": "0054002",
                "schoolCd": "0049005",
                "lclsfNm": "주거",
                "mclsfNm": "전월세 및 주거급여 지원",
                "bizPrdBgngYmd": "20260101",
                "bizPrdEndYmd": "20261231",
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
                "lclsfNm": "주거",
                "mclsfNm": "임대주택",
                "bizPrdBgngYmd": "        ",
                "bizPrdEndYmd": "        ",
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
    # 100만 이상은 이미 원 단위로 보고 그대로 쓴다(아래 만원 단위 변환 테스트와
    # 대비되는 케이스 — youth_center_client._bounded_income_krw_or_none 참고).
    assert first.max_income_krw == 26_000_000
    assert first.marital_status == ""
    assert first.region_code == "11110,11140"
    assert first.institution_group_code == "0054002"
    assert first.school_code == "0049005"


def test_parse_youth_policy_json_converts_small_income_values_from_manwon_to_krw():
    # 실측(2026-09-03): earnMinAmt/earnMaxAmt는 대부분 "만원" 단위로 내려온다
    # (예: "5000" = 5,000만원). 100만 미만 값은 ×10,000해서 원으로 환산해야 한다.
    payload = {
        "result": {
            "youthPolicyList": [
                {
                    "plcyNo": "P777",
                    "plcyNm": "소득 조건이 만원 단위로 내려오는 정책",
                    "earnMinAmt": "3000",
                    "earnMaxAmt": "6000",
                }
            ]
        }
    }
    policy = _parse_youth_policy_json(payload)[0]
    assert policy.min_income_krw == 30_000_000
    assert policy.max_income_krw == 60_000_000


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


def test_parse_youth_policy_json_parses_category_and_period_fields():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    first = policies[0]
    assert first.large_category == "주거"
    assert first.mid_category == "전월세 및 주거급여 지원"
    assert first.apply_start_ymd == "20260101"
    assert first.apply_end_ymd == "20261231"


def test_parse_youth_policy_json_treats_blank_period_as_none():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    second = policies[1]
    assert second.apply_start_ymd is None
    assert second.apply_end_ymd is None


def test_parse_youth_policy_json_uses_aplyYmd_not_bizPrd_for_status_dates():
    # 실측 버그: 신청기간(aplyYmd)은 이미 끝났는데 사업기간(bizPrdBgngYmd/EndYmd)은
    # 한참 남아있는 정책이 실제로 있었다 — apply_start/end_ymd는 반드시 aplyYmd에서
    # 파싱해야 하고, bizPrd* 값을 쓰면 안 된다.
    payload = {
        "result": {
            "youthPolicyList": [
                {
                    "plcyNo": "P999",
                    "plcyNm": "신청기간과 사업기간이 다른 정책",
                    "aplyYmd": "20260501 ~ 20260619",
                    "bizPrdBgngYmd": "20260701",
                    "bizPrdEndYmd": "20270630",
                }
            ]
        }
    }
    policy = _parse_youth_policy_json(payload)[0]
    assert policy.apply_start_ymd == "20260501"
    assert policy.apply_end_ymd == "20260619"


def test_parse_youth_policy_json_falls_back_to_ref_url_when_apply_url_blank():
    # 실측: aplyUrlAddr(신청 URL)이 비어있는 레코드가 전체의 67%나 됐고, 그중
    # 상당수는 refUrlAddr1/2(참고 URL)에 실제 접근 가능한 링크가 있었다 —
    # 프론트에서 href=""로 렌더돼 "자세히 보기"를 눌러도 제자리인 버그의 원인.
    payload = {
        "result": {
            "youthPolicyList": [
                {
                    "plcyNo": "P001",
                    "plcyNm": "신청 URL이 비어있는 정책",
                    "aplyUrlAddr": "",
                    "refUrlAddr1": "https://example.com/ref1",
                    "refUrlAddr2": "https://example.com/ref2",
                },
                {
                    "plcyNo": "P002",
                    "plcyNm": "신청 URL과 참고 URL1이 둘 다 비어있는 정책",
                    "aplyUrlAddr": "",
                    "refUrlAddr1": "",
                    "refUrlAddr2": "https://example.com/ref2-only",
                },
                {
                    "plcyNo": "P003",
                    "plcyNm": "URL이 아예 없는 정책",
                    "aplyUrlAddr": "",
                    "refUrlAddr1": "",
                    "refUrlAddr2": "",
                },
            ]
        }
    }
    policies = _parse_youth_policy_json(payload)
    assert policies[0].apply_url == "https://example.com/ref1"
    assert policies[1].apply_url == "https://example.com/ref2-only"
    assert policies[2].apply_url == ""


def test_parse_youth_policy_json_prefers_apply_url_over_ref_url_when_both_present():
    policies = _parse_youth_policy_json(SAMPLE_PAYLOAD)
    assert policies[0].apply_url == "https://example.com/apply/1"


def test_bounded_income_krw_or_none_converts_manwon_scale_values():
    assert _bounded_income_krw_or_none("5000") == 50_000_000  # 5,000만원
    assert _bounded_income_krw_or_none("9999") == 99_990_000  # 사실상 상한없음 sentinel로 추정
    assert _bounded_income_krw_or_none("999999") == 9_999_990_000  # 100만 미만 경계값


def test_bounded_income_krw_or_none_keeps_already_krw_scale_values_as_is():
    assert _bounded_income_krw_or_none("1000000") == 1_000_000  # 100만 경계값(이상)
    assert _bounded_income_krw_or_none("43056240") == 43_056_240


def test_bounded_income_krw_or_none_treats_zero_and_blank_as_no_limit():
    assert _bounded_income_krw_or_none("0") is None
    assert _bounded_income_krw_or_none(None) is None
    assert _bounded_income_krw_or_none("") is None


def test_fetch_all_policies_requests_a_large_page_size(monkeypatch):
    from app.features.policy_matcher import youth_center_client

    monkeypatch.setattr(youth_center_client.settings, "youth_center_api_key", "test-key")

    captured = {}

    def fake_get(url, params, timeout):
        captured["params"] = params
        return httpx.Response(
            status_code=200, json=SAMPLE_PAYLOAD, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(youth_center_client.httpx, "get", fake_get)

    policies = youth_center_client.fetch_all_policies()

    assert captured["params"]["pageSize"] >= 3000
    assert len(policies) == 2
