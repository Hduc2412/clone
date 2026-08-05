import { PageHeader } from "@/components/admin/AdminUI";

const topics = [
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
        description="Theo dõi bộ dữ liệu đã nghiệm thu. Upload và publish tài liệu sẽ được phát triển sau Authentication."
      />

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["32", "Bài viết đã lập chỉ mục", "Đủ nội dung từ ảnh"],
          ["10", "Nhóm chủ đề", "Taxonomy đang sử dụng"],
          ["0", "Nguồn thiếu ảnh", "Kiểm tra nghiêm ngặt đạt"],
        ].map(([value, label, note]) => (
          <article
            key={label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-3xl font-semibold tracking-tight">{value}</p>
            <p className="mt-2 text-sm font-medium text-slate-700">{label}</p>
            <p className="mt-1 text-xs text-slate-400">{note}</p>
          </article>
        ))}
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold">Phân bố chủ đề</h3>
          <p className="mt-1 text-xs text-slate-400">
            Version đang phục vụ: xkld_knowledge_v20260730
          </p>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map(([topic, count]) => (
            <div
              key={topic}
              className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3"
            >
              <span className="text-sm text-slate-600">{topic}</span>
              <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm">
                {count}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6">
        <p className="font-medium text-slate-700">Module upload đang khóa</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          Giai đoạn tiếp theo sẽ hỗ trợ PDF, Word, FAQ và hình ảnh theo luồng:
          upload → xem trước → chunk → embedding → staging → kiểm thử → publish.
        </p>
      </div>
    </>
  );
}
