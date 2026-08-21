import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel

from app.core.config import settings

YOUTH_CENTER_API_URL = "https://www.youthcenter.go.kr/opi/youthPlcyList.do"


class RawYouthPolicy(BaseModel):
    policy_name: str
    description: str
    apply_url: str
    application_period: str
    min_age: int | None
    max_age: int | None
    min_income_krw: int | None
    max_income_krw: int | None
    marital_status: str
    region_code: str


def fetch_policies(query: str | None = None, page_index: int = 1, display: int = 100) -> list[RawYouthPolicy]:
    if not settings.youth_center_api_key:
        raise RuntimeError("YOUTH_CENTER_API_KEY is not set — see README '온통청년 API 키 발급'")
    params = {
        "openApiVlak": settings.youth_center_api_key,
        "pageIndex": page_index,
        "display": display,
    }
    if query:
        params["query"] = query
    response = httpx.get(YOUTH_CENTER_API_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return _parse_youth_policy_xml(response.text)


# NOTE: 아래 태그명(plcyNm, plcyExplnCn, sprtTrgtMinAge, mrgSttsCd 등)은 온통청년
# 공식 문서에서 요청 파라미터만 확인했고 실제 응답 필드명은 검증하지 못했다.
# 실제 API 키로 라이브 응답 샘플을 확보하면 이 함수의 _text() 호출부만 수정하면 된다.
def _parse_youth_policy_xml(xml_text: str) -> list[RawYouthPolicy]:
    root = ET.fromstring(xml_text)
    policies = []
    for item in root.iter("youthPolicy"):
        policies.append(
            RawYouthPolicy(
                policy_name=_text(item, "plcyNm"),
                description=_text(item, "plcyExplnCn"),
                apply_url=_text(item, "aplyUrlAddr"),
                application_period=_text(item, "aplyYmd") or "상시",
                min_age=_int_or_none(_text(item, "sprtTrgtMinAge")),
                max_age=_int_or_none(_text(item, "sprtTrgtMaxAge")),
                min_income_krw=_int_or_none(_text(item, "earnMinAmt")),
                max_income_krw=_int_or_none(_text(item, "earnMaxAmt")),
                marital_status=_text(item, "mrgSttsCd"),
                region_code=_text(item, "zipCd"),
            )
        )
    return policies


def _text(item: ET.Element, tag: str) -> str:
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _int_or_none(value: str) -> int | None:
    return int(value) if value.isdigit() else None
