from typing import Literal

# "금융 정책 추천" 탭이 필터링 기준으로 쓰는 대분류(lclsfNm) 태그. 온통청년 API
# 실측 결과 이 태그 문자열의 가운뎃점은 U+FF65(반각 카타카나 가운뎃점, "･")다 —
# 일반 U+30FB("・")나 가운뎃점(U+00B7, "·")과 시각적으로 비슷해 보이지만 다른
# 문자라 잘못 쓰면 조용히 매치가 안 된다.
FINANCIAL_LARGE_CATEGORY = "금융･복지･문화"

# 2026-08-26 기준 CachedPolicy에서 실제로 관측된 대분류 태그 8종 (/policy_matcher/categories
# 응답으로 직접 확인). "복지문화"와 "금융･복지･문화", "참여권리"와 "참여･기반", "교육"과
# "교육･직업훈련"처럼 비슷하지만 다른 태그가 중복으로 섞여 있다 — 온통청년 쪽 대분류
# 체계가 시점별로 갈라진 것으로 보이는 기존 데이터 품질 문제(FINANCIAL_LARGE_CATEGORY
# 주석 참고)의 연장선. LLM 도구 호출 스키마(policy_chat)에서 category를 자유 텍스트로
# 두면 모델이 실제로 존재하지 않는 태그를 만들어내 조용히 0건이 되는 문제가 있어
# Literal로 제한한다 — 온통청년이 새 대분류를 추가하면 이 목록도 같이 갱신해야 한다.
PolicyCategoryTag = Literal[
    "일자리",
    "금융･복지･문화",
    "복지문화",
    "주거",
    "교육",
    "참여･기반",
    "교육･직업훈련",
    "참여권리",
]


def category_tags(raw: str) -> list[str]:
    # 정책 하나에 콤마로 여러 태그가 붙기도 하고("일자리,교육"), 같은 태그가
    # 반복되기도 한다("일자리,일자리,일자리") — set으로 중복만 제거하고
    # 순서는 유지한다.
    seen: set[str] = set()
    tags: list[str] = []
    for part in raw.split(","):
        tag = part.strip()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags
