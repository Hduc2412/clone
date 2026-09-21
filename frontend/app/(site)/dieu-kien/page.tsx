import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import {
  Button,
  Card,
  Section,
  SectionHeading,
} from "@/components/ui/primitives";
import { CONDITIONS } from "@/content/pages";

export const metadata: Metadata = {
  title: "Điều kiện tham gia",
  description:
    "Điều kiện về độ tuổi, bằng cấp, tiếng Nhật, sức khỏe và lý lịch khi tham gia chương trình điều dưỡng, hộ lý Nhật Bản.",
};

export default function ConditionsPage() {
  return (
    <>
      <PageHero
        eyebrow="Điều kiện"
        title="Điều kiện tham gia chương trình"
        lead="Đây là điều kiện chung. Mỗi đơn hàng có yêu cầu riêng và thường chặt hơn ở một vài tiêu chí, nên cách chắc chắn nhất là đối chiếu hồ sơ của bạn với từng đơn."
      >
        <div className="flex flex-wrap gap-3">
          <Button href="/tu-van">Đối chiếu hồ sơ của tôi</Button>
          <Button href="/don-hang" variant="outline">
            Xem điều kiện từng đơn
          </Button>
        </div>
      </PageHero>

      <Section>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3.5">Tiêu chí</th>
                  <th className="px-5 py-3.5">Yêu cầu</th>
                  <th className="px-5 py-3.5">Ghi chú</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {CONDITIONS.map((condition) => (
                  <tr key={condition.criterion}>
                    <td className="px-5 py-4 font-medium text-slate-900">
                      {condition.criterion}
                    </td>
                    <td className="px-5 py-4 text-slate-700">
                      {condition.requirement}
                    </td>
                    <td className="px-5 py-4 leading-6 text-slate-500">
                      {condition.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <div className="grid gap-8 lg:grid-cols-2">
            <div>
              <SectionHeading
                eyebrow="Hiểu đúng"
                title="Chưa đạt một tiêu chí không có nghĩa là hết cửa"
              />
              <div className="mt-5 space-y-4 text-base leading-7 text-slate-600">
                <p>
                  Tiếng Nhật là tiêu chí gần như ai cũng chưa đạt lúc mới tìm
                  hiểu, và đó là chuyện bình thường. Trình độ tiếng là điều kiện
                  tại thời điểm nộp hồ sơ vào đơn hàng, không phải lúc đăng ký.
                  Phần lớn học viên học từ đầu tại trung tâm.
                </p>
                <p>
                  Những tiêu chí không đổi được thì nên biết sớm: độ tuổi, bằng
                  cấp chuyên ngành, tình trạng sức khỏe thuộc danh mục loại trừ.
                  Biết sớm để chọn đúng diện chương trình, thay vì học xong mấy
                  tháng mới phát hiện không đủ điều kiện.
                </p>
              </div>
            </div>

            <Card className="p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Hệ thống phân biệt hai chuyện khác nhau
              </h3>
              <dl className="mt-5 space-y-5 text-sm">
                <div className="rounded-xl bg-rose-50 p-4">
                  <dt className="font-semibold text-rose-800">Chưa đạt</dt>
                  <dd className="mt-1 leading-6 text-rose-700">
                    Hồ sơ ghi rõ và không khớp yêu cầu bắt buộc. Ví dụ đơn cần N3
                    mà bạn đang N4. Đơn này bị loại khỏi danh sách giới thiệu.
                  </dd>
                </div>
                <div className="rounded-xl bg-amber-50 p-4">
                  <dt className="font-semibold text-amber-800">Chưa rõ</dt>
                  <dd className="mt-1 leading-6 text-amber-700">
                    Bạn chưa khai mục đó. Hệ thống <strong>không loại</strong> đơn
                    hàng, mà hỏi thêm. Người chưa khai năm sinh không phải là
                    người quá tuổi, chỉ là chưa biết.
                  </dd>
                </div>
              </dl>
            </Card>
          </div>
        </Section>
      </section>
    </>
  );
}
