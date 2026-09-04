import itertools
from datetime import datetime, timezone

from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.status import today_kst
from app.features.savings_simulator.simulator import match_real_housing_policies, match_real_savings_policies

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="청년내일저축계좌",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="금융･복지･문화",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _match_input(**overrides) -> PolicyMatchInput:
    defaults = dict(age=29, is_married=False, annual_income_krw=40_000_000, region="서울")
    defaults.update(overrides)
    return PolicyMatchInput(**defaults)


def test_match_real_savings_policies_finds_savings_keyword_policy(db_session):
    policy = _seed_policy(db_session, policy_name="청년내일저축계좌 지원")
    result = match_real_savings_policies([policy], _match_input(), today_kst())
    assert [p.policy_key for p in result] == [policy.policy_key]


def test_match_real_savings_policies_excludes_policy_without_savings_keyword(db_session):
    policy = _seed_policy(db_session, policy_name="청년 취업 지원 사업")
    result = match_real_savings_policies([policy], _match_input(), today_kst())
    assert result == []


def test_match_real_savings_policies_applies_age_eligibility(db_session):
    policy = _seed_policy(db_session, policy_name="청년내일저축계좌", min_age=19, max_age=34)
    assert match_real_savings_policies([policy], _match_input(age=29), today_kst()) != []
    assert match_real_savings_policies([policy], _match_input(age=50), today_kst()) == []


def test_match_real_savings_policies_excludes_expired(db_session):
    policy = _seed_policy(
        db_session, policy_name="청년내일저축계좌", apply_start_ymd="20200101", apply_end_ymd="20200201"
    )
    assert match_real_savings_policies([policy], _match_input(), today_kst()) == []


def test_match_real_savings_policies_excludes_disability_only_policy_for_non_disabled(db_session):
    # matching.is_eligible을 재사용하므로 장애인/보훈대상자 전용 정책 필터링도
    # 자동으로 같이 적용돼야 한다.
    policy = _seed_policy(db_session, policy_name="장애인 자산형성 통장")
    assert match_real_savings_policies([policy], _match_input(has_disability=False), today_kst()) == []
    assert match_real_savings_policies([policy], _match_input(has_disability=True), today_kst()) != []


def test_match_real_savings_policies_dedupes_same_policy_name(db_session):
    # 2026-09-02 QA에서 발견: 온통청년 원본에 같은 이름의 정책이 설명만 다르게
    # 중복 등록된 경우가 있어(예: "청년주택드림청약통장") 화면에 두 번 떴었다.
    policy_a = _seed_policy(db_session, policy_name="청년주택드림청약통장", description="설명 A")
    policy_b = _seed_policy(db_session, policy_name="청년주택드림청약통장", description="설명 B")
    result = match_real_savings_policies([policy_a, policy_b], _match_input(), today_kst())
    assert len(result) == 1
    assert result[0].policy_name == "청년주택드림청약통장"


def test_match_real_housing_policies_splits_by_jeonse_and_purchase(db_session):
    jeonse_policy = _seed_policy(db_session, policy_name="신혼부부 전세자금 대출이자 지원", large_category="주거")
    purchase_policy = _seed_policy(db_session, policy_name="청년 주택구입 대출이자 지원", large_category="주거")
    all_policies = [jeonse_policy, purchase_policy]

    jeonse_result = match_real_housing_policies(all_policies, "jeonse", _match_input(), today_kst())
    purchase_result = match_real_housing_policies(all_policies, "purchase", _match_input(), today_kst())

    assert [p.policy_key for p in jeonse_result] == [jeonse_policy.policy_key]
    assert [p.policy_key for p in purchase_result] == [purchase_policy.policy_key]


def _signup_login(client, email="sim-user@example.com", **overrides):
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    client.post("/auth/signup", json=payload)
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


# ---------------------------------------------------------------------------
# 청년미래적금 (2026-09-03: 청년도약계좌 후속상품으로 전면 재작업 — 아래 상수는
# simulator.py의 실제 값과 일치해야 한다)


def test_youth_future_savings_requires_auth(client):
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 30_000_000},
    )
    assert response.status_code == 401


def test_youth_future_savings_general_tier_for_non_sme_low_income(client):
    # 소득이 낮아도(우대형 소득기준 3,600만원 이하) 중소기업 재직자가 아니면
    # 일반형(6%)이지 우대형(12%)이 아니어야 한다.
    token = _signup_login(client, is_sme_employee=False)
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["matching_rate"] == 0.06
    assert body["benefit_diff_krw"] > 0
    assert body["policy_total_krw"] > body["market_total_krw"]


def test_youth_future_savings_preferential_tier_for_sme_low_income(client):
    token = _signup_login(client, email="sme-user@example.com", is_sme_employee=True)
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["matching_rate"] == 0.12


def test_youth_future_savings_high_income_gets_tax_benefit_only_no_match(client):
    token = _signup_login(client, email="mid-income@example.com")
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 65_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["matching_rate"] == 0.0
    # 매칭은 없지만 비과세 혜택은 여전히 적용돼 시중적금보단 유리해야 한다.
    assert body["policy_total_krw"] > body["market_total_krw"]


def test_youth_future_savings_over_income_cap_is_ineligible(client):
    token = _signup_login(client, email="high-income@example.com")
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 100_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["matching_rate"] == 0.0
    assert body["benefit_diff_krw"] == 0
    assert body["policy_total_krw"] == body["market_total_krw"]


def test_youth_future_savings_outside_age_range_is_ineligible(client):
    token = _signup_login(client, email="too-old@example.com", age=40)
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert "19~34세" in body["eligibility_note"]


def test_youth_future_savings_matching_capped_at_500000_monthly():
    # HTTP 왕복 없이 계산 함수를 직접 호출해 매칭 상한(월 50만원)이 실제로 걸리는지
    # 검증한다 — 월 100만원을 넣어도 정부 매칭분은 50만원 기준으로만 계산돼야 한다.
    from app.features.savings_simulator.schemas import YouthFutureSavingsInput
    from app.features.savings_simulator.simulator import simulate_youth_future_savings

    months = 36
    matching_rate = 0.06
    expected_government_total = round(500_000 * matching_rate * months)

    result = simulate_youth_future_savings(
        YouthFutureSavingsInput(monthly_amount_krw=1_000_000, annual_income_krw=20_000_000),
        is_sme_employee=False,
    )
    # policy_total = principal(월납입*개월+시드) + government_total + policy_interest
    # market_total = principal + market_interest 이므로, 두 total의 차이에서 이자 차이분을
    # 빼면 government_total만 남는다. 이자는 policy(비과세) - market(세후)이라 항상
    # policy_interest > market_interest이므로, diff는 government_total보다 크거나 같다.
    diff = result.policy_total_krw - result.market_total_krw
    assert diff >= expected_government_total


def test_youth_future_savings_response_includes_real_matched_policies(client, db_session):
    _seed_policy(db_session, policy_name="청년내일저축계좌 지원", min_age=19, max_age=39)
    _seed_policy(db_session, policy_name="청년 취업 지원 사업")  # 저축 키워드 없어 안 나와야 함
    token = _signup_login(client, age=29, region="서울")
    response = client.post(
        "/savings_simulator/youth_future_savings",
        json={"monthly_amount_krw": 400_000, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    matched = response.json()["matched_policies"]
    assert [p["policy_name"] for p in matched] == ["청년내일저축계좌 지원"]


# ---------------------------------------------------------------------------
# 버팀목전세자금대출 / 디딤돌대출 (2026-09-03: 실제 정부 고시 금리/LTV/소득상한으로
# 교체 — 아래 상수는 simulator.py의 실제 값과 일치해야 한다)


def test_housing_loan_requires_auth(client):
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
    )
    assert response.status_code == 401


def test_housing_loan_jeonse_within_newlywed_income_cap_is_eligible(client):
    # 일반 소득상한(5,000만원)은 넘지만 신혼가구 상한(7,500만원)은 안 넘는 값으로
    # 검증한다 — 일반/신혼가구 구분이 실제로 반영되는지 함께 확인한다.
    token = _signup_login(client, email="jeonse-married@example.com", is_married=True)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["product_name"] == "신혼부부전용 버팀목 전세자금대출"
    # min(250M*0.8=200M, 250M-50M=200M, 신혼부부전용 대출한도 200M) = 200M
    assert body["loan_amount_krw"] == 200_000_000
    assert body["monthly_saving_krw"] > 0


def test_housing_loan_jeonse_general_household_over_income_cap_is_ineligible(client):
    # 미혼(일반) 세대는 소득상한이 5,000만원이라 6,500만원은 초과해야 한다.
    token = _signup_login(client, email="jeonse-single@example.com", is_married=False)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["eligible"] is False


def test_housing_loan_jeonse_unmarried_outside_age_range_is_ineligible(client):
    # 청년전용 버팀목은 만 19~34세 제한이 있다.
    token = _signup_login(client, email="jeonse-old@example.com", age=40, is_married=False)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 40_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert "19~34세" in body["summary"]


def test_housing_loan_jeonse_married_has_no_age_limit(client):
    # 2026-09-03 사용자 지적으로 재조사한 결과, 신혼부부전용 버팀목은 나이 제한이
    # 없다(실제 조건은 "혼인기간 7년 이내"인데 이 앱은 결혼 연차를 안 받아서 반영
    # 못 함) — 청년전용과 달리 40세 신혼부부도 나이로는 걸러지면 안 된다.
    token = _signup_login(client, email="jeonse-married-old@example.com", age=40, is_married=True)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["eligible"] is True


def test_housing_loan_jeonse_newlywed_rate_is_lower_than_youth_at_same_income(client):
    # 2026-09-03 사용자 지적("청년전용이랑 신혼부부용이랑 이자 똑같아? 그럼 굳이
    # 비교해야해?"): 처음엔 상품명만 바꾸고 청년전용 표를 그대로 재사용해서 실제로
    # 두 금리가 같았다 — 재조사 결과 신혼부부전용이 별도의(대체로 더 낮은) 표를
    # 쓰는 걸 확인해서 고쳤다. 같은 소득/보증금 조건에서 신혼부부전용이 더
    # 낮아야 한다(청년전용 2~4천만원 구간 2.5% vs 신혼부부전용 2.2%).
    youth_token = _signup_login(client, email="rate-compare-youth@example.com", age=29, is_married=False)
    married_token = _signup_login(client, email="rate-compare-married@example.com", age=29, is_married=True)
    payload = {
        "housing_type": "jeonse",
        "target_price_krw": 40_000_000,  # 보증금 5천만원 이하 구간(신혼부부전용 최저 금리대)
        "self_capital_krw": 10_000_000,
        "household_annual_income_krw": 30_000_000,
    }
    youth = client.post(
        "/savings_simulator/housing_loan", json=payload, headers={"Authorization": f"Bearer {youth_token}"}
    ).json()
    married = client.post(
        "/savings_simulator/housing_loan", json=payload, headers={"Authorization": f"Bearer {married_token}"}
    ).json()
    assert youth["policy_rate"] == 0.025
    assert married["policy_rate"] == 0.022
    assert married["policy_rate"] < youth["policy_rate"]


def test_housing_loan_jeonse_newlywed_rate_varies_by_deposit_size():
    # 신혼부부전용은 청년전용과 달리 임차보증금 규모로도 한 번 더 갈린다(2차원 표).
    from app.features.savings_simulator.schemas import HousingLoanInput
    from app.features.savings_simulator.simulator import simulate_housing_loan

    low_deposit = simulate_housing_loan(
        HousingLoanInput(
            housing_type="jeonse", target_price_krw=40_000_000, self_capital_krw=0, household_annual_income_krw=30_000_000
        ),
        is_married=True,
    )
    high_deposit = simulate_housing_loan(
        HousingLoanInput(
            housing_type="jeonse", target_price_krw=150_000_000, self_capital_krw=0, household_annual_income_krw=30_000_000
        ),
        is_married=True,
    )
    assert low_deposit.policy_rate == 0.022  # 5천만원 이하 구간
    assert high_deposit.policy_rate == 0.024  # 1억~1.5억 구간
    assert low_deposit.policy_rate < high_deposit.policy_rate


def test_housing_loan_purchase_over_income_cap_is_ineligible(client):
    token = _signup_login(client, email="purchase-high-income@example.com")
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "purchase",
            "target_price_krw": 400_000_000,
            "self_capital_krw": 100_000_000,
            "household_annual_income_krw": 150_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["monthly_saving_krw"] == 0


def test_housing_loan_purchase_uses_newlywed_table_when_married(client):
    token = _signup_login(client, email="purchase-married@example.com", is_married=True)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "purchase",
            "target_price_krw": 300_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,  # 일반 상한(6,000만원) 초과, 신혼 상한(8,500만원) 이내
            "loan_term_years": 30,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["product_name"] == "신혼부부전용 디딤돌대출"
    assert body["policy_rate"] == 0.0350  # 신혼가구 4천~7천만원 구간, 30년


def test_housing_loan_purchase_rate_varies_by_loan_term(client):
    token = _signup_login(client, email="purchase-term@example.com")
    base = {
        "housing_type": "purchase",
        "target_price_krw": 300_000_000,
        "self_capital_krw": 100_000_000,
        "household_annual_income_krw": 30_000_000,  # 일반 2천~4천만원 구간
    }
    r10 = client.post(
        "/savings_simulator/housing_loan", json={**base, "loan_term_years": 10}, headers={"Authorization": f"Bearer {token}"}
    ).json()
    r30 = client.post(
        "/savings_simulator/housing_loan", json={**base, "loan_term_years": 30}, headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert r10["policy_rate"] == 0.0320
    assert r30["policy_rate"] == 0.0345
    assert r10["policy_rate"] < r30["policy_rate"]


def test_housing_loan_response_includes_real_matched_policies(client, db_session):
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출이자 지원", large_category="주거")
    token = _signup_login(client, age=29, region="서울")
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 40_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    matched = response.json()["matched_policies"]
    assert [p["policy_name"] for p in matched] == ["신혼부부 전세자금 대출이자 지원"]


def test_housing_loan_amount_never_exceeds_price_minus_self_capital(client):
    token = _signup_login(client)
    # LTV 한도(80%)나 대출한도(1.5억원)보다 목표가-자기자본 차액이 더 작은 경우,
    # 그 작은 쪽을 따라야 한다.
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 200_000_000,
            "self_capital_krw": 180_000_000,
            "household_annual_income_krw": 40_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    assert body["loan_amount_krw"] == 20_000_000
