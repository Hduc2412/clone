# -*- coding: utf-8 -*-
"""Phép đột biến: cố ý làm hỏng từng chốt chặn rồi xem bộ đo có đỏ không.

    venv/Scripts/python.exe -m scripts.dot_bien [--chi=<một phần tên>]

## Vì sao bộ này tồn tại

Một bộ đo không đỏ khi mã sai thì nó không đo gì cả — nó chỉ tạo ra cảm giác an
toàn. Trong dự án này **bộ đo sai trước khi mã sai** đã xảy ra hơn mười lần:

- Ca kiểm thử viết `assertEqual(ra["source"], qa.NGUON_KHONG_GOI_DUOC)`, tức so
  hằng số với chính nó. Đổi hằng số thành `"khong_biet"` thì ca vẫn xanh.
- Bộ chấm Agent mới kiểm **tên trường**, nên đổi giá trị thành "99 năm" hay
  "Osaka" thay "Tokyo" vẫn báo đạt.
- Bộ E2E HTTP chỉ kiểm những thứ đúng với mọi hồ sơ, nên một máy chủ trả **cùng
  một đơn đạt cho mọi hồ sơ** vẫn làm cả năm ca báo đạt.

Cả ba đều do chủ đồ án hoặc chính phép đột biến này tìm ra, không phải do đọc mã.

## Cách đọc kết quả

`BẮT ĐƯỢC` là tốt: bộ đo đã đỏ đúng lúc mã sai. `*** LỌT ***` nghĩa là chốt chặn
ấy **không có ai canh** — sửa nó đi mà không ai biết.

Mỗi lượt có một lần chạy **đối chứng** trước: nếu bộ đo đã đỏ từ đầu thì mọi kết
luận sau đó vô nghĩa, nên script dừng ngay.

## Ba loại mục tiêu

| Mục tiêu | Chạy gì | Cần máy chủ |
|---|---|:-:|
| `tests.*` | một module `unittest` | không |
| `xuyen_suot` | `scripts.nghiem_thu_xuyen_suot` | không |
| `e2e`, `hanh_trinh` | bộ HTTP, trên **máy chủ riêng dựng cho từng đột biến** | có |

Máy chủ không tự nạp lại mã nguồn, nên đo đột biến qua HTTP bắt buộc phải khởi
động tiến trình mới mỗi lần. Chậm, nhưng ba lỗi nặng nhất của tuần này nằm đúng ở
tầng mà bộ đo trong tiến trình không đi qua.
"""
import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PY = r"venv\Scripts\python.exe"

#: (tên, file, chuỗi cũ, chuỗi mới, các bộ đo phải đỏ)
#:
#: Chuỗi cũ phải xuất hiện **đúng một lần có nghĩa** trong file; script chỉ thay
#: lần đầu. Không tìm thấy thì in `BỎ QUA` — và một dòng BỎ QUA cũng là lỗi cần
#: sửa, vì nó nghĩa là đột biến này không còn đo gì.
DOT_BIEN = [
    (
        "bỏ lọc outcome trong _diem_manh",
        "app/agent/mo_dau.py",
        '        and d.get("outcome") not in explain.NON_REASONS\n',
        "",
        ["tests.test_agent_tu_van", "xuyen_suot"],
    ),
    (
        "xep_hang_duoc nới thành 'luôn đúng'",
        "app/matching/engine.py",
        'return any(row.outcome != "unknown" for row in soft_rows)',
        "return True",
        ["xuyen_suot"],
    ),
    (
        "bộ lọc tiếng Nhật luôn ĐẠT",
        "app/matching/engine.py",
        '    required_japanese = requirements.get("japanese_required")',
        "    required_japanese = None",
        ["xuyen_suot"],
    ),
    (
        "CHUA_RO bị coi là KHONG_DAT (loại oan hồ sơ khuyết)",
        "app/matching/engine.py",
        'CHUA_RO = "CHUA_RO"',
        'CHUA_RO = "KHONG_DAT"',
        ["xuyen_suot"],
    ),
    (
        "match_orders mất tính tất định",
        "app/matching/engine.py",
        "key=lambda item: (-item.score, item.deadline, item.code)",
        "key=lambda item: 0",
        ["xuyen_suot"],
    ),
    (
        "lộ trình học luôn rỗng",
        "app/consultation/advice.py",
        "lo_trinh = learning_path.build(courses, level_from=profile_level, level_to=can)",
        "lo_trinh = None",
        ["xuyen_suot"],
    ),
    (
        "bàn giao bỏ phần việc nên làm tiếp",
        "app/agent/ban_giao.py",
        "VIỆC NÊN LÀM TIẾP",
        "XOA",
        ["xuyen_suot", "hanh_trinh"],
    ),
    (
        "bỏ nhánh dự phòng khi mô hình không trả lời",
        "app/agent/orchestrator.py",
        "if van_ban is None:",
        "if False:",
        ["tests.test_agent_tu_van"],
    ),
    (
        "gộp 'hết hạn mức' vào 'bot không biết'",
        "app/advisor/qa.py",
        'NGUON_KHONG_GOI_DUOC = "khong_goi_duoc"',
        'NGUON_KHONG_GOI_DUOC = "khong_biet"',
        ["tests.test_agent_tu_van"],
    ),
    (
        "bàn giao bỏ dấu 'TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC'",
        "app/agent/ban_giao.py",
        "TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC",
        "ghi chú",
        ["tests.test_agent_tu_van"],
    ),
    (
        "mọi đơn đều ĐẠT — bỏ qua bộ lọc cứng",
        "app/matching/engine.py",
        "        eligible = is_eligible(hard_rows)",
        "        eligible = True",
        ["e2e"],
    ),
    (
        "không sinh câu hỏi cho dữ liệu còn thiếu",
        "app/matching/engine.py",
        "            missing_info=collect_missing(hard_rows, soft_rows),",
        "            missing_info=(),",
        ["e2e"],
    ),
    (
        "điểm mềm luôn 0 — nguyện vọng không ảnh hưởng thứ tự",
        "app/matching/engine.py",
        "        score = sum(row.points for row in soft_rows)",
        "        score = 0",
        ["e2e"],
    ),
    (
        "bỏ chốt chặn quanh gan_lich_hen",
        "app/api/support.py",
        '            "Yêu cầu %s: không gắn được lịch %s vào bản ghi. Liên kết vẫn còn ở "',
        '            1 / 0 or "đột biến: ném lại lỗi thay vì ghi log"',
        ["tests.test_agent_tu_van"],
    ),
    (
        "bàn giao: tín hiệu quay về suy từ appointment_code (lỗi 06/10)",
        "app/db/support_requests.py",
        '    return yeu_cau.get("ban_giao_lich") != lich["appointment_code"]',
        '    return not yeu_cau.get("appointment_code")',
        ["tests.test_agent_tu_van"],
    ),
    (
        "bàn giao: không ghi dấu đã dựng với lịch nào",
        "app/db/support_requests.py",
        '        dat["ban_giao_lich"] = appointment_code',
        "        pass",
        ["tests.test_agent_tu_van"],
    ),
    (
        "bàn giao: đường nhận xử lý không đồng bộ lịch",
        "app/api/support.py",
        "    await _dong_bo_lich(document)",
        "    pass  # đột biến",
        ["tests.test_agent_tu_van"],
    ),
    (
        "bấm gửi lại: không trả lịch đã có",
        "app/api/support.py",
        '        return (da_co or {}).get("appointment_code")',
        "        return None",
        ["tests.test_agent_tu_van", "hanh_trinh"],
    ),
    (
        'quyền hồ sơ: bỏ đường đi theo đơn (lỗi 06/10 lần 1 quay lại)',
        'app/services/quyen_ho_so.py',
        '    return bool(ma) and ma in await ma_ho_so_qua_don(email)',
        '    return False',
        ['tests.test_quyen_ho_so', 'hanh_trinh'],
    ),
    (
        'quyền hồ sơ: nới thành ai cũng xem được',
        'app/services/quyen_ho_so.py',
        '    if profile.get("assigned_to") == email:',
        '    if True:',
        ['tests.test_quyen_ho_so', 'hanh_trinh'],
    ),
    (
        'quyền hồ sơ: đơn đã đóng vẫn cho quyền',
        'app/services/quyen_ho_so.py',
        '    don = await list_recruitment_applications(assigned_to=email, active_only=True, limit=TRAN)',
        '    don = await list_recruitment_applications(assigned_to=email, active_only=False, limit=TRAN)',
        ['tests.test_quyen_ho_so'],
    ),
    (
        'quyền hồ sơ: danh sách hồ sơ bỏ phần đang phụ trách qua đơn',
        'app/services/quyen_ho_so.py',
        '        hoac.append({"code": {"$in": ma}})',
        '        pass',
        ['tests.test_quyen_ho_so', 'hanh_trinh'],
    ),
    (
        'nhật ký: ảnh chụp assigned_to lại được dùng để cấp quyền (lỗi 06/10 lần 2)',
        'app/services/quyen_ho_so.py',
        '    ma = log.get("profile_code")',
        '    if log.get("assigned_to") == _email(current_user):\n        return True\n    ma = log.get("profile_code")',
        ['tests.test_quyen_ho_so'],
    ),
    (
        'nhật ký: danh sách bỏ hồ sơ được phân công trực tiếp',
        'app/services/quyen_ho_so.py',
        '    ma = sorted(await ma_ho_so_truc_tiep(email) | await ma_ho_so_qua_don(email))',
        '    ma = sorted(await ma_ho_so_qua_don(email))',
        ['tests.test_quyen_ho_so'],
    ),
    (
        'dọn E2E: lấy cả sổ của database khác',
        'scripts/don_du_lieu_e2e.py',
        '        if d.get("db") != settings.mongodb_db_name:',
        '        if False:',
        ['tests.test_don_du_lieu_e2e'],
    ),
    (
        'dọn E2E: bỏ chốt thời điểm',
        'scripts/don_du_lieu_e2e.py',
        '            if t < moc:',
        '            if False:',
        ['tests.test_don_du_lieu_e2e'],
    ),
    (
        'dọn E2E: bộ đo không ghi danh phiên',
        'scripts/e2e_hanh_trinh.py',
        '    so_phien_e2e.ghi(sid, bo_do="e2e_hanh_trinh", url=goc)',
        '    pass',
        ['tests.test_don_du_lieu_e2e'],
    ),
    (
        'rà diff: lịch liên quan không lấy bản mới nhất',
        'app/db/support_requests.py',
        '        {"support_code": code}, {"_id": 0, "booking_key": 0}, sort=[("created_at", -1)]',
        '        {"support_code": code}, {"_id": 0, "booking_key": 0}',
        ['tests.test_agent_tu_van'],
    ),
    (
        'rà diff: khối đối chiếu hỏng làm mất yêu cầu',
        'app/api/support.py',
        '        return await khoi_doi_chieu.dung_tu_nhat_ky(session_id, job_order_code)',
        '        return await khoi_doi_chieu.dung_tu_nhat_ky(session_id, job_order_code) if True else None\n    finally:\n        pass\n    try:\n        pass',
        ['tests.test_agent_tu_van'],
    ),
    (
        'AdvisorChat: hỏng rồi không bỏ promise — không thử lại được (lỗi gốc 06/10)',
        '../frontend/components/candidate/AdvisorChat.tsx',
        '            if (moDau.current?.hua === hua) moDau.current = null;',
        '            void hua;',
        ["frontend"],
    ),
    (
        'AdvisorChat: không dùng chung lời gọi mở đầu đang chạy',
        '../frontend/components/candidate/AdvisorChat.tsx',
        '        if (moDau.current?.moc !== moc) {',
        '        if (true) {',
        ["frontend"],
    ),
    (
        'AdvisorChat: không hiện nút Thử lại khi nạp hỏng',
        '../frontend/components/candidate/AdvisorChat.tsx',
        '          {nap === "loi" && (',
        '          {false && (',
        ["frontend"],
    ),
    (
        'ConsultationFlow: bước kết quả không vẽ lỗi (đăng ký hỏng im lặng)',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '          {error && (\n            <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700" role="alert">',
        '          {false && (\n            <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700" role="alert">',
        ["frontend"],
    ),
    (
        'ConsultationFlow: đi tiếp với mã phiên rỗng',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '  if (!sessionId) throw new Error(LOI_KHONG_MO_DUOC_PHIEN);',
        '  void LOI_KHONG_MO_DUOC_PHIEN;',
        ["frontend"],
    ),
    (
        'ConsultationFlow: Khai lại từ đầu xóa màn hình trước khi có phiên mới',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '      moi = moPhien(await resetSession());',
        '      moi = await resetSession();',
        ["frontend"],
    ),
    (
        'kiểm thử: không xóa bộ giới hạn giữa các ca',
        'tests/__init__.py',
        '    rate_limiter.clear()\n    return _chay_ca_goc(self, result)',
        '    return _chay_ca_goc(self, result)',
        ['tests.test_doc_lap_gioi_han'],
    ),
    (
        'đổi phiên: 503 vẫn lấy lại phiên cũ (lỗi 06/10 điểm 1)',
        '../frontend/lib/journeySession.ts',
        '  if (!moi) return "";',
        '  if (!moi) return ensureSessionId();',
        ['frontend'],
    ),
    (
        'đổi phiên: nhận lại đúng mã cũ mà coi là phiên mới',
        '../frontend/lib/journeySession.ts',
        'UUID.test(sessionId) && sessionId !== cu) {',
        'UUID.test(sessionId)) {',
        ['frontend'],
    ),
    (
        'đổi phiên: không xóa đơn đã đăng ký (lỗi 06/10 điểm 2)',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '    setRegistrations([]);\n',
        '',
        ['frontend'],
    ),
    (
        'đổi phiên: không xóa thông báo vừa đăng ký',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '    setJustRegistered(null);\n',
        '',
        ['frontend'],
    ),
    (
        'đổi phiên: ô gửi CV không dựng lại theo phiên',
        '../frontend/components/candidate/ConsultationFlow.tsx',
        '          key={sessionId}\n',
        '',
        ['frontend'],
    ),
    (
        'mã thoát: bộ chấm Agent luôn trả 0 (lỗi 06/10 điểm 3)',
        'scripts/nghiem_thu_agent.py',
        '    return ma\n',
        '    return 0\n',
        ['tests.test_ma_thoat_nghiem_thu'],
    ),
    (
        "mã thoát: bộ chốt coi 'chưa đo được' là hỏng",
        'scripts/nghiem_thu_chot.py',
        '    if any(m not in (0, KHONG_DO_DUOC) for m in ma_thoat):',
        '    if any(m != 0 for m in ma_thoat):',
        ['tests.test_ma_thoat_nghiem_thu'],
    ),
    (
        "mã thoát: hành trình coi 'chưa đo được' là đạt",
        'scripts/e2e_hanh_trinh.py',
        '    if khong_do:\n        return KHONG_DO_DUOC',
        '    if False:\n        return KHONG_DO_DUOC',
        ['tests.test_ma_thoat_nghiem_thu'],
    ),
    (
        'mã thoát: lời tư vấn không từ mô hình mà vẫn tính là đã đo',
        'scripts/e2e_hanh_trinh.py',
        '            if ra.get("source") == "khong_goi_duoc":',
        '            if False:',
        ['tests.test_ma_thoat_nghiem_thu'],
    ),
    (
        "gắn liên kết lịch LUÔN thất bại (đo đường khôi phục đầu-cuối)",
        "app/db/support_requests.py",
        '    dat = {"appointment_code": appointment_code, "updated_at": now()}',
        '    raise RuntimeError("đột biến: database chớp một nhịp")',
        ["hanh_trinh"],
    ),
    (
        "đăng ký bỏ chốt chặn confirmed",
        "app/api/registrations.py",
        "    if not payload.confirmed:",
        "    if False:",
        ["hanh_trinh"],
    ),
    (
        "hàng đợi lọc sai nguồn — hồ sơ tự đăng ký không hiện ra",
        "app/db/database.py",
        '    query: dict[str, Any] = {"source": "self_registration"}',
        '    query: dict[str, Any] = {"source": "khong_bao_gio_khop"}',
        ["hanh_trinh"],
    ),
    (
        "nhật ký giới thiệu bỏ đơn bị loại",
        "app/matching/engine.py",
        "    items = ranked + tuple(rejected_items)",
        "    items = ranked",
        ["hanh_trinh"],
    ),
    # --- Tám điểm bắt trên trình duyệt thật 06/10 -----------------------------
    (
        "CV gốc: bỏ header cấm lưu đệm (trình duyệt 06/10, điểm 8)",
        "app/api/documents.py",
        "        headers=KHONG_LUU_DEM,\n",
        "",
        ["tests.test_cv_khong_luu_dem"],
    ),
    (
        "toàn văn CV: bỏ header cấm lưu đệm",
        "app/api/documents.py",
        "    response.headers.update(KHONG_LUU_DEM)\n",
        "",
        ["tests.test_cv_khong_luu_dem"],
    ),
    (
        "nhật ký: đọc thẳng soft_rows của đơn bị loại (điểm 5)",
        "../admin-frontend/app/admin/recommendation-logs/[code]/page.tsx",
        "  const softRows = item.soft_rows ?? [];",
        "  const softRows = item.soft_rows!;",
        ["admin"],
    ),
    (
        "nhật ký: hiện điểm cho cả đơn bị loại",
        "../admin-frontend/app/admin/recommendation-logs/[code]/page.tsx",
        "{item.eligible ? (\n            <>",
        "{true ? (\n            <>",
        ["admin"],
    ),
    (
        "hàng đợi: quản lý không có tab hồ sơ của mọi người (điểm 7)",
        "../admin-frontend/app/admin/queue/page.tsx",
        '            ...(canManage ? [["all", "Đang có người phụ trách"]] : []),\n',
        "",
        ["admin"],
    ),
    (
        "danh sách đang phụ trách: bỏ kiểm quyền quản lý",
        "app/api/registrations.py",
        '    ensure_can_assign(current_user, "Chỉ Admin/Manager xem được hồ sơ của mọi người.")\n',
        "",
        ["tests.test_handover"],
    ),
    (
        "mở đầu sau CV: chống trùng theo chữ như cũ (điểm 3)",
        "app/api/agent.py",
        "    if not await _da_mo_dau(session_id, van_ban, khoa=khoa):",
        "    if not await _da_mo_dau(session_id, van_ban):",
        ["tests.test_mo_dau_theo_tep"],
    ),
    (
        "mở đầu: khai tay bị coi là đọc CV hỏng",
        "app/agent/mo_dau.py",
        "    if not tai_lieu:\n        return KHAI_TAY",
        "    if not tai_lieu:\n        return CV_HONG",
        ["tests.test_mo_dau_theo_tep"],
    ),
    (
        "đề xuất: máy chủ bỏ nhãn tiếng Việt (điểm 1)",
        "app/agent/contract.py",
        '            "value_label": nhan_gia_tri(self.field, self.value),\n',
        "",
        ["tests.test_de_xuat_nhan_va_vung"],
    ),
    (
        "đề xuất: giao diện bỏ qua nhãn, hiện mã máy",
        "../frontend/components/candidate/AdvisorChat.tsx",
        "  if (nhan) return nhan;\n",
        "",
        ["frontend"],
    ),
    (
        "xác nhận tỉnh qua trợ lý không kèm vùng (điểm 2)",
        "app/api/agent.py",
        '            phan.setdefault("preferences", {})["desired_region_group"] = vung',
        "            pass",
        ["tests.test_de_xuat_nhan_va_vung"],
    ),
    (
        "khai lại hỏng: câu báo bảo bấm nút Thử lại không có (điểm 4)",
        "../frontend/components/candidate/ConsultationFlow.tsx",
        "      setError(LOI_KHAI_LAI);",
        "      setError(LOI_KHONG_MO_DUOC_PHIEN);",
        ["frontend"],
    ),
    (
        "hỗ trợ: có bàn giao vẫn nói 'không kèm kết quả đối chiếu' (điểm 6)",
        "../admin-frontend/app/admin/support/page.tsx",
        "                  ) : item.ban_giao ? (",
        "                  ) : false ? (",
        ["admin"],
    ),
    # --- Bảo mật và vận hành, 06/10 tối --------------------------------------
    (
        "phiên đăng nhập: bỏ kiểm token thuộc đúng bản ghi tài khoản",
        "app/auth/security.py",
        '    if payload.get("acc") != dau_tai_khoan(user):',
        "    if False:",
        ["tests.test_phien_tai_khoan_cu"],
    ),
    (
        "hàng đợi hồ sơ: tổng lấy theo số đang trả về (cắt im lặng)",
        "app/api/registrations.py",
        '    return {"items": items, "count": len(items), "total": max(total, len(items))}',
        '    return {"items": items, "count": len(items), "total": len(items)}',
        ["tests.test_hang_doi_du"],
    ),
    (
        "hàng đợi hỗ trợ: tổng lấy theo số đang trả về",
        "app/api/support.py",
        '    return {"items": items, "count": len(items), "total": max(total, len(items))}',
        '    return {"items": items, "count": len(items), "total": len(items)}',
        ["tests.test_hang_doi_du"],
    ),
    (
        "hàng đợi hồ sơ: giao diện không báo khi danh sách bị cắt",
        "../admin-frontend/app/admin/queue/page.tsx",
        "          {tongCho > items.length && (",
        "          {false && (",
        ["admin"],
    ),
    (
        "tổng quan: thẻ 'Hồ sơ chờ nhận' đếm phần đã cắt",
        "../admin-frontend/app/admin/page.tsx",
        "  const chuaAiNhan = Math.max(tongCho, queue.filter((r) => !r.assigned_to).length);",
        "  const chuaAiNhan = queue.filter((r) => !r.assigned_to).length;",
        ["admin"],
    ),
    # --- Trợ lý tư vấn, 07/10 -------------------------------------------------
    (
        "nhật ký gần nhất lấy cả nhật ký một đơn (lỗi đo 07/10, 5 hồ sơ)",
        "app/db/recommendation_logs.py",
        '        {"profile_code": profile_code, **dieu_kien_ca_danh_muc()},',
        '        {"profile_code": profile_code},',
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "từ chối: dò 'chưa có thông tin' ở bất kỳ đâu như bản cũ",
        "app/advisor/qa.py",
        "    return _TU_CHOI_TRON.match(cau.strip()) is not None",
        '    return "chưa có thông tin" in cau.lower() and len(cau) < 200',
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "hậu kiểm: bỏ chốt tự nhận đã làm thay khách",
        "app/advisor/qa.py",
        "    if (khop := _TU_NHAN_DA_LAM.search(sach)) is not None:",
        "    if (khop := None) is not None:",
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "hậu kiểm: bỏ chốt mã đơn/mã khóa bịa",
        "app/advisor/qa.py",
        "    if ma_la:\n        return f\"nhắc tới mã",
        "    if False:\n        return f\"nhắc tới mã",
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "phòng theo đơn: câu khách vừa hỏi không vào khối cho phép",
        "app/advisor/qa.py",
        "dieu_kien_nen, so_khach_vua_noi(cau_hoi))",
        "dieu_kien_nen)",
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "phòng theo đơn: mô hình lỗi thì chỉ còn 'đang bận'",
        "app/api/consultation_room.py",
        "        cau = du_phong.theo_don(ket_qua, log_ca_danh_muc=log_ca_danh_muc)",
        "        pass",
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "phòng theo đơn: không đưa đơn khác vào ngữ cảnh",
        "app/api/consultation_room.py",
        "        don_khac=don_khac,\n",
        "",
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "đơn khác: đối chiếu cả danh mục cả khi hồ sơ chưa xác nhận",
        "app/services/matching_service.py",
        "    if profile.get(\"status\") != profiles.STATUS_CONFIRMED:\n        return None\n    log, _ = await run_matching(profile, trigger=trigger)",
        "    log, _ = await run_matching(profile, trigger=trigger)",
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "đơn khác: in điểm cả khi chưa xếp hạng được",
        "app/consultation/khoi_mo_rong.py",
        "        if co_hang and _xep_hang_duoc(r):",
        "        if True:",
        ["tests.test_tu_van_mo_rong"],
    ),
    (
        "hậu kiểm: bỏ chốt khóa học không có trong danh mục (khóa thật)",
        "app/advisor/qa.py",
        "    if (khoa := _khoa_khong_co_trong_danh_muc(sach, khoi_cho_phep)) is not None:",
        "    if (khoa := None) is not None:",
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "hậu kiểm: bỏ chốt đảo quan hệ hai khoản tiền (tiền thật)",
        "app/advisor/qa.py",
        "    if (dao := _dao_quan_he_tien(sach)) is not None:",
        "    if (dao := None) is not None:",
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "hậu kiểm: chiều bao hàm tiền bị đảo ngược trong chốt (tiền thật)",
        "app/advisor/qa.py",
        "                bao, phan = (a, b) if bao_truoc else (b, a)",
        "                bao, phan = (b, a) if bao_truoc else (a, b)",
        ["tests.test_hau_kiem_co_nhan"],
    ),
    (
        "hỗ trợ: tư vấn viên chuyển được yêu cầu (bỏ kiểm quyền quản lý)",
        "app/api/support.py",
        '    ensure_can_assign(current_user, "Chỉ Admin/Manager được chuyển người xử lý.")\n',
        "",
        ["tests.test_ho_tro_chuyen_tra"],
    ),
    (
        "hỗ trợ: người ngoài trả được yêu cầu về hàng đợi",
        "app/api/support.py",
        "    if giu != current_user[\"email\"] and not is_privileged(current_user):\n        raise HTTPException(status_code=403, detail=f\"Yêu cầu này do {giu} đang xử lý.\")\n\n    document = await store.tra_ve_hang_doi(",
        "    document = await store.tra_ve_hang_doi(",
        ["tests.test_ho_tro_chuyen_tra"],
    ),
    (
        "hỗ trợ: chuyển không khóa theo người đang giữ",
        "app/db/support_requests.py",
        '        {"code": code, "assigned_to": tu, "status": STATUS_DANG_XU_LY},\n        {\n            "$set": {"assigned_to": den,',
        '        {"code": code},\n        {\n            "$set": {"assigned_to": den,',
        ["tests.test_ho_tro_chuyen_tra"],
    ),
    (
        "hỗ trợ: giao diện không có ô chuyển cho quản lý",
        "../admin-frontend/app/admin/support/page.tsx",
        '                  {item.assigned_to && item.status === "dang_xu_ly" && laQuanLy && (',
        "                  {false && (",
        ["admin"],
    ),
    (
        "Agent: dấu hiệu ngoài phạm vi lọt ra màn hình",
        "app/advisor/qa.py",
        "    if DAU_NGOAI_PHAM_VI in sach:\n        con_lai",
        "    if False:\n        con_lai",
        ["tests.test_tu_van_mo_rong", "tests.test_hau_kiem_co_nhan"],
    ),
    (
        "E2E: không trả hồ sơ về hàng đợi trước khi xóa tài khoản tạm",
        "scripts/e2e_hanh_trinh.py",
        "            hs, ht = asyncio.run(_tra_ve_hang_doi(tu_tao, so))",
        "            hs, ht = 0, 0",
        ["tests.test_e2e_tra_ve_hang_doi"],
    ),
    # --- Bảng đối chiếu ✓ và cửa xác nhận hồ sơ (08/10) ---
    (
        "bảng ✓: tiêu chí chưa rõ cũng hiện dấu ✓ (máy tính)",
        "../frontend/components/candidate/BangDoiChieu.tsx",
        '<td className="py-2.5 text-center">\n                  <DauTich dat={row.result === "DAT"} />',
        '<td className="py-2.5 text-center">\n                  <DauTich dat={row.result !== "KHONG_DAT"} />',
        ["frontend"],
    ),
    (
        "bảng ✓: thẻ điện thoại lệch quy tắc với bảng máy tính",
        "../frontend/components/candidate/BangDoiChieu.tsx",
        '<span className="w-5 shrink-0 text-center">\n                  <DauTich dat={row.result === "DAT"} />',
        '<span className="w-5 shrink-0 text-center">\n                  <DauTich dat={row.result !== "KHONG_DAT"} />',
        ["frontend"],
    ),
    (
        "bảng ✓: thiếu thông tin mà không ghi 'Chưa cung cấp'",
        "../frontend/components/candidate/BangDoiChieu.tsx",
        "  if (row.missing_field || !row.candidate_text?.trim()) return CHUA_CUNG_CAP;",
        "  if (false) return CHUA_CUNG_CAP;",
        ["frontend"],
    ),
    (
        "bảng ✓: đơn trượt điều kiện bắt buộc vẫn hiện điểm nguyện vọng",
        "../frontend/components/candidate/BangDoiChieu.tsx",
        "        {!eligible ? (",
        "        {false ? (",
        ["frontend"],
    ),
    (
        "cửa xác nhận: hồ sơ chưa xác nhận vẫn hiện bảng và kết luận",
        "../frontend/components/candidate/OrderAdvicePanel.tsx",
        "  if (!advice.profile_confirmed) {",
        "  if (false) {",
        ["frontend"],
    ),
    (
        "cửa xác nhận: trợ lý nhận kết quả đối chiếu của hồ sơ chưa xác nhận",
        "app/api/consultation_room.py",
        "            khoi_doi_chieu = KHOI_CHUA_XAC_NHAN",
        "            pass",
        ["tests.test_bang_doi_chieu"],
    ),
    (
        "bảng ✓: đơn trượt chỉ còn dòng không đạt (nhật ký rút gọn)",
        "app/services/matching_service.py",
        '    if row.get("eligible") or not row.get("hard_rows_passed"):',
        "    if True:",
        ["tests.test_bang_doi_chieu"],
    ),
    # --- Quyền, xác minh, cửa xác nhận, ngữ cảnh (08/10, đợt 2) ---
    (
        "hỗ trợ: hàng đợi trả nguyên bản ghi cho consultant",
        "app/api/support.py",
        "            ban_toi_thieu.ho_tro(d)\n",
        "            d\n",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "hỗ trợ: chi tiết không kiểm người đang giữ",
        "app/api/support.py",
        "    if not _duoc_doc_day_du(document, current_user):\n        # Chưa ai nhận",
        "    if False:\n        # Chưa ai nhận",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "hỗ trợ: ?status=dang_xu_ly trả việc của mọi người",
        "app/api/support.py",
        "            status=status, kind=kind, assigned_to=current_user[\"email\"], limit=limit",
        "            status=status, kind=kind, limit=limit",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "đăng ký: consultant đọc phiếu hồ sơ chưa ai nhận",
        "app/api/registrations.py",
        "    if not application.get(\"assigned_to\"):\n        raise HTTPException(",
        "    if False:\n        raise HTTPException(",
        ["tests.test_quyen_va_xac_minh", "tests.test_registrations"],
    ),
    (
        "hội thoại: chi tiết không kiểm quyền",
        "app/api/management.py",
        "    if duoc_xem is not None and session_id not in duoc_xem:",
        "    if False:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "tạo khách: consultant giao được cho người khác",
        "app/api/management.py",
        "        if xin_giao and xin_giao != cua_minh:",
        "        if False:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "xác minh: khách sửa ô nhân viên đã ghi bị lờ đi im lặng",
        "app/db/candidate_profiles.py",
        "        if o.get(\"source\") != \"staff\" or muc_gui >= SOURCE_PRIORITY[\"staff\"]:",
        "        if True:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "xác minh: nhãn cũ không vào lịch sử khi nhân viên đổi giá trị",
        "app/db/candidate_profiles.py",
        "        if cu.get(\"verification\") and (merged_fields.get(key) or {}).get(\"value\") != cu.get(\"value\"):",
        "        if False:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "tiếng Nhật: hoàn thành chương trình bị ghi thành trình độ đối chiếu",
        "app/api/profiles.py",
        "    fields = profile.get(\"fields\") or {}\n    tu_van = None\n    hoc_tap = {",
        "    fields = dict(profile.get(\"fields\") or {})\n    if ket_qua:\n        fields[\"japanese_level\"] = {\"value\": ket_qua, \"source\": \"staff\", \"verification\": \"center\"}\n    tu_van = None\n    hoc_tap = {",
        ["tests.test_quyen_va_xac_minh"],
    ),
    # --- Bản 2 (08/10 tối) ---
    (
        "hội thoại: nối lại qua số điện thoại (mọi phiên chat)",
        "app/services/quyen_hoi_thoai.py",
        "    phien: set[str] = set()\n",
        "    phien: set[str] = {r[\"session_id\"] async for r in db.sessions.find({}, {\"_id\": 0, \"session_id\": 1})}\n",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "hỗ trợ: không cần khách đồng ý bàn giao vẫn mở hồ sơ",
        "app/services/quyen_ho_so.py",
        "if d.get(\"dong_y_ban_giao\") is True and d.get(\"session_id\")",
        "if d.get(\"session_id\")",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "hỗ trợ: quyền đọc từ yêu cầu thành quyền SỬA hồ sơ",
        "app/services/quyen_ho_so.py",
        "    return chi_doc and bool(profile.get(\"session_id\"))",
        "    return bool(profile.get(\"session_id\"))",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "xác minh: khách đè được ô ĐÃ xác minh có căn cứ",
        "app/db/candidate_profiles.py",
        "                and not da_xac_minh_co_can_cu(current)\n",
        "\n",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "xác minh: ô nhân viên nhập không căn cứ vẫn bị khóa",
        "app/db/candidate_profiles.py",
        "            if incoming_priority < current_priority and not khach_sua_loi_khai:",
        "            if incoming_priority < current_priority:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "internal_note: consultant đọc được",
        "app/db/job_orders.py",
        "CHI_QUAN_LY_DOC = (\"internal_note\",)",
        "CHI_QUAN_LY_DOC = ()",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "thời gian chờ: trợ lý hồ sơ ghi cứng, không theo cấu hình",
        "app/agent/orchestrator.py",
        "    return settings.advisor_agent_timeout_seconds",
        "    return 25.0",
        ["tests.test_agent_tu_van"],
    ),
    (
        "cửa xác nhận: API tư vấn theo đơn trả kết quả cho hồ sơ chưa xác nhận",
        "app/api/consultation_room.py",
        "    if profile.get(\"status\") != profiles.STATUS_CONFIRMED:\n        raise HTTPException(status_code=409, detail=profiles.loi_chua_xac_nhan())",
        "    if False:\n        raise HTTPException(status_code=409, detail=profiles.loi_chua_xac_nhan())",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "lý do chi tiết: dùng nhật ký của phiên bản hồ sơ cũ",
        "app/api/matching.py",
        "    if log.get(\"profile_version\") != profile.get(\"version\", 1):",
        "    if False:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "chi phí: điểm trung lập in như điểm mạnh trong khối gửi AI",
        "app/matching/explain.py",
        "    if row.outcome in NON_REASONS and row.points > 0:",
        "    if False:",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "chi phí: gộp 'đơn chưa công bố' với 'khách chưa nêu'",
        "../frontend/components/candidate/BangDoiChieu.tsx",
        "    lyDo.includes(DON_CHUA_CONG_BO) && `đơn chưa công bố ${PHIA_DON[key] ?? muc}`,",
        "    lyDo.includes(DON_CHUA_CONG_BO) && `chưa rõ nguyện vọng`,",
        ["frontend"],
    ),
    (
        "ngữ cảnh: ghi chú nội bộ của hồ sơ đăng ký lọt vào khối tiến độ",
        "app/consultation/tien_do.py",
        "            \"chang\": CHANG_CUA_TRANG_THAI.get(d.get(\"status\") or \"\", \"Đang xử lý\"),",
        "            \"chang\": f\"{d.get('status')} {d.get('note')}\",",
        ["tests.test_quyen_va_xac_minh"],
    ),
    (
        "ngân sách mô hình: gặp 429 mà vẫn gọi tiếp",
        "scripts/ngan_sach_mo_hinh.py",
        '                ngan_sach.ly_do_dung = "gặp 429"',
        "                pass",
        ["tests.test_ngan_sach_mo_hinh"],
    ),
    # --- Bộ chấm câu trả lời mô hình thật (09/10) ---
    (
        "bộ chấm: bỏ xét phủ định ở ca hoàn thành chương trình",
        "scripts/danh_gia_tu_van_that.py",
        "            if not re.search(r\"(chưa|không)[^.]{0,60}$\", kq_cau[: khop.start()], re.IGNORECASE):\n",
        "            if True:\n",
        ["tests.test_bo_cham_tu_van"],
    ),
    (
        "bộ chấm: không còn bắt câu khẳng định đủ điều kiện",
        "scripts/danh_gia_tu_van_that.py",
        "        for khop in re.finditer(r\"đủ điều kiện tiếng nhật|",
        "        for khop in re.finditer(r\"KHONG_BAO_GIO_KHOP|",
        ["tests.test_bo_cham_tu_van"],
    ),
    # --- Nhập Excel: cột ghi chú tư vấn viên (12/10) ---
    (
        "nhập Excel: file thiếu cột ghi chú vẫn xóa ghi chú đang lưu",
        "app/services/job_order_import.py",
        "            if result.action == \"update\" or key in GIU_NEU_THIEU_COT:\n                _bo_duong_dan(result.data, duong)\n",
        "            pass\n",
        ["tests.test_job_order_import"],
    ),
    (
        "nhập Excel: cập nhật bằng file thiếu cột vẫn xóa các trường khác",
        "app/services/job_order_import.py",
        "            if result.action == \"update\" or key in GIU_NEU_THIEU_COT:",
        "            if key in GIU_NEU_THIEU_COT:",
        ["tests.test_job_order_import"],
    ),
    (
        "nhập Excel: quá 500 dòng lại bị cắt im lặng",
        "app/services/job_order_import.py",
        "        if len(tat_ca) > MAX_ROWS:\n            workbook.close()\n            raise ValueError(",
        "        if len(tat_ca) > MAX_ROWS:\n            tat_ca.pop()\n            break\n            raise ValueError(",
        ["tests.test_job_order_import"],
    ),
    # --- Khối đơn cho mô hình: nhãn yêu cầu giới tính (12/10) ---
    (
        "khối đơn: đọc nhầm bảng giới tính của ứng viên, lọt mã khong_yeu_cau",
        "app/consultation/order_context.py",
        "catalog.GENDER_PREF_LABELS.get(gioi, gioi)}\"\n        if gioi and gioi != \"khong_yeu_cau\"",
        "catalog.GENDER_LABELS.get(gioi, gioi)}\"\n        if gioi",
        ["tests.test_consultation_eligibility"],
    ),
    # --- Chỉ tiêu, đơn quá hạn, tình trạng đơn cho khung chat (12/10) ---
    (
        "chỉ tiêu: trừ ngay khi đủ điều kiện sơ bộ thay vì khi trúng tuyển",
        "app/services/chi_tieu.py",
        'TINH = "passed"',
        'TINH = "eligible"',
        ["tests.test_chi_tieu"],
    ),
    (
        "chỉ tiêu: bản công khai lộ số đã tuyển thô",
        "app/db/job_orders.py",
        '    da = int(ra.pop("hired_count", 0) or 0)',
        '    da = int(ra.get("hired_count", 0) or 0)',
        ["tests.test_chi_tieu"],
    ),
    (
        "đơn quá hạn: quét lại sinh thông báo trùng",
        "app/services/het_han_don.py",
        "        if da_co:\n            continue\n",
        "        if False:\n            continue\n",
        ["tests.test_chi_tieu"],
    ),
    (
        "thông báo về đơn: consultant tắt được",
        "app/api/appointments.py",
        '        if current_user.get("role") not in ("admin", "manager"):',
        '        if False:',
        ["tests.test_chi_tieu"],
    ),
]

#: Bộ đo nào phải xanh ở lần chạy đối chứng. Mọi mục tiêu xuất hiện trong
#: `DOT_BIEN` PHẢI có ở đây — thiếu thì đột biến của nó được tính "bắt được" mà
#: không có lần đối chứng xanh nào trước đó. Lỗ này có thật ngày 06/10 với
#: `tests.test_doc_lap_gioi_han`; `main()` nay tự kiểm và dừng nếu thiếu.
DOI_CHUNG = (
    "frontend", "admin", "tests.test_agent_tu_van", "tests.test_quyen_ho_so",
    "tests.test_don_du_lieu_e2e", "tests.test_doc_lap_gioi_han", "tests.test_ma_thoat_nghiem_thu",
    "tests.test_cv_khong_luu_dem", "tests.test_handover", "tests.test_mo_dau_theo_tep",
    "tests.test_de_xuat_nhan_va_vung", "tests.test_phien_tai_khoan_cu", "tests.test_hang_doi_du",
    "tests.test_e2e_tra_ve_hang_doi", "tests.test_tu_van_mo_rong", "tests.test_hau_kiem_co_nhan",
    "tests.test_ho_tro_chuyen_tra", "tests.test_bang_doi_chieu", "tests.test_ngan_sach_mo_hinh", "tests.test_quyen_va_xac_minh",
    "tests.test_registrations", "tests.test_bo_cham_tu_van", "tests.test_job_order_import", "tests.test_consultation_eligibility", "tests.test_chi_tieu",
    "xuyen_suot", "e2e", "hanh_trinh",
)

CONG = {"e2e": 8031, "hanh_trinh": 8032}
MODULE = {"e2e": "scripts.e2e_xuyen_suot", "hanh_trinh": "scripts.e2e_hanh_trinh"}

#: `hanh_trinh` chạy ở chế độ khai tay: **không** gọi mô hình.
#:
#: Không đột biến nào ở đây nhắm bước đọc CV, nên để mỗi lượt đốt một lượt hạn
#: mức là trả giá cho thứ không đo. Ngày 06/10 một lượt đột biến đầy đủ đã chạy
#: bộ hành trình sáu lần ở chế độ đọc CV thật: tốn sáu lượt, lưu thêm sáu bản sao
#: CV mẫu vào `storage/cv`, và lượt chạy kế tiếp nhận 429.
THAM_SO = {"hanh_trinh": ("--khai-tay",)}


#: Mã thoát "không đo được" của các bộ HTTP — xem `e2e_hanh_trinh.KHONG_DO_DUOC`.
KHONG_DO_DUOC = 3


def _qua_may_chu_rieng(cong: int, module: str, *tham_so: str) -> bool | None:
    """Dựng một máy chủ riêng, chạy bộ đo HTTP trên đó, rồi dọn.

    Trả `True` (xanh), `False` (đỏ), hoặc `None` (**không đo được** — bước cần
    mô hình không chạy được). Phân biệt cái thứ ba là bắt buộc: không có nó thì
    một lần Gemini báo 503 bị đếm thành một đột biến bị bắt, và con số "19/19"
    nói nhiều hơn điều nó thật sự đo được.
    """
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "main:app", "--port", str(cong), "--log-level", "error"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(120):
            with socket.socket() as so:
                if so.connect_ex(("127.0.0.1", cong)) == 0:
                    break
            time.sleep(0.25)
        else:
            print("      (máy chủ đột biến không lên — không đo được)")
            return None
        ra = subprocess.run(
            [PY, "-m", module, "--url", f"http://127.0.0.1:{cong}", *tham_so],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if ra.returncode == KHONG_DO_DUOC:
            return None
        return ra.returncode == 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            proc.kill()


def _node() -> str:
    import shutil

    # Gạch xuôi: Windows nhận được, và không có ký tự thoát nào để hỏng.
    return os.environ.get("NODE_EXE") or shutil.which("node") or "F:/NodeJS/node.exe"


def chay(muc_tieu: str) -> bool | None:
    if muc_tieu in ("frontend", "admin"):
        # Bộ kiểm thử website / quản trị: TypeScript dịch rồi chạy trong `vm`, không
        # cần trình duyệt. Chạy từ thư mục của app vì mẫu đường dẫn là tương đối.
        thu_muc = "frontend" if muc_tieu == "frontend" else "admin-frontend"
        ra = subprocess.run(
            [_node(), "--test", "tests/**/*.test.cjs"],
            cwd=str(Path(__file__).resolve().parents[2] / thu_muc),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return ra.returncode == 0
    if muc_tieu in MODULE:
        return _qua_may_chu_rieng(
            CONG[muc_tieu], MODULE[muc_tieu], *THAM_SO.get(muc_tieu, ())
        )
    if muc_tieu == "xuyen_suot":
        ra = subprocess.run(
            [PY, "-m", "scripts.nghiem_thu_xuyen_suot"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    else:
        ra = subprocess.run(
            [PY, "-m", "unittest", muc_tieu],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    return ra.returncode == 0


def main() -> int:
    chi = ""
    khong_ghi_db = False
    for arg in sys.argv[1:]:
        if arg.startswith("--chi="):
            chi = arg.split("=", 1)[1]
        # Bỏ các đột biến đo bằng bộ HTTP: chúng dựng máy chủ thật và GHI vào database
        # (phiên, hồ sơ, lịch hẹn của bộ E2E). Dùng khi chưa có kho kiểm thử riêng.
        if arg == "--khong-ghi-db":
            khong_ghi_db = True

    bo = [d for d in DOT_BIEN if not chi or chi.lower() in d[0].lower()]
    if khong_ghi_db:
        bo = [d for d in bo if not set(d[4]) & set(MODULE)]
        print(f"--khong-ghi-db: bỏ các đột biến đo qua HTTP; còn {len(bo)} đột biến.")
    can = sorted({m for d in bo for m in d[4]})

    thieu = sorted(set(can) - set(DOI_CHUNG))
    if thieu:
        print(f"DỪNG: mục tiêu {thieu} không có trong DOI_CHUNG — đột biến của chúng sẽ không có đối chứng.")
        return 1

    print("=== Đối chứng: chưa đột biến, mọi bộ đo phải XANH ===")
    ok = True
    for m in [x for x in DOI_CHUNG if x in can]:
        x = chay(m)
        print(f"  {'xanh' if x else ('KHÔNG ĐO ĐƯỢC' if x is None else 'ĐỎ  ')}  {m}")
        ok = ok and bool(x)
    if not ok:
        print("Đối chứng đã đỏ — dừng, vì mọi kết luận sau đó vô nghĩa.")
        return 1

    print()
    bat_duoc = 0
    bo_qua = 0
    khong_do_duoc = 0
    for ten, f, cu, moi, muc_tieus in bo:
        # Đọc và ghi bằng BYTE, hoàn nguyên đúng từng byte và cả giờ sửa đổi.
        #
        # Bản trước ghi bằng chế độ văn bản: trên Windows nó tự đổi `\n` thành
        # `\r\n`, nên mỗi lần "hoàn nguyên" lại viết một file LF thành CRLF. Và
        # nó để giờ sửa đổi của file nhảy lên, trong khi nội dung y nguyên — ngày
        # 06/10 chốt "máy chủ chạy mã cũ" của `nghiem_thu_chot` báo động oan vì
        # đúng chuyện này: `database.py` mới hơn máy chủ mà không ai sửa gì.
        duong = Path(f)
        goc_byte = duong.read_bytes()
        gio_goc = duong.stat()
        goc = goc_byte.decode("utf-8").replace("\r\n", "\n")
        if cu not in goc or cu == moi:
            print(f"  BỎ QUA  {ten} — không thay được gì trong {f}")
            bo_qua += 1
            continue
        duong.write_bytes(goc.replace(cu, moi, 1).encode("utf-8"))
        try:
            kq = {m: chay(m) for m in muc_tieus}
        finally:
            # Hoàn nguyên trong `finally`: Ctrl-C giữa lượt chạy mà để nguyên
            # đột biến trong cây mã là cách chắc chắn để mất một buổi đi tìm
            # một lỗi mình tự tạo ra.
            duong.write_bytes(goc_byte)
            os.utime(duong, ns=(gio_goc.st_atime_ns, gio_goc.st_mtime_ns))
        do = [m for m, x in kq.items() if x is False]
        khong_do = [m for m, x in kq.items() if x is None]
        if do:
            bat_duoc += 1
            print(f"  BẮT ĐƯỢC  {ten}")
            print(f"            bởi: {', '.join(do)}")
        elif khong_do:
            # Không tính là bắt được, cũng không tính là lọt. Chạy lại khi mô
            # hình trả lời được — không có cách nào biết kết quả trước lúc ấy.
            khong_do_duoc += 1
            print(f"  KHÔNG ĐO ĐƯỢC  {ten}")
            print(f"            {', '.join(khong_do)}: bước cần mô hình không chạy được")
        else:
            print(f"  *** LỌT *** {ten}")
            print(f"            {', '.join(muc_tieus)} vẫn xanh dù mã đã sai")

    do_duoc = len(bo) - bo_qua - khong_do_duoc
    print()
    ghi_chu = []
    if bo_qua:
        ghi_chu.append(f"{bo_qua} bỏ qua")
    if khong_do_duoc:
        ghi_chu.append(f"{khong_do_duoc} không đo được — chạy lại sau")
    print(f"{bat_duoc}/{do_duoc} đột biến bị bắt" + (f" ({', '.join(ghi_chu)})" if ghi_chu else ""))
    return 0 if bat_duoc == do_duoc and not bo_qua and not khong_do_duoc else 1


if __name__ == "__main__":
    raise SystemExit(main())
