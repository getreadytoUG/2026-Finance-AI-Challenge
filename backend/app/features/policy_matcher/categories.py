# "금융 정책 추천" 탭이 필터링 기준으로 쓰는 대분류(lclsfNm) 태그. 온통청년 API
# 실측 결과 이 태그 문자열의 가운뎃점은 U+FF65(반각 카타카나 가운뎃점, "･")다 —
# 일반 U+30FB("・")나 가운뎃점(U+00B7, "·")과 시각적으로 비슷해 보이지만 다른
# 문자라 잘못 쓰면 조용히 매치가 안 된다.
FINANCIAL_LARGE_CATEGORY = "금융･복지･문화"


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
