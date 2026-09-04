from app.features.policy_matcher.marriage_comparison import compare_housing_loan_scenarios
from app.features.policy_matcher.schemas import MarriageComparisonInput


def _input(**overrides) -> MarriageComparisonInput:
    defaults = dict(age=29, annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
    defaults.update(overrides)
    return MarriageComparisonInput(**defaults)


# ---------------------------------------------------------------------------
# 2026-09-03 재작업("혼인신고 계산기도 특정 정책 타겟팅해야 함"): 예전엔
# CachedPolicy 2,750건 전체를 스캔해 married_only/unmarried_only/both 버킷으로
# "자격이 바뀌는 정책"을 찾았는데, 대부분 밋밋한 결과만 내서(사용자 판단: 그
# 섹션은 빼도 된다) 걷어냈다. 이제는 항상 이 두 고정 기준 상품(버팀목/디딤돌)을
# 미혼/기혼으로 비교해서 보여준다. 실제 계산 로직(savings_simulator/simulator.py)의
# 실수치를 그대로 재사용하므로, 여기서는 "미혼/기혼 상품이 실제로 다르게 나오는지"만
# 검증한다 — 요율표 자체의 세부 경계값 테스트는 test_savings_simulator.py에 이미 있다.


def test_compare_housing_loan_scenarios_returns_jeonse_and_purchase():
    result = compare_housing_loan_scenarios(_input())
    assert [c.housing_type for c in result] == ["jeonse", "purchase"]


def test_compare_housing_loan_scenarios_uses_different_product_names_by_marital_status():
    result = compare_housing_loan_scenarios(_input())
    jeonse = result[0]
    assert jeonse.unmarried.product_name == "청년전용 버팀목 전세자금대출"
    assert jeonse.married.product_name == "신혼부부전용 버팀목 전세자금대출"
    purchase = result[1]
    assert purchase.unmarried.product_name == "내집마련 디딤돌대출"
    assert purchase.married.product_name == "신혼부부전용 디딤돌대출"


def test_compare_housing_loan_scenarios_married_uses_combined_household_income():
    # 미혼 시나리오는 본인 소득(4천만)만, 기혼 시나리오는 배우자 소득(2천만)을
    # 합산한 6천만원 기준으로 금리가 갈려야 한다(버팀목 4~6천만원 구간 2.9%).
    result = compare_housing_loan_scenarios(_input(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000))
    jeonse = result[0]
    assert jeonse.unmarried.policy_rate == 0.025  # 4천만원 이하 구간
    assert jeonse.married.policy_rate == 0.029  # 6천만원 구간(4~6천)


def test_compare_housing_loan_scenarios_uses_price_and_self_capital_inputs():
    result = compare_housing_loan_scenarios(
        _input(target_price_krw=200_000_000, self_capital_krw=180_000_000, spouse_annual_income_krw=None)
    )
    jeonse = result[0]
    # LTV(0.8*200M=160M)나 대출한도(1.5억)보다 목표가-자기자본 차액(20M)이 더
    # 작으므로 그 작은 쪽을 따라야 한다 — savings_simulator와 동일한 계산.
    assert jeonse.unmarried.loan_amount_krw == 20_000_000
    assert jeonse.married.loan_amount_krw == 20_000_000


def test_compare_housing_loan_scenarios_uses_default_price_when_not_given():
    result = compare_housing_loan_scenarios(_input())
    jeonse = result[0]
    # 기본값(목표가 2.5억/자기자본 5천만원) → LTV 0.8*2.5억=2억, 차액 2억,
    # 대출한도 1.5억 중 최솟값 = 1.5억.
    assert jeonse.unmarried.loan_amount_krw == 150_000_000
