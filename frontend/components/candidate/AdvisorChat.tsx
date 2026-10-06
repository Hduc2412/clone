"use client";

/**
 * Một khung tư vấn sau khi đọc CV: cấp hồ sơ khi không có orderCode,
 * tư vấn đúng đơn khi có orderCode. Giữ API và lịch sử hai phạm vi riêng.
 * Chatbot tư vấn chung ở góc màn hình không thuộc khung này.
 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  type AdvisorTurn,
  type AgentReply,
  type AgentState,
  type NextAction,
  type ProposedFact,
  askAgent,
  askAdvisor,
  fetchAdvisorTurns,
  confirmAgentFact,
  fetchAgentState,
  openAgentTurn,
} from "@/lib/candidateApi";

/** Nhãn tiếng Việt cho tên trường, để câu xác nhận đọc được. */
const TEN_TRUONG: Record<string, string> = {
  full_name: "họ tên",
  birth_year: "năm sinh",
  gender: "giới tính",
  education_level: "bằng cấp",
  major: "chuyên ngành",
  japanese_level: "trình độ tiếng Nhật",
  experience_years: "số năm kinh nghiệm",
  care_experience: "kinh nghiệm chăm sóc",
  phone: "số điện thoại",
  desired_prefecture: "tỉnh mong muốn",
  desired_employer_type: "loại cơ sở mong muốn",
  salary_expectation_jpy: "lương mong muốn",
  budget_vnd: "ngân sách",
};

function docGiaTri(field: string, value: unknown, nhan?: string | null): string {
  // Mã danh mục đọc bằng nhãn máy chủ gửi kèm. Kiểm trên trình duyệt ngày 06/10,
  // câu xác nhận hiện "Loại hình: vien_duong_lao" — khách phải đọc mã máy rồi bấm
  // "Đúng, lưu lại".
  if (nhan) return nhan;
  if (typeof value === "boolean") {
    return field === "care_experience"
      ? value
        ? "đã từng chăm sóc người bệnh"
        : "chưa từng chăm sóc người bệnh"
      : value
        ? "có"
        : "không";
  }
  // 2.0 đọc ra "2". Một số thập phân treo ở đó làm câu xác nhận trông như đầu
  // ra của máy, mà đây là câu người dùng phải đọc rồi bấm đồng ý.
  if (typeof value === "number" && Number.isInteger(value)) return String(value);
  return String(value);
}

interface AdvisorChatProps {
  sessionId: string;
  orderCode?: string;
  moc?: "sau_cv" | "sau_matching";
  onProfileChanged?: () => void | Promise<void>;
}

function isAgentReply(turn: AdvisorTurn | AgentReply): turn is AgentReply {
  return "facts_to_save" in turn;
}

/** Đổi phiên hoặc đơn thì dựng khung mới, không mang lịch sử/đề xuất cũ theo. */
export default function AdvisorChat(props: AdvisorChatProps) {
  return (
    <AdvisorConversation
      key={JSON.stringify([props.sessionId, props.orderCode ?? null])}
      {...props}
    />
  );
}

function AdvisorConversation({
  sessionId,
  orderCode,
  moc = "sau_cv",
  onProfileChanged,
}: AdvisorChatProps) {
  const [trangThai, setTrangThai] = useState<AgentState | null>(null);
  const [luot, setLuot] = useState<AdvisorTurn[]>([]);
  const [deXuat, setDeXuat] = useState<ProposedFact[]>([]);
  const [goiY, setGoiY] = useState<NextAction | null>(null);
  const [noiDung, setNoiDung] = useState("");
  const [dangHoi, setDangHoi] = useState(false);
  const [dangLuu, setDangLuu] = useState<string | null>(null);
  const [loi, setLoi] = useState("");
  const cuoiRef = useRef<HTMLDivElement>(null);

  // Lượt mở đầu: giữ PROMISE của lời gọi, không giữ một cờ.
  //
  // Bản trước bật cờ "đã mở đầu" TRƯỚC khi gọi. Gọi hỏng một lần (mất mạng, máy
  // chủ khởi động lại) là cờ vẫn bật, và trong cùng lần hiển thị đó không bao
  // giờ gọi lại — khách thấy một dòng lỗi mà không có cách nào thoát ra.
  //
  // Giữ promise thì được cả ba điều:
  // - Đang gọi mà component dựng lại (React StrictMode chạy effect hai lần, hoặc
  //   trang vẽ lại) → dùng CHUNG promise ấy, chỉ một lời gọi mạng. Máy chủ chống
  //   trùng lượt mở đầu theo kiểu đọc-rồi-ghi (`api/agent._da_mo_dau`), nên hai
  //   lời gọi ĐỒNG THỜI vẫn có thể cùng ghi; phía này phải bảo đảm không có hai.
  // - Gọi hỏng → bỏ promise, để "Thử lại" tạo lời gọi mới.
  // - Mở đầu thành công mà bước nạp lịch sử hỏng → thử lại chỉ nạp lịch sử,
  //   không gọi mở đầu lần hai.
  const moDau = useRef<{ moc: string; hua: Promise<unknown> } | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // Trạng thái lần nạp đầu, tách khỏi `loi` của từng câu hỏi: chỉ lỗi NẠP mới
  // có nút "Thử lại" — lỗi một câu hỏi thì câu ấy đã được trả lại vào ô nhập.
  const [nap, setNap] = useState<"dang" | "xong" | "loi">("dang");
  const [lanThu, setLanThu] = useState(0);

  useEffect(() => {
    let huy = false;
    (async () => {
      try {
        setLoi("");
        setNap("dang");
        if (orderCode) {
          const history = await fetchAdvisorTurns(sessionId, orderCode);
          if (huy) return;
          setLuot(history.items);
          setNap("xong");
          return;
        }
        if (moDau.current?.moc !== moc) {
          const hua = openAgentTurn(sessionId, moc);
          moDau.current = { moc, hua };
          hua.catch(() => {
            // Chỉ bỏ đúng promise đã hỏng — một lời gọi mới hơn có thể đã thay chỗ.
            if (moDau.current?.hua === hua) moDau.current = null;
          });
        }
        await moDau.current!.hua;
        // Lịch sử đã chứa lượt mở đầu — lấy từ máy chủ thay vì tự ghép, để tải
        // lại trang không sinh thêm một bản sao.
        const day = await fetchAgentState(sessionId);
        if (huy) return;
        setTrangThai(day);
        setLuot(day.turns);
        setGoiY(day.next_best_action);
        setNap("xong");
      } catch (reason) {
        if (!huy) {
          setNap("loi");
          setLoi(
            reason instanceof Error
              ? reason.message
              : "Chưa mở được phòng tư vấn.",
          );
        }
      }
    })();
    return () => {
      huy = true;
    };
  }, [sessionId, orderCode, moc, lanThu]);

  useEffect(() => {
    cuoiRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [luot.length]);

  const hoi = useCallback(
    async (cau: string) => {
      if (!cau.trim() || dangHoi) return;
      setDangHoi(true);
      setLoi("");
      setNoiDung("");
      try {
        const ra = orderCode
          ? await askAdvisor(sessionId, orderCode, cau.trim())
          : await askAgent(sessionId, cau.trim());
        if (!alive.current) return;
        setLuot((truoc) => [
          ...truoc,
          { question: ra.question, answer: ra.answer, source: ra.source },
        ]);
        if (isAgentReply(ra)) {
          setDeXuat(ra.facts_to_save);
          setGoiY(ra.suggested_action ?? ra.next_best_action);
          setTrangThai((truoc) => (truoc ? { ...truoc, ...ra } : truoc));
        }
      } catch (reason) {
        if (!alive.current) return;
        setNoiDung(cau);
        setLoi(
          reason instanceof Error ? reason.message : "Chưa gửi được câu hỏi.",
        );
      } finally {
        if (alive.current) setDangHoi(false);
      }
    },
    [sessionId, orderCode, dangHoi],
  );

  const xacNhan = useCallback(
    async (muc: ProposedFact) => {
      setDangLuu(muc.field);
      setLoi("");
      try {
        await confirmAgentFact(sessionId, muc.field, muc.value);
        if (!alive.current) return;
        setDeXuat((truoc) => truoc.filter((d) => d.field !== muc.field));
        const day = await fetchAgentState(sessionId);
        if (!alive.current) return;
        setTrangThai(day);
        await onProfileChanged?.();
      } catch (reason) {
        if (!alive.current) return;
        setLoi(
          reason instanceof Error ? reason.message : "Chưa lưu được, bạn thử lại.",
        );
      } finally {
        if (alive.current) setDangLuu(null);
      }
    },
    [sessionId, onProfileChanged],
  );

  const guiForm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void hoi(noiDung);
  };

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5"
      aria-label={orderCode ? `Phòng tư vấn đơn ${orderCode}` : "Phòng tư vấn hồ sơ"}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold text-slate-900">
          {orderCode ? `Tư vấn đơn ${orderCode}` : "Tư vấn theo hồ sơ của bạn"}
        </h3>
        {trangThai && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            {trangThai.stage_label}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm leading-6 text-slate-600">
        {orderCode
          ? `Trợ lý đối chiếu hồ sơ của bạn với đơn ${orderCode}, giúp giải thích điều kiện, điểm còn thiếu và hướng chuẩn bị.`
          : "Trợ lý đọc hồ sơ của bạn, hỏi thêm thông tin còn thiếu và tư vấn hướng đi hoặc đơn phù hợp. Thông tin mới chỉ được lưu khi bạn xác nhận."}
        {" "}Câu hỏi chung về chương trình thì hỏi khung chat ở góc màn hình.
      </p>

      {luot.length > 0 && (
        <div className="mt-4 space-y-4">
          {luot.map((l, i) => (
            <div key={`${i}-${l.question}`} className="space-y-2">
              {/* Lượt mở đầu do hệ thống sinh: không hiện câu hỏi giả "[hệ thống] …"
                  cho người dùng đọc — họ không hỏi câu đó. */}
              {!l.question.startsWith("[hệ thống]") && (
                <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-slate-100 px-4 py-2.5 text-sm leading-6 text-slate-800">
                  {l.question}
                </p>
              )}
              <div
                className={`max-w-[92%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm leading-6 ${
                  l.source === "khong_biet"
                    ? "bg-amber-50 text-amber-900 ring-1 ring-amber-200"
                    : l.source === "khong_goi_duoc"
                      ? "bg-slate-50 text-slate-700 ring-1 ring-slate-200"
                      : "bg-[#fdf2f2] text-slate-800"
                }`}
              >
                {/* Ba trạng thái, không phải hai. "Trợ lý không đoán" là bot đã
                    cân nhắc rồi chịu dừng. "Trợ lý đang bận" là không gọi được
                    mô hình — một sự cố kỹ thuật. Dán nhãn thận trọng lên một lần
                    dịch vụ chết là nhận công không phải của mình, và tệ hơn: ứng
                    viên tưởng công ty không có thông tin nên thôi không hỏi nữa. */}
                {l.source === "khong_biet" && (
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
                    Trợ lý không đoán
                  </p>
                )}
                {l.source === "khong_goi_duoc" && (
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Trợ lý đang bận
                  </p>
                )}
                {l.answer}
              </div>
            </div>
          ))}
          <div ref={cuoiRef} />
        </div>
      )}

      {deXuat.length > 0 && (
        <div className="mt-4 space-y-2 rounded-xl border border-sky-200 bg-sky-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-800">
            Trợ lý nghe được, cần bạn xác nhận
          </p>
          {/* Nói rõ: chưa có gì vào hồ sơ. Một dòng hiện ra mà người đọc tưởng
              hệ thống đã lưu thì họ sẽ không bấm, và dữ liệu mất. */}
          <p className="text-sm leading-6 text-sky-900">
            Những mục dưới đây <strong>chưa được lưu</strong>. Bạn bấm xác nhận thì
            trợ lý mới ghi vào hồ sơ.
          </p>
          {deXuat.map((muc) => (
            <div
              key={muc.field}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-3 py-2"
            >
              <span className="text-sm text-slate-800">
                {TEN_TRUONG[muc.field] ?? muc.field}:{" "}
                <strong>{docGiaTri(muc.field, muc.value, muc.value_label)}</strong>
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void xacNhan(muc)}
                  disabled={dangLuu !== null}
                  className="rounded-lg bg-[#cb1d1e] px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {dangLuu === muc.field ? "Đang lưu…" : "Đúng, lưu lại"}
                </button>
                <button
                  type="button"
                  disabled={dangLuu !== null}
                  onClick={() =>
                    setDeXuat((truoc) =>
                      truoc.filter((d) => d.field !== muc.field),
                    )
                  }
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700"
                >
                  Không đúng
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {trangThai && trangThai.suggested_questions.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Trợ lý đang cần biết thêm
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {trangThai.suggested_questions.map((cau) => (
              <button
                key={cau}
                type="button"
                onClick={() => setNoiDung(cau)}
                className="rounded-full border border-slate-300 px-3.5 py-1.5 text-left text-sm text-slate-700 hover:border-[#cb1d1e] hover:text-[#cb1d1e]"
              >
                {cau}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {/* Câu hỏi bấm được, chọn theo trạng thái thật.
            Không dùng một danh sách cố định: phòng tư vấn theo đơn từng hiện
            "Vì sao em chưa đạt đơn này?" cho một hồ sơ ĐẠT hết điều kiện — mời
            người dùng hỏi một câu sai tiền đề rồi bắt trợ lý gỡ. */}
        {orderCode ? (
          <GoiY onChon={setNoiDung} cac={["Em còn thiếu gì cho đơn này?", "Tổng chi phí em phải chuẩn bị là bao nhiêu?"]} />
        ) : trangThai?.eligible_count == null ? (
          <GoiY onChon={setNoiDung} cac={["Hồ sơ em còn thiếu thông tin gì?", "Em nên chuẩn bị gì tiếp theo?"]} />
        ) : trangThai.eligible_count > 0 ? (
          <GoiY onChon={setNoiDung} cac={["Em nên chọn đơn nào?", "Đơn nào đi sớm nhất?"]} />
        ) : (
          <GoiY onChon={setNoiDung} cac={["Vì sao em chưa đạt?", "Em cần học bao lâu thì đủ?"]} />
        )}
      </div>

      {nap === "dang" && luot.length === 0 && (
        <p className="mt-4 text-sm text-slate-500" role="status">
          Trợ lý đang mở phòng tư vấn…
        </p>
      )}

      {loi && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          <p>{loi}</p>
          {/* Chỉ lỗi NẠP mới có nút này. Lỗi của một câu hỏi thì câu ấy đã được
              trả lại vào ô nhập — bấm "Hỏi" lần nữa là thử lại. */}
          {nap === "loi" && (
            <button
              type="button"
              onClick={() => setLanThu((n) => n + 1)}
              className="rounded-lg border border-red-300 bg-white px-3 py-1.5 font-semibold text-red-700"
            >
              Thử lại
            </button>
          )}
        </div>
      )}

      <form onSubmit={guiForm} className="mt-4 flex gap-2">
        <input
          value={noiDung}
          onChange={(e) => setNoiDung(e.target.value)}
          maxLength={500}
          placeholder={orderCode ? "Bạn muốn hỏi gì về đơn này?" : "Bạn muốn hỏi gì về hồ sơ của mình?"}
          aria-label={orderCode ? "Câu hỏi về đơn này" : "Câu hỏi về hồ sơ"}
          className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-[#cb1d1e]"
        />
        <button
          disabled={dangHoi || !noiDung.trim()}
          className="rounded-xl bg-[#cb1d1e] px-5 py-3 font-semibold text-white disabled:opacity-50"
        >
          {dangHoi ? "Đang hỏi…" : "Hỏi"}
        </button>
      </form>

      {goiY && goiY.type !== "none" && (
        <p className="mt-3 text-sm text-slate-600">
          Bước tiếp theo trợ lý gợi ý: <strong>{goiY.label}</strong>
          {goiY.target ? ` (${goiY.target})` : ""}
        </p>
      )}
    </section>
  );
}

function GoiY({
  cac,
  onChon,
}: {
  cac: string[];
  onChon: (cau: string) => void;
}) {
  return (
    <>
      {cac.map((cau) => (
        <button
          key={cau}
          type="button"
          onClick={() => onChon(cau)}
          className="rounded-full border border-slate-300 px-3.5 py-1.5 text-sm text-slate-700 hover:border-[#cb1d1e] hover:text-[#cb1d1e]"
        >
          {cau}
        </button>
      ))}
    </>
  );
}
