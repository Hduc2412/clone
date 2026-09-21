import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import {
  Button,
  Card,
  Section,
  SectionHeading,
  Steps,
} from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";

export const metadata: Metadata = {
  title: "Hệ thống đối chiếu hồ sơ",
  description:
    "Hệ thống đọc hồ sơ của bạn, đối chiếu với từng đơn hàng đang tuyển và nói rõ bạn đạt hay chưa đạt ở từng tiêu chí. Không cần tài khoản, không cần chờ giờ hành chính.",
};

/**
 * Trang giới thiệu hệ thống cho ứng viên.
 *
 * Khác `/gioi-thieu` — trang đó nói về công ty. Trang này nói về công cụ: nó làm
 * được gì cho bạn, vì sao kết quả đáng tin, và dữ liệu bạn đưa vào được dùng ra
 * sao.
 *
 * Giọng viết hướng tới người đang lo bị lừa, không phải hội đồng chấm. Nên ở đây
 * không nói "bộ đối chiếu tất định", "ràng buộc R1" hay số ca kiểm thử; nói cùng
 * những điều đó bằng thứ ngôn ngữ mà người đọc kiểm chứng được ngay trên màn
 * hình của họ.
 */

const BA_BUOC = [
  {
    title: "Đưa hồ sơ vào",
    detail:
      "Gửi file CV có sẵn, hoặc điền tay khoảng mười ô. Không cần tạo tài khoản, không cần để lại số điện thoại nếu bạn chưa muốn.",
  },
  {
    title: "Xem lại thứ máy đọc được",
    detail:
      "Máy đọc CV có thể đọc sai. Hệ thống hiện lại từng ô để bạn sửa, và chỉ đem hồ sơ đi đối chiếu sau khi bạn bấm xác nhận.",
  },
  {
    title: "Nhận danh sách đơn kèm lý do",
    detail:
      "Mỗi đơn kèm bảng từng tiêu chí: tiếng Nhật, bằng cấp, tuổi, kinh nghiệm, giới tính, hạn nộp. Đạt hay chưa đạt đều ghi rõ, kèm con số của bạn đặt cạnh yêu cầu của đơn.",
  },
];

const VI_SAO_TIN = [
  {
    title: "Nói rõ vì sao, không chỉ đưa con số",
    detail:
      "Một con số phần trăm không cho bạn biết gì. Ở đây mỗi đơn mở ra được bảng mười một dòng: bảy điều kiện bắt buộc và bốn tiêu chí theo nguyện vọng, mỗi dòng ghi đơn yêu cầu gì và hồ sơ bạn có gì.",
  },
  {
    title: "Điều chưa biết không làm bạn mất đơn",
    detail:
      "Bỏ trống một ô thì hệ thống ghi là “chưa rõ” rồi hỏi lại, chứ không coi như bạn không đạt. Người chưa khai năm sinh không phải là người quá tuổi — đó là hai chuyện khác nhau.",
  },
  {
    title: "Cùng một hồ sơ luôn ra cùng một kết quả",
    detail:
      "Phần chấm điểm do quy tắc viết sẵn tính, không phải do máy đoán. Hỏi lại lần thứ hai, thứ ba vẫn ra đúng danh sách đó, và nhân viên tư vấn mở lại được đúng bảng bạn đã xem.",
  },
  {
    title: "Không hứa thay công ty",
    detail:
      "Hệ thống nói mức độ phù hợp trên giấy tờ, không nói bạn sẽ trúng tuyển. Quyết định cuối vẫn là của nhân viên tư vấn và cơ sở tiếp nhận bên Nhật.",
  },
];

const DU_LIEU = [
  "Hồ sơ bạn khai chỉ dùng để đối chiếu với đơn hàng và để nhân viên tư vấn gọi lại. Không hiển thị công khai ở bất cứ đâu.",
  "Bạn chỉ để lại số điện thoại khi tự bấm đăng ký một đơn cụ thể. Trước bước đó, xem kết quả đối chiếu không cần số của bạn.",
  "File CV gốc lưu lại để nhân viên đối chiếu khi cần, không dùng vào việc gì khác.",
  "Muốn xoá hồ sơ đã khai thì bấm “Khai lại từ đầu” ngay trên trang đối chiếu.",
];

export default function SystemPage() {
  return (
    <>
      <PageHero
        eyebrow="Hệ thống đối chiếu hồ sơ"
        title="Biết mình hợp đơn nào trước khi gọi điện"
        lead="Thay vì hỏi rồi chờ tới giờ hành chính mới có câu trả lời, bạn đưa hồ sơ vào và nhận ngay danh sách đơn phù hợp kèm lý do cho từng tiêu chí."
      >
        <div className="flex flex-wrap gap-3">
          <Button href="/tu-van">Thử ngay, mất hai phút</Button>
          <Button href="/don-hang" variant="outline">
            Xem đơn đang tuyển
          </Button>
        </div>
      </PageHero>

      <Section>
        <SectionHeading
          eyebrow="Cách dùng"
          title="Ba bước"
          lead="Dừng ở bước nào cũng được. Thông tin đã nhập vẫn nằm trên máy của bạn, quay lại là thấy."
        />
        <div className="mt-8 grid gap-8 lg:grid-cols-[1.2fr_1fr]">
          <Steps items={BA_BUOC} />

          <Card className="h-fit p-6">
            <h3 className="text-base font-bold text-slate-900">
              Không có sẵn file CV?
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Điền tay cũng được, và chỉ hai ô là bắt buộc: họ tên và trình độ
              tiếng Nhật. Chưa học tiếng cũng là một câu trả lời hợp lệ — vẫn có
              đơn dành cho bạn.
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Phần lớn người vào bằng điện thoại và không sẵn file trong máy, nên
              lối điền tay được thiết kế để đi trọn được trên màn hình nhỏ.
            </p>
            <div className="mt-6">
              <Button href="/tu-van" className="w-full">
                Điền hồ sơ
              </Button>
            </div>
          </Card>
        </div>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <SectionHeading
            eyebrow="Vì sao đáng tin"
            title="Bốn điều hệ thống này làm khác"
            lead="Bạn kiểm chứng được cả bốn ngay trên màn hình, không phải tin lời ai."
          />
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            {VI_SAO_TIN.map((item) => (
              <Card key={item.title} className="p-6">
                <h3 className="text-base font-semibold text-slate-900">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {item.detail}
                </p>
              </Card>
            ))}
          </div>
        </Section>
      </section>

      <Section>
        <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <SectionHeading
              eyebrow="Dữ liệu của bạn"
              title="Dùng vào việc gì"
              lead="Nói trước để bạn quyết định có đưa hồ sơ vào hay không."
            />
            <ul className="mt-6 space-y-3">
              {DU_LIEU.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <Card className="h-fit p-6">
            <h3 className="text-base font-bold text-slate-900">
              Vẫn muốn nói chuyện với người thật
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Hệ thống trả lời được câu “tôi hợp đơn nào”. Những câu riêng của
              hoàn cảnh bạn — đang vướng hợp đồng cũ, sức khoẻ có vấn đề, gia đình
              chưa đồng ý — thì gọi vẫn nhanh hơn.
            </p>
            <div className="mt-6 space-y-3">
              <Button href={COMPANY.hotlineHref} className="w-full">
                Gọi {COMPANY.hotline}
              </Button>
              <Button href="/lien-he" variant="outline" className="w-full">
                Xem địa chỉ văn phòng
              </Button>
            </div>
            <p className="mt-5 text-xs leading-5 text-slate-500">
              Ngoài giờ hành chính thì mở khung chat ở góc phải màn hình, hoặc để
              lại lịch hẹn để nhân viên gọi lại đúng khung giờ bạn chọn.
            </p>
          </Card>
        </div>
      </Section>
    </>
  );
}
