# 온통청년 API 실측 결과(2026-08) "취약계층 및 금융지원"이 lclsfNm(대분류)
# 전체를 통틀어 유일하게 "금융"을 이름에 포함하는 mclsfNm(중분류)이었다 —
# "금융 정책 추천" 탭이 필터링 기준으로 쓴다.
FINANCIAL_MID_CATEGORY = "취약계층 및 금융지원"


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
