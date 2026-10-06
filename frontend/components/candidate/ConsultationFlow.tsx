"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import AdvisorChat from "./AdvisorChat";
import CvUpload from "@/components/candidate/CvUpload";
import MatchCard from "@/components/candidate/MatchCard";
import {
  NumberField,
  SelectField,
  TextField,
  TriStateField,
} from "@/components/candidate/fields";
import { Badge, Button, Card } from "@/components/ui/primitives";
import {
  ApiError,
  CandidateProfile,
  MatchResult,
  PreferenceFormValues,
  ProfileFormValues,
  ProfileMeta,
  confirmProfile,
  MyRegistration,
  RegistrationResult,
  createProfile,
  fetchMatches,
  fetchMyRegistrations,
  fetchProfile,
  fetchProfileMeta,
  ensureSessionId,
  refreshSessionId,
  getSessionId,
  registerForOrder,
  resetSession,
  updateProfile,
  valueOf,
} from "@/lib/candidateApi";

type Step = "form" | "results";

interface FormState {
  full_name: string;
  birth_year: string;
  gender: string;
  education_level: string;
  major: string;
  japanese_level: string;
  experience_years: string;
  care_experience: boolean | undefined;
  phone: string;
  desired_prefecture: string;
  desired_employer_type: string;
  salary_expectation_jpy: string;
  budget_vnd: string;
}

const EMPTY: FormState = {
  full_name: "",
  birth_year: "",
  gender: "",
  education_level: "",
  major: "",
  japanese_level: "",
  experience_years: "",
  care_experience: undefined,
  phone: "",
  desired_prefecture: "",
  desired_employer_type: "",
  salary_expectation_jpy: "",
  budget_vnd: "",
};

/** Đổ hồ sơ đã lưu ngược vào biểu mẫu, để người quay lại không phải gõ lại. */
function fromProfile(profile: CandidateProfile): FormState {
  const f = profile.fields;
  const p = profile.preferences;
  const text = (section: typeof f, key: string) => {
    const value = valueOf<string | number>(section, key);
    return value === undefined || value === null ? "" : String(value);
  };
  return {
    full_name: text(f, "full_name"),
    birth_year: text(f, "birth_year"),
    gender: text(f, "gender"),
    education_level: text(f, "education_level"),
    major: text(f, "major"),
    japanese_level: text(f, "japanese_level"),
    experience_years: text(f, "experience_years"),
    care_experience: valueOf<boolean>(f, "care_experience"),
    phone: text(f, "phone"),
    desired_prefecture: text(p, "desired_prefecture"),
    desired_employer_type: text(p, "desired_employer_type"),
    salary_expectation_jpy: text(p, "salary_expectation_jpy"),
    budget_vnd: text(p, "budget_vnd"),
  };
}

export default function ConsultationFlow() {
  // Mã phiên nay do máy chủ cấp kèm cookie đã ký, nên lần vẽ đầu tiên chưa
  // có. Giữ trong state để phần gửi CV không vẽ ra với mã rỗng.
  const [sessionId, setSessionId] = useState("");
  const [meta, setMeta] = useState<ProfileMeta | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [step, setStep] = useState<Step>("form");
  const [showProfileForm, setShowProfileForm] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [booting, setBooting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [registrations, setRegistrations] = useState<MyRegistration[]>([]);
  const [justRegistered, setJustRegistered] = useState<RegistrationResult | null>(null);
  const [registering, setRegistering] = useState<string | null>(null);

/** Mã phiên rỗng thì dừng ngay, với một câu nói đúng chuyện gì đang xảy ra.
 *
 * `ensureSessionId` trả chuỗi rỗng khi máy chủ không trả lời VÀ trong máy chưa
 * có mã nào — đúng trường hợp khách vào lần đầu lúc mạng chập chờn. Bản trước đi
 * tiếp với mã rỗng, gọi `fetchProfile("")`, rồi hiện lỗi của một đường dẫn hỏng
 * thay vì nói thẳng là chưa kết nối được. */
const LOI_KHONG_MO_DUOC_PHIEN =
  "Chưa mở được phiên tư vấn — có thể mạng đang chập chờn. Bạn bấm Thử lại nhé.";
function moPhien(sessionId: string): string {
  if (!sessionId) throw new Error(LOI_KHONG_MO_DUOC_PHIEN);
  return sessionId;
}

/** "Khai lại từ đầu" hỏng thì màn hình đó không có nút "Thử lại" nào — nút để bấm
 * lại chính là "Khai lại từ đầu". Kiểm trên trình duyệt ngày 06/10: câu chung bảo
 * "bấm Thử lại" và khách đi tìm một nút không tồn tại. */
const LOI_KHAI_LAI =
  "Chưa mở được phiên tư vấn mới — có thể mạng đang chập chờn. Hồ sơ hiện tại vẫn " +
  "giữ nguyên; bạn bấm lại “Khai lại từ đầu” nhé.";

/** Máy chủ từ chối vì phiên, không phải vì dữ liệu. */
function khong_nhan_phien(reason: unknown): boolean {
  const status = (reason as { status?: number })?.status;
  return status === 401 || status === 403;
}

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  // Khởi động: lấy danh mục, và nếu trình duyệt này đã khai hồ sơ trước đó thì
  // đưa thẳng tới kết quả thay vì bắt gõ lại từ đầu.
  useEffect(() => {
    let alive = true;
    (async () => {
      // Mã trong máy có thể lệch khỏi cookie (cookie bị xoá, hết hạn, hay ký
      // bằng khoá khác). Khi lệch thì mọi lời gọi trả 401 và trang chết hẳn —
      // tải lại bao nhiêu lần cũng vậy, vì bản sao hỏng vẫn nằm trong máy. Nên
      // thử một lần nữa với mã hỏi thẳng máy chủ trước khi báo lỗi cho người dùng.
      try {
        // Lấy mã phiên NẰM TRONG `try`.
        //
        // `ensureSessionId` tự bắt lỗi mạng, nên mất mạng không làm nó ném. Nhưng
        // nó chạm `localStorage` ngoài `try` của chính nó, và trình duyệt chặn bộ
        // nhớ trang thì chỗ ấy ném. Để ngoài `try` ở đây là `booting` không bao
        // giờ về `false` — trang treo ở "Đang tải biểu mẫu…", không lỗi, không nút.
        let sessionId = moPhien(await ensureSessionId());
        if (alive) setSessionId(sessionId);
        let ho_so_ban_dau;
        try {
          ho_so_ban_dau = await fetchProfile(sessionId);
        } catch (reason) {
          if (!khong_nhan_phien(reason)) throw reason;
          sessionId = moPhien(await refreshSessionId());
          if (alive) setSessionId(sessionId);
          ho_so_ban_dau = await fetchProfile(sessionId);
        }
        const [catalog, existing, mine] = await Promise.all([
          fetchProfileMeta(),
          Promise.resolve(ho_so_ban_dau),
          // Đơn đã đăng ký từ lần trước. Không có thì trả mảng rỗng chứ không
          // làm hỏng cả trang — phần lớn người vào lần đầu chưa đăng ký gì.
          fetchMyRegistrations(sessionId).catch(() => ({ items: [] })),
        ]);
        if (!alive) return;
        setMeta(catalog);
        setRegistrations(mine.items);
        if (existing) {
          setProfile(existing);
          setForm(fromProfile(existing));
          if (existing.status === "confirmed") {
            const matches = await fetchMatches(sessionId);
            if (!alive) return;
            setResult(matches);
            setStep("results");
          }
        }
      } catch (reason) {
        if (alive) setError((reason as Error).message);
      } finally {
        if (alive) setBooting(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  /** Hồ sơ vừa đổi qua phòng tư vấn thì kết quả đối chiếu phải tính lại.
   *
   * `refresh: true` bắt buộc. Kết quả được cache mười phút theo phiên bản hồ sơ
   * và dấu vân tay danh mục đơn; không có cờ này thì ứng viên vừa xác nhận thêm
   * một trường sẽ nhìn đúng bảng xếp hạng cũ, và kết luận là xác nhận chẳng có
   * tác dụng gì. */
  const taiLaiKetQua = useCallback(async () => {
    const id = getSessionId();
    if (!id) return;
    try {
      setResult(await fetchMatches(id, { refresh: true }));
    } catch {
      /* Hồ sơ có thể vừa rời trạng thái đã xác nhận. Giữ bảng cũ, không xoá
         màn hình của người đang đọc. */
    }
  }, []);

  const register = useCallback(async (jobOrderCode: string) => {
    setRegistering(jobOrderCode);
    setError("");
    try {
      const created = await registerForOrder(getSessionId(), jobOrderCode);
      setJustRegistered(created);
      const mine = await fetchMyRegistrations(getSessionId());
      setRegistrations(mine.items);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Chưa gửi được đăng ký, bạn thử lại giúp em.",
      );
    } finally {
      setRegistering(null);
    }
  }, []);

  const registeredCodes = useMemo(
    () => new Set(registrations.map((row) => row.job_order_code)),
    [registrations],
  );

  // Đang có hồ sơ chờ nhân viên xử lý thì không mở đăng ký đơn thứ hai. Phía máy
  // chủ cũng chặn, nhưng để nút sáng rồi mới báo lỗi là bắt người dùng bấm vào
  // một thứ chắc chắn hỏng.
  const hasOpenRegistration = registrations.length > 0;

  const validate = useCallback((): boolean => {
    const found: Record<string, string> = {};
    if (form.full_name.trim().length < 2) {
      found.full_name = "Bạn cho em xin họ tên đầy đủ.";
    }
    if (!form.japanese_level) {
      found.japanese_level =
        "Mục này quyết định đơn nào bạn nộp được. Chưa học thì chọn 'Chưa học'.";
    }
    if (form.birth_year) {
      const year = Number(form.birth_year);
      const newest = new Date().getFullYear() - 15;
      if (year < 1950 || year > newest) {
        found.birth_year = `Năm sinh cần nằm trong khoảng 1950 đến ${newest}.`;
      }
    }
    setErrors(found);
    if (Object.keys(found).length > 0) setShowProfileForm(true);
    return Object.keys(found).length === 0;
  }, [form]);

  const submit = async () => {
    setError("");
    if (!validate()) return;

    setBusy(true);
    const sessionId = getSessionId();
    const fields: ProfileFormValues = {
      full_name: form.full_name.trim(),
      birth_year: form.birth_year ? Number(form.birth_year) : undefined,
      gender: form.gender || undefined,
      education_level: form.education_level || undefined,
      major: form.major.trim() || undefined,
      japanese_level: form.japanese_level,
      experience_years: form.experience_years
        ? Number(form.experience_years)
        : undefined,
      care_experience: form.care_experience,
      phone: form.phone.trim() || undefined,
    };
    const preferences: PreferenceFormValues = {
      desired_prefecture: form.desired_prefecture || undefined,
      desired_employer_type: form.desired_employer_type || undefined,
      salary_expectation_jpy: form.salary_expectation_jpy
        ? Number(form.salary_expectation_jpy)
        : undefined,
      budget_vnd: form.budget_vnd ? Number(form.budget_vnd) : undefined,
    };

    try {
      // Chat may have created a draft after this form was opened.
      const currentProfile = profile ?? await fetchProfile(sessionId);
      let saved = currentProfile
        ? await updateProfile(sessionId, fields, preferences, currentProfile.version)
        : await createProfile(sessionId, fields, preferences);
      if (saved.status !== "confirmed") {
        saved = await confirmProfile(sessionId);
      }
      setProfile(saved);
      setResult(await fetchMatches(sessionId));
      setStep("results");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (reason) {
      const apiError = reason as ApiError;
      setError(apiError.message);
      if (apiError.missing?.length) {
        setShowProfileForm(true);
        setErrors(
          Object.fromEntries(
            apiError.missing.map((key) => [key, "Mục này cần điền để đối chiếu."]),
          ),
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const startOver = async () => {
    // Mở phiên mới TRƯỚC, xóa màn hình SAU — và chỉ xóa khi đã có phiên mới.
    //
    // Bản trước xóa trắng màn hình bất kể `resetSession` trả gì. Mất mạng đúng lúc
    // bấm "Khai lại từ đầu" thì khách nhìn một biểu mẫu trống không có ô gửi CV
    // (ô ấy không vẽ với mã rỗng), không một lời giải thích.
    let moi: string;
    try {
      moi = moPhien(await resetSession());
    } catch {
      setError(LOI_KHAI_LAI);
      return;
    }
    // Xóa MỌI trạng thái gắn với phiên cũ — không chỉ hồ sơ và kết quả.
    //
    // Bản trước bỏ sót ba thứ của phần đăng ký. Chủ đồ án tái hiện ngày 06/10:
    // khai lại, khai hồ sơ mới, xem kết quả — vẫn hiện "bạn đang có hồ sơ đăng ký
    // đơn …" của phiên trước, và đơn ấy hiện là "đã đăng ký" trên thẻ. Danh mục
    // (`meta`) là thứ duy nhất được giữ: nó không thuộc về phiên nào.
    setSessionId(moi);
    setProfile(null);
    setResult(null);
    setForm(EMPTY);
    setErrors({});
    setError("");
    setStep("form");
    setShowProfileForm(false);
    setRegistrations([]);
    setJustRegistered(null);
    setRegistering(null);
  };

  const summary = useMemo(() => {
    if (!profile) return [];
    // Không giả định `labels` luôn có. Một bảng tóm tắt thiếu vài dòng thì vẫn
    // đọc được; còn để nó ném lỗi thì cả trang tư vấn trắng xoá và ứng viên mất
    // sạch thứ vừa khai. Đã xảy ra thật khi endpoint gửi CV trả hồ sơ chưa gắn nhãn.
    const labels = profile.labels ?? {};
    const items = [
      ["Họ tên", valueOf<string>(profile.fields, "full_name")],
      ["Năm sinh", valueOf<number>(profile.fields, "birth_year")],
      ["Tiếng Nhật", labels.japanese_level],
      ["Bằng cấp", labels.education_level],
      ["Nơi mong muốn", labels.desired_region_group],
      ["Loại hình", labels.desired_employer_type],
    ];
    return items.filter(([, value]) => value !== undefined && value !== null);
  }, [profile]);

  if (booting) {
    return (
      <Card className="p-8 text-center text-sm text-slate-500">
        Đang tải biểu mẫu…
      </Card>
    );
  }

  if (!meta) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-slate-600">
          Chưa kết nối được máy chủ nên biểu mẫu chưa dùng được.
          {error && <span className="mt-1 block text-brand-600">{error}</span>}
        </p>
        <div className="mt-4">
          <Button onClick={() => window.location.reload()}>Thử lại</Button>
        </div>
      </Card>
    );
  }

  if (step === "results" && result) {
    return (
      <div className="space-y-6">
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-ink-900">Hồ sơ đã ghi nhận</p>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-slate-600">
                {summary.map(([label, value]) => (
                  <span key={String(label)}>
                    {label}: <span className="text-ink-900">{String(value)}</span>
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setStep("form")}>
                Sửa hồ sơ
              </Button>
              <Button variant="ghost" onClick={startOver}>
                Khai lại từ đầu
              </Button>
            </div>
          </div>
          {/* Bước kết quả trước đây KHÔNG vẽ `error`, dù hai việc ở đúng bước này
              báo lỗi qua nó: đăng ký một đơn, và "Khai lại từ đầu". Khách bấm, đăng
              ký hỏng hoặc không mở được phiên mới, và màn hình đứng im không một
              lời — bắt được ngày 06/10 bằng ca kiểm thử của "Khai lại từ đầu". */}
          {error && (
            <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700" role="alert">
              {error}
            </p>
          )}
        </Card>

        {justRegistered && (
          <Card className="border-emerald-200 bg-emerald-50 p-5">
            <p className="text-sm font-medium text-emerald-900">
              Đã gửi đăng ký đơn {justRegistered.job_order_code}
              {justRegistered.job_order_title
                ? ` — ${justRegistered.job_order_title}`
                : ""}
            </p>
            <p className="mt-1.5 text-sm leading-6 text-emerald-800">
              {justRegistered.message}
            </p>
            <p className="mt-2 text-xs text-emerald-700">
              Mã hồ sơ của bạn: {justRegistered.application_code}. Bạn ghi lại để
              tiện đối chiếu khi nhân viên gọi.
            </p>
            <p className="mt-3 text-sm text-emerald-800">
              Theo dõi hồ sơ đang ở bước nào tại{" "}
              <Link href="/ho-so-cua-toi" className="font-semibold underline">
                Hồ sơ của tôi
              </Link>
              .
            </p>
          </Card>
        )}

        {!justRegistered && hasOpenRegistration && (
          <Card className="border-sky-200 bg-sky-50 p-5">
            <p className="text-sm text-sky-900">
              Bạn đang có hồ sơ đăng ký đơn{" "}
              <span className="font-medium">{registrations[0].job_order_code}</span>{" "}
              chờ nhân viên liên hệ. Xem hồ sơ đang ở bước nào tại{" "}
              <Link href="/ho-so-cua-toi" className="font-semibold underline">
                Hồ sơ của tôi
              </Link>
              .
            </p>
          </Card>
        )}

        {/* Phòng tư vấn đặt NGAY TRÊN danh sách thẻ đơn, không ở cuối trang.
            Danh sách thẻ đọc được, nhưng nó không trả lời câu người ta thật sự
            đang hỏi: *tóm lại tôi có cơ hội không, và vướng ở đâu*. Đặt dưới
            danh sách thì phải cuộn qua mười mấy thẻ mới thấy. */}
        {sessionId && (
          <AdvisorChat
            sessionId={sessionId}
            moc="sau_matching"
            onProfileChanged={taiLaiKetQua}
          />
        )}

        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-xl font-semibold text-ink-900">
            {result.eligible_count > 0
              ? `${result.eligible_count} đơn bạn đủ điều kiện nộp`
              : "Chưa có đơn nào bạn đủ điều kiện"}
          </h2>
          <Badge tone="neutral">đã xét {result.total_considered} đơn</Badge>
        </div>

        {/* Hai quy tắc của bộ đối chiếu, đặt NGAY cạnh kết quả.
            Trước 06/10, ý thứ nhất chỉ có ở thẻ cuối trang, ý thứ hai nằm trong
            biểu mẫu thu gọn — tức là ở xa đúng chỗ người ta đang đọc kết quả và
            tự hỏi "sao đơn kia không có". Không có hai câu này, một hồ sơ khai
            thiếu đọc kết quả như một lời từ chối. */}
        <p className="-mt-3 text-sm leading-6 text-slate-600">
          Mục nào bạn chưa khai thì hệ thống <strong>không loại đơn vì nó</strong> —
          chỉ ghi là chưa rõ và hỏi thêm. Nguyện vọng (khu vực, loại cơ sở, lương,
          chi phí) <strong>chỉ dùng để xếp thứ tự</strong>, không làm đơn nào bị loại.
        </p>

        {result.missing_info.length > 0 && (
          <Card className="border-amber-200 bg-amber-50 p-5">
            <p className="text-sm font-medium text-amber-900">
              Khai thêm mấy mục này thì kết quả chắc hơn
            </p>
            <p className="mt-1 text-sm text-amber-800">
              Thiếu thông tin không làm bạn mất đơn nào — hệ thống để “chưa rõ” chứ
              không loại. Nhưng biết thêm thì xếp hạng sát với bạn hơn.
            </p>
            <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-amber-900">
              {result.missing_info.slice(0, 5).map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
            <div className="mt-4">
              <Button variant="secondary" onClick={() => setStep("form")}>
                Bổ sung thông tin
              </Button>
            </div>
          </Card>
        )}

        {result.matches.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-sm text-slate-600">
              Với hồ sơ hiện tại, chưa đơn nào trong danh mục đạt đủ điều kiện bắt
              buộc. Bạn thử bổ sung thông tin, hoặc gọi hotline để được tư vấn đơn
              sắp mở.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button onClick={() => setStep("form")}>Bổ sung hồ sơ</Button>
              <Button variant="secondary" href="/lien-he">
                Liên hệ tư vấn
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {result.matches.map((item) => (
              <MatchCard
                key={item.code}
                item={item}
                onRegister={register}
                registering={registering === item.code}
                registered={registeredCodes.has(item.code)}
                disabled={hasOpenRegistration}
              />
            ))}
          </div>
        )}

        <p className="rounded-xl bg-slate-100 px-4 py-3 text-xs leading-5 text-slate-600">
          {result.disclaimer}
        </p>
      </div>
    );
  }

  return (
    <Card className="p-5 sm:p-7">
      <p className="text-sm text-slate-600">
        Gửi CV để hệ thống đọc hồ sơ, sau đó trao đổi trực tiếp với trợ lý tư vấn.
        Bạn kiểm tra và xác nhận thông tin trước khi đối chiếu đơn tuyển dụng.
      </p>

      {error && (
        <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
          {error}
        </p>
      )}

      <div className="mt-6">
        {/* `key` theo phiên: ô gửi CV giữ kết quả lần đọc trong trạng thái riêng
            của nó, nên không dựng lại thì sau "Khai lại từ đầu" nó vẫn hiện "đã
            đọc xong" của CV phiên trước. `AdvisorChat` đã có `key` như vậy. */}
        <CvUpload
          key={sessionId}
          sessionId={sessionId}
          onProfileRead={(read) => {
            setProfile(read);
            setForm(fromProfile(read));
          }}
        />
      </div>

      {/* Trợ lý lên tiếng ngay sau khi máy đọc xong CV, TRƯỚC bước xác nhận.
          Đây là lúc ứng viên vừa gửi một tệp và đang chờ xem máy hiểu được gì.
          Nói lại thứ đọc được là cách duy nhất để họ phát hiện máy đọc nhầm, và
          hỏi một hai thứ còn thiếu lúc họ còn đang chú ý thì tỉ lệ được trả lời
          cao hơn hẳn so với hỏi sau. */}
      {profile && sessionId && (
        <div className="mt-6">
          <AdvisorChat
            sessionId={sessionId}
            moc="sau_cv"
            onProfileChanged={async () => {
              const moi = await fetchProfile(sessionId).catch(() => null);
              if (moi) {
                setProfile(moi);
                setForm(fromProfile(moi));
              }
            }}
          />
        </div>
      )}

      <details
        className="mt-6"
        open={showProfileForm}
        onToggle={(event) => setShowProfileForm(event.currentTarget.open)}
      >
        <summary className="cursor-pointer text-sm font-semibold text-slate-700">
          {profile ? "Xem hoặc sửa thông tin hồ sơ đã đọc" : "Chưa có CV? Khai thông tin bằng biểu mẫu"}
        </summary>
        <div className="mt-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Năng lực trên giấy tờ
          </h3>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <TextField
              label="Họ và tên"
              required
              value={form.full_name}
              onChange={(value) => set("full_name", value)}
              error={errors.full_name}
              placeholder="Nguyễn Văn An"
              maxLength={100}
            />
            <SelectField
              label="Trình độ tiếng Nhật"
              required
              hint="Chưa học cũng là một câu trả lời, vẫn có đơn phù hợp."
              value={form.japanese_level}
              onChange={(value) => set("japanese_level", value)}
              options={meta.japanese_levels}
              error={errors.japanese_level}
              emptyLabel="— Chọn mức —"
            />
            <NumberField
              label="Năm sinh"
              value={form.birth_year}
              onChange={(value) => set("birth_year", value.slice(0, 4))}
              error={errors.birth_year}
              placeholder="2003"
            />
            <SelectField
              label="Giới tính"
              hint="Một số đơn chỉ tuyển nam hoặc chỉ tuyển nữ."
              value={form.gender}
              onChange={(value) => set("gender", value)}
              options={meta.genders}
            />
            <SelectField
              label="Bằng cấp cao nhất"
              value={form.education_level}
              onChange={(value) => set("education_level", value)}
              options={meta.education_levels}
            />
            <TextField
              label="Chuyên ngành"
              value={form.major}
              onChange={(value) => set("major", value)}
              placeholder="Điều dưỡng"
              maxLength={100}
            />
            <NumberField
              label="Số năm kinh nghiệm"
              value={form.experience_years}
              onChange={(value) => set("experience_years", value.slice(0, 2))}
              suffix="năm"
              placeholder="0"
            />
            <TextField
              label="Số điện thoại"
              hint="Để nhân viên gọi lại. Không bắt buộc."
              value={form.phone}
              onChange={(value) => set("phone", value)}
              inputMode="tel"
              placeholder="09xx xxx xxx"
              maxLength={15}
            />
          </div>
          <div className="mt-5">
            <TriStateField
              label="Đã từng chăm sóc người bệnh hoặc người cao tuổi chưa?"
              hint="Kể cả chăm người nhà, thực tập hay làm bán thời gian."
              value={form.care_experience}
              onChange={(value) => set("care_experience", value)}
              yesLabel="Đã từng"
              noLabel="Chưa từng"
            />
          </div>
        </div>

        <div className="mt-8 border-t border-slate-100 pt-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Nguyện vọng
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Phần này chỉ dùng để xếp thứ tự đơn nào hợp với bạn hơn. Nó không bao giờ
            loại đơn nào ra khỏi danh sách.
          </p>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <SelectField
              label="Tỉnh mong muốn"
              hint="Nêu tỉnh là đủ, hệ thống tự suy ra vùng."
              value={form.desired_prefecture}
              onChange={(value) => set("desired_prefecture", value)}
              options={meta.prefectures}
              emptyLabel="Đâu cũng được"
            />
            <SelectField
              label="Loại hình cơ sở"
              value={form.desired_employer_type}
              onChange={(value) => set("desired_employer_type", value)}
              options={meta.employer_types}
              emptyLabel="Đâu cũng được"
            />
            <NumberField
              label="Lương mong muốn mỗi tháng"
              value={form.salary_expectation_jpy}
              onChange={(value) => set("salary_expectation_jpy", value.slice(0, 7))}
              suffix="¥"
              placeholder="190000"
            />
            <NumberField
              label="Chi phí có thể chuẩn bị"
              value={form.budget_vnd}
              onChange={(value) => set("budget_vnd", value.slice(0, 10))}
              suffix="đ"
              placeholder="150000000"
            />
          </div>
        </div>

      </details>

      <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-6">
        <Button size="lg" onClick={submit} disabled={busy}>
          {busy ? "Đang đối chiếu…" : "Xác nhận hồ sơ và xem đơn phù hợp"}
        </Button>
        {result && (
          <Button variant="ghost" onClick={() => setStep("results")}>
            Quay lại kết quả
          </Button>
        )}
        <p className="text-xs text-slate-500">
          Thông tin chỉ dùng để tư vấn, không hiển thị công khai.
        </p>
      </div>
    </Card>
  );
}
