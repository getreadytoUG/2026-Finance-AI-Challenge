from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.notices.models import Notice
from app.features.notices.schemas import NoticeListResponse, NoticeOut

router = APIRouter()

# 실제 관리자 작성 화면은 아직 없다 — "어드민이 올린 척" 데모용으로 서버 기동 시
# 예시 공지 몇 개를 미리 심어둔다(seed_policy_cache_if_empty/seed_admin_user와
# 동일한 패턴, main.py의 lifespan에서 seed_example_notices_if_empty(db)로 호출).
_EXAMPLE_NOTICES = [
    {
        "category": "금리",
        "title": "한국은행 기준금리 3.00% → 2.75% 인하 반영",
        "content": (
            "한국은행 금융통화위원회가 기준금리를 2.75%로 0.25%p 인하했습니다. "
            "정책금융 시뮬레이터의 시중 상품 비교금리 가정치도 순차적으로 업데이트할 예정이며, "
            "실제 적용 금리는 상품 취급 은행 공시를 다시 확인해주세요."
        ),
        "days_ago": 1,
    },
    {
        "category": "상품",
        "title": "추천 상품 추가 공시: 청년미래적금",
        "content": (
            "청년도약계좌 후속 상품인 청년미래적금이 정책금융 시뮬레이터 비교 대상에 새로 추가됐습니다. "
            "우대형/일반형 매칭 비율과 소득 조건은 상품 상세에서 확인할 수 있습니다."
        ),
        "days_ago": 2,
    },
    {
        "category": "정책",
        "title": "청년월세 한시 특별지원, 하반기 재접수 시작",
        "content": (
            "상반기 마감됐던 청년월세 한시 특별지원이 하반기 예산 추가 편성으로 재접수를 시작합니다. "
            "대상 지역·소득 조건에 맞는 회원에게는 정책 달력에도 함께 반영됩니다."
        ),
        "days_ago": 4,
    },
    {
        "category": "서비스",
        "title": "정책 달력 알림, 마감 임박 정책 우선 표시로 개편",
        "content": (
            "정책 달력 탭에서 신청 마감이 임박한 정책이 목록 상단에 먼저 노출되도록 정렬 방식을 개선했습니다."
        ),
        "days_ago": 6,
    },
    {
        "category": "공지",
        "title": "예시 공지: 서비스 정기 점검 안내",
        "content": (
            "이 항목은 공지사항 탭 구성을 보여주기 위한 예시 공지입니다. "
            "실제 점검 일정이 확정되면 이 자리에 안내가 게시됩니다."
        ),
        "days_ago": 8,
    },
]


def seed_example_notices_if_empty(db: Session) -> None:
    if db.query(Notice.id).first() is not None:
        return
    now = datetime.now(timezone.utc)
    for item in _EXAMPLE_NOTICES:
        db.add(
            Notice(
                category=item["category"],
                title=item["title"],
                content=item["content"],
                created_at=now - timedelta(days=item["days_ago"]),
            )
        )
    db.commit()


@router.get("", response_model=NoticeListResponse)
def list_notices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notices = db.query(Notice).order_by(Notice.created_at.desc()).all()
    return NoticeListResponse(notices=[NoticeOut.model_validate(n) for n in notices])
