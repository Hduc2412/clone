/**
 * Một hành trình ẩn danh dùng chung cho chat và CV.
 *
 * ## Mã phiên nay do máy chủ cấp
 *
 * Trước 22/09/2026 trình duyệt tự sinh mã bằng `crypto.randomUUID()` rồi coi nó
 * là danh tính. Máy chủ tin vào mã ấy, nên ai gửi lên mã của người khác là đọc
 * và sửa được hồ sơ của họ.
 *
 * Nay máy chủ phát một cookie `httponly` đã ký gắn với mã phiên, và chỉ máy chủ
 * mới sinh được mã. JavaScript ở đây **không đọc được cookie đó** — đúng như
 * thiết kế. Thứ giữ trong `localStorage` chỉ còn là một bản sao của mã để hiển
 * thị và để gọi API; nó không còn là bằng chứng danh tính nữa.
 *
 * Hệ quả: mọi lời gọi tới backend phải kèm `credentials: "include"`, nếu không
 * trình duyệt sẽ không gửi cookie sang cổng khác và mọi thứ trả về 401.
 */
const KEY = "xkld-candidate-session";
const CHAT_KEY = "xkld-chat-state-v1";
const UUID = /^(?:[a-f0-9]{32}|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})$/i;

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

/** Tránh mở nhiều phiên cùng lúc khi vài thành phần cùng gọi lúc trang vừa tải. */
let dangMoPhien: Promise<string> | null = null;

/**
 * Mã phiên hiện tại, hỏi máy chủ nếu chưa có.
 *
 * Trả về chuỗi rỗng khi máy chủ không với tới được — nơi gọi phải xử lý được
 * trường hợp đó thay vì bịa ra một mã, vì mã tự bịa nay không có cookie đi kèm
 * nên gọi API nào cũng hỏng.
 */
export async function ensureSessionId(): Promise<string> {
  if (typeof window === "undefined") return "";
  if (dangMoPhien) return dangMoPhien;

  dangMoPhien = (async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/public/phien`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return peekSessionId();
      const { session_id: sessionId } = await res.json();
      if (typeof sessionId === "string" && UUID.test(sessionId)) {
        window.localStorage.setItem(KEY, sessionId);
        return sessionId;
      }
      return peekSessionId();
    } catch {
      // Mất mạng hoặc backend chưa chạy. Trả mã cũ nếu có — có thể cookie vẫn
      // còn hiệu lực và lần gọi sau sẽ thành công.
      return peekSessionId();
    } finally {
      dangMoPhien = null;
    }
  })();

  return dangMoPhien;
}

/**
 * Hỏi lại máy chủ cho chắc, bỏ qua mọi thứ đang giữ trong máy.
 *
 * Mã trong `localStorage` có thể lệch khỏi cookie: cookie bị xoá, hết hạn, hoặc
 * được ký bằng khoá khác (xảy ra thật khi hai backend cùng chạy trên cùng tên
 * host). Khi lệch, mọi lời gọi `/public/*` trả 401 và trang chết hẳn với câu
 * "phiên đã hết hạn" — người dùng tải lại bao nhiêu lần cũng vậy, vì bản sao
 * hỏng trong máy vẫn còn đó.
 *
 * Hàm này là đường thoát: hỏi máy chủ, lấy mã thật, ghi đè bản sao trong máy.
 */
export async function refreshSessionId(): Promise<string> {
  if (typeof window === "undefined") return "";
  window.localStorage.removeItem(KEY);
  dangMoPhien = null;
  return ensureSessionId();
}

/**
 * Ghi lại mã phiên do máy chủ trả về.
 *
 * Lượt chat đầu tiên cũng mở phiên, và mã thật nằm trong phản hồi chứ không do
 * trình duyệt tự nghĩ ra. Ghi lại để trang gửi CV dùng chung đúng hành trình —
 * nếu không, khách chat xong bấm sang tư vấn sẽ thành hai người khác nhau.
 */
export function rememberSessionId(sessionId: string): void {
  if (typeof window === "undefined") return;
  if (UUID.test(sessionId)) window.localStorage.setItem(KEY, sessionId);
}

/**
 * Đọc mã phiên đang có mà **không** gọi máy chủ.
 *
 * Trang theo dõi hồ sơ cần phân biệt "chưa từng dùng trên máy này" với "đã có
 * hồ sơ", nên nó cần một hàm không tạo gì cả. Trả chuỗi rỗng khi chưa có gì.
 */
export function peekSessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(KEY);
  return existing && UUID.test(existing) ? existing : "";
}

/**
 * Mã phiên đang giữ, dùng cho lời gọi đồng bộ.
 *
 * Khác bản cũ ở chỗ **không tự sinh mã mới**: mã tự sinh nay vô dụng vì không
 * có cookie đi kèm. Nơi nào cần chắc chắn có phiên thì phải `await
 * ensureSessionId()`.
 */
export function getSessionId(): string {
  return peekSessionId();
}

/**
 * Mở một phiên MỚI. Trả mã phiên mới, hoặc chuỗi rỗng nếu không mở được.
 *
 * ## Căn cứ là câu trả lời của `/public/phien/moi`, không phải `ensureSessionId`
 *
 * Bản trước xoá mã trong máy, gọi `/phien/moi` mà không xem kết quả, rồi hỏi
 * `ensureSessionId()`. Máy chủ trả 503 thì `fetch` không ném lỗi, cookie vẫn là
 * cookie CŨ, nên `ensureSessionId` trả lại đúng phiên cũ — một mã không rỗng —
 * và giao diện tưởng đã sang phiên mới rồi xoá màn hình. Chủ đồ án tái hiện được
 * ngày 06/10.
 *
 * Nay chỉ coi là đã sang phiên mới khi `/phien/moi` trả `ok` VÀ mang một mã hợp
 * lệ KHÁC mã cũ. Chưa chắc chắn thì không đụng gì cả: mã cũ vẫn trong máy, lịch
 * sử chat vẫn còn, không phát sự kiện — vì phiên cũ vẫn đang là phiên thật của
 * cookie, và mọi thứ trên màn hình vẫn đúng với nó.
 */
export async function resetSession(): Promise<string> {
  if (typeof window === "undefined") return "";
  const cu = peekSessionId();
  let moi = "";
  try {
    // Không xoá được cookie từ đây (`httponly`), nên xin máy chủ một phiên khác.
    const res = await fetch(`${BACKEND_URL}/public/phien/moi`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      const { session_id: sessionId } = await res.json();
      if (typeof sessionId === "string" && UUID.test(sessionId) && sessionId !== cu) {
        moi = sessionId;
      }
    }
  } catch {
    /* Mất mạng: chưa có phiên mới. Người gọi báo lỗi, khách thử lại. */
  }
  if (!moi) return "";

  window.localStorage.setItem(KEY, moi);
  window.sessionStorage.removeItem(CHAT_KEY);
  window.dispatchEvent(new Event("xkld-journey-reset"));
  return moi;
}
