"""정책연계형 저축/주거 시뮬레이터 — 순수 계산(LLM 미사용).

⚠️ 아래 매칭비율/금리/LTV/소득 상한은 실제 정부 고시(서민금융진흥원·주택도시기금
등)가 아니라 md_files/UPGRADE.md의 예시 구조를 그대로 옮긴 **시연용 예시 수치**다.
실제 서비스에 쓰려면 반드시 최신 공고문으로 다시 확인해야 한다(2026-09-01 사용자
승인: "예시/추정치라고 명확히 표시하고 진행"). 프론트에서도 결과 카드에 이 사실을
항상 배지로 노출한다 — 여기 숫자만 믿고 신뢰도 있는 값처럼 보여주지 않는다.
"""

from datetime import date

from app.features.policy_matcher.matching import is_eligible, is_savings_account_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status
from app.features.savings_simulator.schemas import (
    HousingLoanInput,
    HousingLoanOutput,
    MatchedSavingsPolicy,
    YouthLeapAccountInput,
    YouthLeapAccountOutput,
)

# 청년도약계좌 예시: 연소득 구간별 정부 매칭비율(가장 유리한 구간부터).
# 매칭은 월 납입액 중 40만원까지만 적용된다는 실제 제도의 "매칭 상한" 구조를 반영.
_MATCH_RATE_BRACKETS: list[tuple[int, float]] = [
    (24_000_000, 0.060),
    (36_000_000, 0.046),
    (48_000_000, 0.037),
    (60_000_000, 0.030),
    (75_000_000, 0.0),  # 매칭은 없지만 비과세 혜택은 유지되는 구간(예시)
]
_INCOME_CAP_KRW = 75_000_000
_MATCH_CAP_MONTHLY_KRW = 400_000
_ASSUMED_ANNUAL_RATE = 0.035  # 정책상품/시중적금 공통 가정 금리(예시)
_MARKET_TAX_RATE = 0.154  # 이자소득세


def _match_rate_for_income(annual_income_krw: int) -> float:
    for cap, rate in _MATCH_RATE_BRACKETS:
        if annual_income_krw <= cap:
            return rate
    return 0.0


def simulate_youth_leap_account(input: YouthLeapAccountInput) -> YouthLeapAccountOutput:
    months = input.goal_years * 12
    eligible = input.annual_income_krw <= _INCOME_CAP_KRW

    if not eligible:
        # 소득 기준 초과 — 정책상품 혜택 없이 시중적금과 동일하게 취급한다.
        gross_interest = input.monthly_amount_krw * (months * (months + 1) / 2) * (_ASSUMED_ANNUAL_RATE / 12)
        net_interest = round(gross_interest * (1 - _MARKET_TAX_RATE))
        total = input.monthly_amount_krw * months + input.seed_money_krw + net_interest
        return YouthLeapAccountOutput(
            eligible=False,
            matching_rate=0.0,
            eligibility_note="연소득이 예시 기준(7,500만원)을 초과해 정부 매칭 대상이 아니에요.",
            policy_total_krw=total,
            market_total_krw=total,
            benefit_diff_krw=0,
            summary="소득 기준 초과로 이 상품의 정부 지원 효과는 없어요(예시 수치).",
        )

    matching_rate = _match_rate_for_income(input.annual_income_krw)
    matched_base = min(input.monthly_amount_krw, _MATCH_CAP_MONTHLY_KRW)
    monthly_government_contribution = matched_base * matching_rate
    government_total = round(monthly_government_contribution * months)

    gross_interest = input.monthly_amount_krw * (months * (months + 1) / 2) * (_ASSUMED_ANNUAL_RATE / 12)
    policy_interest = round(gross_interest)  # 정책상품은 비과세
    market_interest = round(gross_interest * (1 - _MARKET_TAX_RATE))

    principal = input.monthly_amount_krw * months + input.seed_money_krw
    policy_total = principal + government_total + policy_interest
    market_total = principal + market_interest
    diff = policy_total - market_total

    note = (
        f"청년도약계좌 기여금 매칭 {matching_rate * 100:.1f}% 대상(월 최대 "
        f"{_MATCH_CAP_MONTHLY_KRW // 10_000}만원 납입분까지, 예시)"
        if matching_rate > 0
        else "정부 매칭 없이 비과세 혜택만 적용되는 구간이에요(예시)."
    )
    summary = f"정부 지원금 및 비과세로 일반 적금 대비 약 {diff:,}원 추가 수익을 기대할 수 있어요(예시 수치)."

    return YouthLeapAccountOutput(
        eligible=True,
        matching_rate=matching_rate,
        eligibility_note=note,
        policy_total_krw=policy_total,
        market_total_krw=market_total,
        benefit_diff_krw=diff,
        summary=summary,
    )


# 2026-09-02 추가: 위 계산은 여전히 "청년도약계좌류 상품 구조"를 본뜬 예시지만,
# 이 목록만큼은 실제 DB(CachedPolicy)에서 지금 입력한 조건으로 진짜 자격되는
# 저축/자산형성 정책을 찾아준다 — matching.is_eligible을 그대로 재사용하므로
# 지난번에 추가한 장애인/보훈대상자 전용 정책 필터링도 자동으로 함께 적용된다.
# router가 DB에서 CachedPolicy를 조회해 넘겨주고, 여기서는 필터링만 한다(이 파일의
# "순수 계산" 원칙 유지 — DB I/O는 router가 담당).
def match_real_savings_policies(
    policies: list[CachedPolicy],
    match_input: PolicyMatchInput,
    today: date,
) -> list[MatchedSavingsPolicy]:
    candidates = [
        p
        for p in policies
        if is_savings_account_policy(p)
        and is_eligible(p, match_input)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
    ]
    candidates.sort(key=lambda p: STATUS_ORDER[compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0]])
    return [
        MatchedSavingsPolicy(
            policy_key=p.policy_key,
            policy_name=p.policy_name,
            benefit_description=p.description,
            application_period=p.application_period,
            reference_url=p.apply_url,
        )
        for p in candidates
    ]


# 버팀목(전세)/디딤돌(매매) 예시 상품 조건 — housing_type별로 LTV/금리/소득상한이 다르다.
_HOUSING_PRODUCTS = {
    "jeonse": {
        "product_name": "버팀목 전세자금대출(예시)",
        "ltv_rate": 0.80,
        "policy_rate": 0.021,
        "market_rate": 0.043,
        "income_cap_krw": 90_000_000,
    },
    "purchase": {
        "product_name": "디딤돌 구입자금대출(예시)",
        "ltv_rate": 0.70,
        "policy_rate": 0.027,
        "market_rate": 0.045,
        "income_cap_krw": 85_000_000,
    },
}


def simulate_housing_loan(input: HousingLoanInput) -> HousingLoanOutput:
    product = _HOUSING_PRODUCTS[input.housing_type]
    eligible = input.household_annual_income_krw <= product["income_cap_krw"]

    max_ltv_amount = round(input.target_price_krw * product["ltv_rate"])
    price_gap = max(0, input.target_price_krw - input.self_capital_krw)
    loan_amount = min(max_ltv_amount, price_gap)

    monthly_interest = round(loan_amount * product["policy_rate"] / 12)
    market_monthly_interest = round(loan_amount * product["market_rate"] / 12)
    monthly_saving = market_monthly_interest - monthly_interest

    if eligible:
        summary = (
            f"시중 대비 매월 약 {monthly_saving:,}원 이자를 절감할 수 있어요"
            f"(연 {product['market_rate'] * 100:.1f}% 시중 상품과 비교, 예시 수치)."
        )
        note = f"{product['product_name']} 자격 요건(예시 소득 기준) 충족"
    else:
        summary = "가구 합산 소득이 예시 기준을 초과해 이 정책 상품 대상이 아니에요."
        note = f"가구 합산 연소득이 예시 기준({product['income_cap_krw']:,}원)을 초과했어요."

    return HousingLoanOutput(
        eligible=eligible,
        product_name=product["product_name"],
        ltv_rate=product["ltv_rate"],
        policy_rate=product["policy_rate"],
        market_rate=product["market_rate"],
        loan_amount_krw=loan_amount,
        monthly_interest_krw=monthly_interest,
        market_monthly_interest_krw=market_monthly_interest,
        monthly_saving_krw=monthly_saving if eligible else 0,
        summary=note + " " + summary,
    )


# 2026-09-02 추가: 전세/구입 대출이자 지원류는 정책명에 "전세" 또는 "구입/매매"가
# 명확히 들어가는 경우만 골라 housing_type별로 나눈다 — "디딤돌"/"버팀목" 단독
# 키워드는 실측 결과 청년창업농/IP지원 사업처럼 주거와 무관한 이름에도 비유적으로
# 쓰여서 뺐다(예: "청년창업농 디딤돌 사업", "IP 디딤돌 프로그램").
_HOUSING_LOAN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "jeonse": ("전세자금", "전세보증금"),
    "purchase": ("주택구입", "구입자금", "매매자금", "주택자금"),
}


def match_real_housing_policies(
    policies: list[CachedPolicy],
    housing_type: str,
    match_input: PolicyMatchInput,
    today: date,
) -> list[MatchedSavingsPolicy]:
    keywords = _HOUSING_LOAN_KEYWORDS[housing_type]
    candidates = [
        p
        for p in policies
        if any(keyword in p.policy_name for keyword in keywords)
        and is_eligible(p, match_input)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
    ]
    candidates.sort(key=lambda p: STATUS_ORDER[compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0]])
    return [
        MatchedSavingsPolicy(
            policy_key=p.policy_key,
            policy_name=p.policy_name,
            benefit_description=p.description,
            application_period=p.application_period,
            reference_url=p.apply_url,
        )
        for p in candidates
    ]
