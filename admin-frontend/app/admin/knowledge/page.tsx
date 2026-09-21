import { PageHeader } from "@/components/admin/AdminUI";

/**
 * Màn hình Tri thức AI.
 *
 * Mọi con số ở đây là **bản ghi tay**, không đọc từ Qdrant. Phần nạp tri thức
 * thuộc pipeline RAG do người khác phát triển và chưa mở API quản lý, nên màn
 * hình này chưa có nguồn dữ liệu thật để nối vào; đặc tả năm endpoint cần thiết
 * nằm ở `docs/handoff/KNOWLEDGE_BASE_SPEC.md`.
 *
 * Trước đây trang này in ba con số trần như thể chúng là số liệu sống, trong đó
 * có "0 nguồn thiếu ảnh" — con số ấy sai, thực tế là 22 trên 32 đoạn còn rác
 * nhận dạng ảnh. Một màn hình quản trị nói sai còn tệ hơn một màn hình nói
 * "chưa có dữ liệu", vì người trực sẽ tin nó. Nên giờ mỗi con số đi kèm ngày
 * ghi và lời nói rõ nó đến từ đâu.
 */

const NGAY_GHI = "30/07/2026";

const CHI_SO = [
  {
    value: "32",
    label: "Đoạn đã lập chỉ mục",
    note: `Đếm tay ngày ${NGAY_GHI}`,
  },
  {
    value: "10",
    label: "Nhóm chủ đề",
    note: "Theo VALID_TOPICS trong app/rag/taxonomy.py",
  },
  {
    value: "22",
    label: "Đoạn còn rác nhận dạng ảnh",
    note: "Đã báo nhóm chatbot, chưa xử lý xong",
    canhBao: true,
  },
];

const CHU_DE: [string, number][] = [
  ["Chi phí", 1],
  ["Quy trình", 3],
  ["Điều kiện", 1],
  ["Lương thưởng", 3],
  ["Công việc", 2],
  ["Phỏng vấn", 1],
  ["Thời gian", 2],
  ["Học tập", 14],
  ["Ký túc xá", 3],
  ["Chung", 2],
];

export default function KnowledgePage() {
  return (
    <>
      <PageHeader
        eyebrow="Cơ sở tri thức"
        title="Tri thức AI"
        description="Kho ngữ liệu khung chat dùng để trả lời. Màn hình này chưa nối được vào Qdrant — phần nạp tri thức thuộc pipeline RAG và chưa mở API quản lý."
      />

      <div className="mb-6 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900">
          Số liệu ghi tay, không phải dữ liệu sống
        </p>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-amber-800">
          Những con số dưới đây được đếm tay ngày {NGAY_GHI} và không tự cập nhật
          khi kho tri thức được nạp lại. Đừng dùng chúng để kết luận kho đang ở
          tình trạng nào. Năm endpoint cần thiết để thay bằng dữ liệu thật đã đặc
          tả trong <code>docs/handoff/KNOWLEDGE_BASE_SPEC.md</code>.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        {CHI_SO.map((item) => (
          <article
            key={item.label}
            className={`rounded-2xl border bg-white p-5 shadow-sm ${
              item.canhBao ? "border-amber-300" : "border-slate-200"
            }`}
          >
            <p
              className={`text-3xl font-semibold tracking-tight ${
                item.canhBao ? "text-amber-700" : "text-slate-900"
              }`}
            >
              {item.value}
            </p>
            <p className="mt-2 text-sm font-medium text-slate-700">{item.label}</p>
            <p className="mt-1 text-xs text-slate-400">{item.note}</p>
          </article>
        ))}
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold">Phân bố chủ đề</h3>
          <p className="mt-1 text-xs text-slate-400">
            Kho được nạp lại nhiều lần nên tên collection đang phục vụ thay đổi
            theo từng lần dựng. Muốn biết bản nào đang chạy thì tra bí danh
            <code className="mx-1">xkld_knowledge</code> trong Qdrant.
          </p>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
          {CHU_DE.map(([chuDe, soLuong]) => (
            <div
              key={chuDe}
              className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3"
            >
              <span className="text-sm text-slate-600">{chuDe}</span>
              <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm">
                {soLuong}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6">
        <p className="font-medium text-slate-700">Chưa tải tài liệu lên được</p>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
          Luồng dự kiến: tải lên → xem trước → chia đoạn → nhúng vào collection
          nháp → kiểm thử → đưa vào phục vụ. Phần nhúng và collection nháp đã có
          trong <code>ingestion/embedder.py</code>; còn thiếu lớp API để màn hình
          này gọi tới.
        </p>
      </div>
    </>
  );
}
