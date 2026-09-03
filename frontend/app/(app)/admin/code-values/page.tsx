"use client";

import { useEffect, useState } from "react";
import { getAdminCodeValues, type AdminCodeValuesResponse } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { DashboardLayout } from "@/components/DashboardLayout";
import { formatDateTime } from "@/components/AdminWidgets";

const TH_CLASS = "px-3 py-2.5 text-left text-[12px] font-bold text-slate-400";
const TD_CLASS = "border-t border-slate-100 px-3 py-2.5 text-[13px] text-ink align-top";

function Flag({ ok, okLabel, badLabel }: { ok: boolean; okLabel: string; badLabel: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[11px] font-extrabold ${
        ok ? "bg-[#e8f8f4] text-[#159c8d]" : "bg-rose-50 text-rose-500"
      }`}
    >
      {ok ? okLabel : badLabel}
    </span>
  );
}

function Section({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <div className="mb-1 text-[14px] font-extrabold text-ink">{title}</div>
      {note && <p className="mb-3 text-[12px] leading-5 text-slate-400">{note}</p>}
      {children}
    </div>
  );
}

function CodeValuesContent() {
  const [data, setData] = useState<AdminCodeValuesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function load() {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem("token") ?? "";
    getAdminCodeValues(token)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    // load()가 내부에서 setLoading/setError를 동기적으로 호출하는데, 최초 로드도
    // "새로고침" 버튼과 같은 함수를 재사용하려고 일부러 이렇게 뒀다(다른 admin
    // 페이지들의 load() 패턴과 통일).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  const unrecognizedMarital = data?.marital_status_codes.filter((c) => !c.label) ?? [];
  const unmappedRegionCount = data?.region_prefixes.filter((p) => p.mapped_region_names.length === 0).length ?? 0;
  const unknownTagCount = data?.large_category_tags.filter((t) => !t.is_known).length ?? 0;

  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[13px] font-bold text-slate-500">
            정책 캐시 {data?.total_policies ?? 0}건 기준 · 마지막 배치 갱신 {formatDateTime(data?.cache_last_refreshed_at ?? null)}
          </div>
          <p className="mt-1 text-[12px] leading-5 text-slate-400">
            온통청년 API가 내려주는 원본 코드값(혼인상태/지역코드/대분류)이 코드의 정적 매핑표와 실제로 맞는지
            확인하는 화면이에요. 별도 테이블 없이 매 요청마다 정책 캐시를 그대로 집계하므로, 정책 캐시가 갱신될
            때마다(정책 탭의 &quot;지금 갱신&quot; 또는 매일 새벽 배치) 여기 값도 자동으로 최신 상태가 됩니다.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="shrink-0 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-[12px] font-extrabold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6] disabled:opacity-50"
        >
          {loading ? "불러오는 중..." : "새로고침"}
        </button>
      </div>

      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {!data && !error && <p className="text-[13px] text-slate-400">불러오는 중...</p>}

      {data && (
        <>
          <Section
            title="혼인상태 코드 (mrgSttsCd)"
            note={
              unrecognizedMarital.length > 0
                ? `${unrecognizedMarital.length}개 값이 온통청년 공식 코드정의서(기혼/미혼/제한없음)에 없는 값이에요 — 새 코드가 추가됐을 수 있어요.`
                : "온통청년 공식 코드정의서 기준으로 전부 디코딩됐어요 — 기혼/미혼 전용 정책만 혼인여부로 걸러지고, 제한없음(대부분)은 필터링 없이 통과합니다."
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr>
                    <th className={TH_CLASS}>원본 값</th>
                    <th className={TH_CLASS}>정책 수</th>
                    <th className={TH_CLASS}>의미</th>
                  </tr>
                </thead>
                <tbody>
                  {data.marital_status_codes.map((c) => (
                    <tr key={c.value || "(빈값)"}>
                      <td className={`${TD_CLASS} font-mono`}>{c.value || "(빈값)"}</td>
                      <td className={TD_CLASS}>{c.count}</td>
                      <td className={TD_CLASS}>
                        {c.label ? (
                          <span className="rounded-full bg-[#e8f8f4] px-2.5 py-1 text-[11px] font-extrabold text-[#159c8d]">
                            {c.label}
                          </span>
                        ) : (
                          <Flag ok={false} okLabel="" badLabel="알 수 없는 값" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section
            title="지역코드 접두사 (zipCd 앞 2자리)"
            note={`전국 대상(지역코드 없음) ${data.nationwide_region_count}건은 접두사 집계에서 제외했어요.${
              unmappedRegionCount > 0
                ? ` ${unmappedRegionCount}개 접두사는 matching.REGIONS 어디에도 매핑되어 있지 않아요 — 온통청년이 새 시/도 코드를 쓰기 시작했을 수 있어요(광주·전남 통합 코드 "12" 같은 사례가 실제로 있었습니다).`
                : ""
            }`}
          >
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr>
                    <th className={TH_CLASS}>접두사</th>
                    <th className={TH_CLASS}>정책 수</th>
                    <th className={TH_CLASS}>매핑된 시/도</th>
                  </tr>
                </thead>
                <tbody>
                  {data.region_prefixes.map((p) => (
                    <tr key={p.prefix}>
                      <td className={`${TD_CLASS} font-mono`}>{p.prefix}</td>
                      <td className={TD_CLASS}>{p.count}</td>
                      <td className={TD_CLASS}>
                        {p.mapped_region_names.length > 0 ? (
                          p.mapped_region_names.join(", ")
                        ) : (
                          <Flag ok={false} okLabel="" badLabel="미확인 접두사" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section
            title="대분류 (lclsfNm)"
            note={
              unknownTagCount > 0
                ? `${unknownTagCount}개 값이 categories.PolicyCategoryTag 목록에 없어요 — AI 챗봇 검색 스키마가 이 대분류로는 필터링을 못 만들어요.`
                : undefined
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr>
                    <th className={TH_CLASS}>값</th>
                    <th className={TH_CLASS}>정책 수</th>
                    <th className={TH_CLASS}>매핑 상태</th>
                  </tr>
                </thead>
                <tbody>
                  {data.large_category_tags.map((t) => (
                    <tr key={t.value}>
                      <td className={TD_CLASS}>{t.value}</td>
                      <td className={TD_CLASS}>{t.count}</td>
                      <td className={TD_CLASS}>
                        <Flag ok={t.is_known} okLabel="알려진 태그" badLabel="새 태그" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="중분류 (mclsfNm)" note="매칭 로직이 쓰지 않는 참고용 값이에요 — 코드에 별도 매핑표가 없어 원본 값 그대로 보여줍니다.">
            <div className="max-h-[360px] overflow-y-auto overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr>
                    <th className={TH_CLASS}>값</th>
                    <th className={TH_CLASS}>정책 수</th>
                  </tr>
                </thead>
                <tbody>
                  {data.mid_categories.map((m) => (
                    <tr key={m.value}>
                      <td className={TD_CLASS}>{m.value}</td>
                      <td className={TD_CLASS}>{m.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

export default function AdminCodeValuesPage() {
  return (
    <AdminGuard>
      <DashboardLayout eyebrow="ADMIN" title="코드값">
        <CodeValuesContent />
      </DashboardLayout>
    </AdminGuard>
  );
}
