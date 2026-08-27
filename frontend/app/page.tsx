"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  FaArrowRight,
  FaBookOpen,
  FaBriefcase,
  FaGraduationCap,
  FaHouse,
  FaLandmark,
  FaMagnifyingGlass,
  FaPiggyBank,
  FaSeedling,
  FaWandMagicSparkles,
} from "react-icons/fa6";

const INTEREST_TILES = [
  { icon: FaBriefcase, label: "일자리", desc: "취업·창업 지원 정책", variant: "" },
  { icon: FaHouse, label: "주거", desc: "전월세·대출 지원 정책", variant: "icon-box-sky" },
  { icon: FaGraduationCap, label: "교육", desc: "학자금·직업훈련 지원", variant: "icon-box-indigo" },
  { icon: FaLandmark, label: "금융·복지·문화", desc: "생활안정·복지 지원", variant: "icon-box-teal" },
];

const STEPS = [
  {
    title: "프로필 입력",
    desc: "나이, 소득, 지역, 혼인 여부 같은 기본 정보를 입력하면 지금 신청 가능한 정책부터 걸러드립니다.",
  },
  {
    title: "AI가 정책 매칭 & 분석",
    desc: "실제 정책 데이터를 기준으로 나에게 맞는 정책을 찾고, 적합도·예상 혜택·유의사항까지 AI가 리포트로 정리합니다.",
  },
  {
    title: "저축플랜에 반영",
    desc: "정책에서 나오는 실질 혜택을 저축 목표에 반영해, 내가 실제로 더 모아야 할 금액을 계산합니다.",
  },
];

export default function Home() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    if (localStorage.getItem("token")) {
      router.push("/policy");
      return;
    }
    // localStorage only exists client-side, so this check can't move out of
    // the effect without breaking SSR — same one-time gate as app/(app)/layout.tsx.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCheckingAuth(false);
  }, [router]);

  if (checkingAuth) return null;

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-header-inner">
          <Link href="/" className="app-logo">
            <span className="icon-box icon-box-solid icon-box-sm">
              <FaSeedling />
            </span>
            청년/신혼부부 금융 도우미
          </Link>
          <div className="landing-header-actions">
            <Link href="/login" className="btn-ghost">
              로그인
            </Link>
            <Link href="/signup" className="btn" style={{ width: "auto", padding: "10px 20px" }}>
              내 맞춤 혜택 진단
            </Link>
          </div>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-glow" />
        <div className="landing-hero-inner">
          <span className="landing-hero-badge">
            <FaWandMagicSparkles />
            AI 기반 정책·저축 통합 매칭
          </span>
          <h1>
            복잡한 청년·신혼부부 정책,
            <br />
            <span className="landing-hero-gradient-text">내 저축 계획</span>으로 바로 연결합니다
          </h1>
          <p>나이·소득·지역만 입력하면 지금 신청 가능한 정책을 찾아드리고, AI가 분석한 실제 혜택을 저축 목표에 반영해드립니다.</p>

          <form
            className="landing-hero-search"
            onSubmit={(e) => {
              e.preventDefault();
              router.push("/signup");
            }}
          >
            <div className="landing-hero-search-field">
              <FaMagnifyingGlass />
              <input
                type="text"
                placeholder="관심 있는 정책 키워드를 입력하세요 (예: 청년월세, 전세자금 대출)"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <button type="submit" className="landing-hero-search-btn">
              혜택 찾기
            </button>
          </form>
          <p style={{ fontSize: 12, color: "rgba(191,219,254,0.8)", marginTop: 12, marginBottom: 0 }}>
            가입 후 프로필 기준으로 맞춤 검색이 가능해요
          </p>

          <div className="landing-hero-keywords">
            <span>추천 키워드:</span>
            <Link href="/signup">#청년월세</Link>
            <Link href="/signup">#전세자금대출</Link>
            <Link href="/signup">#청년창업지원</Link>
          </div>
        </div>
      </section>

      <section className="landing-tiles">
        {INTEREST_TILES.map((tile) => (
          <Link key={tile.label} href="/signup" className="landing-tile">
            <span className={`icon-box icon-box-lg ${tile.variant}`}>
              <tile.icon />
            </span>
            <h3>{tile.label}</h3>
            <p>{tile.desc}</p>
          </Link>
        ))}
      </section>

      <section className="landing-section">
        <div className="landing-section-head">
          <div>
            <span className="landing-section-eyebrow">Our Service</span>
            <h2>정책과 저축을 하나로 연결합니다</h2>
          </div>
        </div>
        <div className="landing-tiles" style={{ margin: 0, padding: 0 }}>
          <Link href="/signup" className="landing-tile">
            <span className="icon-box icon-box-lg">
              <FaLandmark />
            </span>
            <h3>금융 정책 추천</h3>
            <p>내 조건에 맞는 지금 신청 가능한 금융 지원 정책만 모아 보여드려요.</p>
          </Link>
          <Link href="/signup" className="landing-tile">
            <span className="icon-box icon-box-lg icon-box-sky">
              <FaBookOpen />
            </span>
            <h3>정책 읽기</h3>
            <p>카테고리·지역·마감 상태로 전체 정책을 자유롭게 검색해요.</p>
          </Link>
          <Link href="/signup" className="landing-tile">
            <span className="icon-box icon-box-lg icon-box-indigo">
              <FaWandMagicSparkles />
            </span>
            <h3>AI로 정책 알기</h3>
            <p>대화로 조건을 좁히고, AI 분석 리포트로 적합도와 예상 혜택을 확인해요.</p>
          </Link>
          <Link href="/signup" className="landing-tile">
            <span className="icon-box icon-box-lg icon-box-teal">
              <FaPiggyBank />
            </span>
            <h3>저축플랜</h3>
            <p>정책 혜택을 반영해 목표 금액까지 실제로 더 모아야 할 돈을 계산해요.</p>
          </Link>
        </div>
      </section>

      <section className="landing-steps">
        <div className="landing-steps-inner">
          <div className="landing-steps-head">
            <h2>어떻게 연결되나요?</h2>
            <p>가입부터 저축 계획까지 3단계로 간소화했습니다.</p>
          </div>
          <div className="landing-steps-grid">
            {STEPS.map((step, i) => (
              <div key={step.title} className="landing-step">
                <div className="landing-step-num">{i + 1}</div>
                <h4>{step.title}</h4>
                <p>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-cta">
        <div className="landing-cta-banner">
          <div>
            <h3>내가 받을 수 있는 정책 혜택은 얼마일까요?</h3>
            <p>가입하고 프로필만 입력하면 바로 맞춤 정책과 저축 계획을 확인할 수 있어요.</p>
          </div>
          <Link href="/signup" className="landing-cta-btn">
            무료로 시작하기
            <FaArrowRight />
          </Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div>
            <div className="landing-footer-brand">
              <FaSeedling />
              청년/신혼부부 금융 도우미
            </div>
            <p>공공 정책 데이터를 기반으로 개인 맞춤 정책 매칭과 저축 계획을 제공합니다.</p>
          </div>
          <div className="landing-footer-links">
            <div>
              <h5>서비스</h5>
              <ul>
                <li><Link href="/signup">정책 매칭</Link></li>
                <li><Link href="/signup">저축플랜</Link></li>
                <li><Link href="/login">로그인</Link></li>
              </ul>
            </div>
            <div>
              <h5>고객지원</h5>
              <ul>
                <li><a href="#">공지사항</a></li>
                <li><a href="#">자주 묻는 질문</a></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
