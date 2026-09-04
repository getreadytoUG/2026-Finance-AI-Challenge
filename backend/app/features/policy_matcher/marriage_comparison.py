from typing import Literal

from app.features.policy_matcher.schemas import (
    HousingLoanMarriageComparison,
    HousingLoanScenario,
    MarriageComparisonInput,
)
from app.features.savings_simulator.schemas import HousingLoanInput, HousingLoanOutput
from app.features.savings_simulator.simulator import simulate_housing_loan


def _to_scenario(output: HousingLoanOutput) -> HousingLoanScenario:
    return HousingLoanScenario(
        eligible=output.eligible,
        product_name=output.product_name,
        policy_rate=output.policy_rate,
        ltv_rate=output.ltv_rate,
        loan_amount_krw=output.loan_amount_krw,
        monthly_interest_krw=output.monthly_interest_krw,
        summary=output.summary,
    )


# 2026-09-03 재작업("혼인신고 계산기도 특정 정책 타겟팅해야 함", 사용자 요청): 예전엔
# CachedPolicy 2,750건 전체를 스캔해서 married_only/unmarried_only/both 버킷으로
# "자격이 바뀌는 정책"을 찾았는데, 실제로 혼인상태를 조건으로 거는 정책이 71건뿐이라
# 대부분 밋밋한 결과만 냈다(사용자 판단: 그 섹션은 빼도 된다). 대신 실제로 미혼용/
# 기혼용이 이름부터 별도 상품으로 존재하고 조건도 다른 걸로 확인된 고정 기준 2개만
# 타겟팅한다:
#   전세: [미혼] 청년전용 버팀목 전세자금대출 vs [기혼] 신혼부부전용 버팀목 전세자금대출
#   매매: [미혼] 내집마련 디딤돌대출(청년/일반) vs [기혼] 신혼부부전용 디딤돌대출
# 그 실제 계산 로직(savings_simulator/simulator.py)을 그대로 재사용한다(중복
# 구현하지 않음) — simulate_housing_loan의 is_married 플래그가 이 두 상품 갈래를
# 결정한다. 지역은 이 계산에 안 쓰여서(LTV/금리/소득상한 전부 전국 공통) 더 이상
# 입력받지 않는다.
_HOUSING_TYPES: tuple[Literal["jeonse", "purchase"], ...] = ("jeonse", "purchase")


def compare_housing_loan_scenarios(input: MarriageComparisonInput) -> list[HousingLoanMarriageComparison]:
    married_income = input.annual_income_krw + (input.spouse_annual_income_krw or 0)
    comparisons = []
    for housing_type in _HOUSING_TYPES:
        unmarried_output = simulate_housing_loan(
            HousingLoanInput(
                housing_type=housing_type,
                target_price_krw=input.target_price_krw,
                self_capital_krw=input.self_capital_krw,
                household_annual_income_krw=input.annual_income_krw,
            ),
            is_married=False,
            age=input.age,
        )
        married_output = simulate_housing_loan(
            HousingLoanInput(
                housing_type=housing_type,
                target_price_krw=input.target_price_krw,
                self_capital_krw=input.self_capital_krw,
                household_annual_income_krw=married_income,
            ),
            is_married=True,
            age=input.age,
        )
        comparisons.append(
            HousingLoanMarriageComparison(
                housing_type=housing_type,
                unmarried=_to_scenario(unmarried_output),
                married=_to_scenario(married_output),
            )
        )
    return comparisons
