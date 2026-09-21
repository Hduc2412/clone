/**
 * Gọi các endpoint công khai của hệ thống nghiệp vụ.
 *
 * File riêng, không đụng tới `lib/api.ts` của khung chat. Hai phần do hai người
 * phát triển song song, dùng chung một file là chuốc lấy xung đột mỗi lần sửa.
 *
 * Hai địa chỉ khác nhau cho hai môi trường: trình duyệt đi qua địa chỉ công khai,
 * còn thành phần chạy trên máy chủ gọi thẳng vào mạng nội bộ. Khi chạy bằng
 * Docker, hai địa chỉ này không giống nhau.
 */

export const BACKEND_PUBLIC_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL || BACKEND_PUBLIC_URL;

export interface JobOrderLabels {
  status: string | null;
  employer_type: string | null;
  program: string | null;
  region_group: string | null;
  japanese_required: string | null;
  education_required: string | null;
  gender_pref: string | null;
}

export interface JobOrderRequirements {
  japanese_required: string;
  education_required: string | null;
  experience_min: number;
  age_min: number | null;
  age_max: number | null;
  gender_pref: string;
}

export interface JobOrderReference {
  salary_min: number | null;
  salary_max: number | null;
  allowances: string[];
  cost_total_vnd: number | null;
  interview_date: string | null;
  departure_expected: string | null;
  highlights: string[];
}

export interface PublicJobOrder {
  code: string;
  title: string;
  employer_name: string;
  employer_type: string;
  program: string;
  prefecture: string;
  region_group: string | null;
  city: string | null;
  quota: number;
  deadline: string;
  requirements: JobOrderRequirements;
  reference: JobOrderReference;
  description: string | null;
  labels: JobOrderLabels;
}

export interface JobOrderFacets {
  prefectures: string[];
  region_groups: string[];
  employer_types: string[];
  programs: string[];
  japanese_levels: string[];
}

export interface JobOrderFilters {
  prefecture?: string;
  region_group?: string;
  employer_type?: string;
  program?: string;
  japanese_required?: string;
  limit?: number;
}

function buildQuery(filters: JobOrderFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

/**
 * Dữ liệu đơn hàng được dựng lại mỗi phút. Danh mục đổi vài lần một ngày, nên
 * dựng lại mỗi lần có người vào trang là lãng phí, mà dựng một lần rồi thôi thì
 * đơn đã đóng vẫn còn nằm trên web.
 */
const REVALIDATE_SECONDS = 60;

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${BACKEND_INTERNAL_URL}${path}`, {
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    // Backend chưa chạy là chuyện bình thường lúc phát triển giao diện. Trang
    // vẫn phải dựng được và hiện trạng thái rỗng, thay vì đổ lỗi ra màn hình.
    return fallback;
  }
}

export function fetchJobOrders(
  filters: JobOrderFilters = {},
): Promise<PublicJobOrder[]> {
  return getJson<PublicJobOrder[]>(
    `/public/job-orders${buildQuery(filters)}`,
    [],
  );
}

export async function fetchJobOrder(
  code: string,
): Promise<PublicJobOrder | null> {
  return getJson<PublicJobOrder | null>(
    `/public/job-orders/${encodeURIComponent(code)}`,
    null,
  );
}

export function fetchJobOrderFacets(): Promise<JobOrderFacets> {
  return getJson<JobOrderFacets>("/public/job-orders/facets", {
    prefectures: [],
    region_groups: [],
    employer_types: [],
    programs: [],
    japanese_levels: [],
  });
}
