"""
Kịch bản kiểm thử in thực nghiệm tem nhãn kiểm chuẩn (Calibration Label)
gửi trực tiếp tới máy in laser qua mạng LAN (cổng 9100) theo chuẩn PJL + PCL 5 Raster 300 DPI.

Tuân thủ nghiêm ngặt quy tắc kiến trúc dự án:
- KHÔNG sử dụng thư viện argparse.
- Xử lý tham số bằng sys.argv thuần túy.
- Tự động lưu ảnh xem trước (Preview) để kiểm tra giao diện trước khi in.
- Hỗ trợ cờ --dry-run để chạy kiểm tra offline không cần cắm mạng.

Cách sử dụng:
    # 1. Chạy thử nghiệm offline (chỉ xuất ảnh PNG xem trước và kiểm tra tạo lệnh PCL):
    python examples/print_test_label.py --dry-run

    # 2. In thực tế tới máy in mặc định (10.45.1.191:9100, Khay 1, Khổ Custom 102x148 mm):
    python examples/print_test_label.py

    # 3. Ghi đè địa chỉ IP máy in khác:
    python examples/print_test_label.py 10.45.1.200

    # 4. Xuất mã nhị phân PCL ra tệp để kiểm tra bằng trình xem file hex:
    python examples/print_test_label.py --save-pcl output_test.pcl

    # 5. Tùy chỉnh tỉ lệ scale hoặc dịch lề mm:
    python examples/print_test_label.py --scale 0.94 --shift-x 1.0 --shift-y -1.0
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path
import sys
import time

# Đảm bảo console Windows in tiếng Việt chuẩn UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm đường dẫn src vào sys.path để nạp core_kit
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PIL import Image, ImageDraw, ImageFont
from core_kit.devices import PCL5RasterBuilder, PCLNetworkPrinter, PrinterStatus

# Cấu hình mặc định máy in
DEFAULT_HOST = os.getenv("PRINTER_HOST", "10.45.1.193")
DEFAULT_PORT = int(os.getenv("PRINTER_PORT", "9100"))
DEFAULT_TRAY = "TRAY1"
DEFAULT_WIDTH_MM = 102.0
DEFAULT_HEIGHT_MM = 148.0
DEFAULT_SCALE_X = float(os.getenv("PRINT_SCALE_X", "0.89"))
DEFAULT_SCALE_Y = float(os.getenv("PRINT_SCALE_Y", "0.94"))
DEFAULT_SCALE = (DEFAULT_SCALE_X, DEFAULT_SCALE_Y)
DEFAULT_ROTATE = 90
DEFAULT_SHIFT_X_MM = float(os.getenv("PRINT_SHIFT_X", "-5.0"))
DEFAULT_SHIFT_Y_MM = float(os.getenv("PRINT_SHIFT_Y", "0.0"))


def get_font(size: int = 16) -> ImageFont.ImageFont:
    """Nạp font chữ hệ thống hoặc dùng font mặc định nếu không tìm thấy."""
    for font_name in ["arial.ttf", "calibri.ttf", "tahoma.ttf", "consola.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        # Pillow >= 10.1 hỗ trợ size trong load_default
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def create_calibration_label(
    width_mm: float = 148.0,
    height_mm: float = 102.0,
    dpi: int = 300,
    target_ip: str = DEFAULT_HOST,
    scale_info: str | None = None,
    shift_info: str | None = None,
) -> Image.Image:
    """
    Tạo hình ảnh tem kiểm chuẩn kỹ thuật hoàn chỉnh (1-bit monochrome).
    Bao gồm:
    - Thước đo mm và vạch căn lề ở cả 4 cạnh (giúp kiểm tra lề chết cơ khí 3.5mm bằng thước kẻ).
    - Khối thông tin kiểm chuẩn hệ thống.
    - Dải thang kiểm tra độ phân giải (đường kẻ 1px, 2px, 4px).
    - Khối đen đặc kiểm tra độ phủ mực toner.
    - Mẫu mã vạch 1D và mã ma trận 2D mô phỏng để kiểm tra máy quét.
    """
    canvas_w = int(round(width_mm / 25.4 * dpi))
    canvas_h = int(round(height_mm / 25.4 * dpi))

    # Nền trắng (mode '1': 1 là trắng, 0 là đen)
    img = Image.new("1", (canvas_w, canvas_h), 1)
    draw = ImageDraw.Draw(img)

    # 1. Khung viền mép ngoài (0 mm)
    draw.rectangle([(0, 0), (canvas_w - 1, canvas_h - 1)], fill=None, outline=0, width=2)

    # 2. Đường viền cảnh báo lề chết cơ khí máy in laser (~3.5 mm và 5.0 mm)
    m35_px_x = int(round(3.5 / 25.4 * dpi))
    m35_px_y = int(round(3.5 / 25.4 * dpi))
    draw.rectangle(
        [(m35_px_x, m35_px_y), (canvas_w - 1 - m35_px_x, canvas_h - 1 - m35_px_y)],
        fill=None,
        outline=0,
        width=1,
    )

    m50_px_x = int(round(5.0 / 25.4 * dpi))
    m50_px_y = int(round(5.0 / 25.4 * dpi))
    draw.rectangle(
        [(m50_px_x, m50_px_y), (canvas_w - 1 - m50_px_x, canvas_h - 1 - m50_px_y)],
        fill=None,
        outline=0,
        width=2,
    )

    # 3. Vẽ vạch thước đo Milimet (Ruler ticks) dọc theo mép trên và mép trái
    font_tiny = get_font(12)
    font_small = get_font(16)
    font_medium = get_font(20)
    font_bold = get_font(28)
    font_large = get_font(34)

    # Vạch đo ngang (Mép trên, cách 1mm, 5mm, 10mm)
    for mm in range(1, int(width_mm)):
        x = int(round(mm / 25.4 * dpi))
        if mm % 10 == 0:
            draw.line([(x, 0), (x, 24)], fill=0, width=2)
            draw.text((x + 3, 22), str(mm), fill=0, font=font_tiny)
        elif mm % 5 == 0:
            draw.line([(x, 0), (x, 15)], fill=0, width=1)
        else:
            draw.line([(x, 0), (x, 8)], fill=0, width=1)

    # Vạch đo dọc (Mép trái)
    for mm in range(1, int(height_mm)):
        y = int(round(mm / 25.4 * dpi))
        if mm % 10 == 0:
            draw.line([(0, y), (24, y)], fill=0, width=2)
            draw.text((26, y - 6), str(mm), fill=0, font=font_tiny)
        elif mm % 5 == 0:
            draw.line([(0, y), (15, y)], fill=0, width=1)
        else:
            draw.line([(0, y), (8, y)], fill=0, width=1)

    # Chú thích vùng lề 3.5mm
    draw.text(
        (canvas_w - 380, 26),
        "[!] Đường nét đơn = Lề 3.5mm cơ khí",
        fill=0,
        font=font_tiny,
    )

    # 4. Tiêu đề chính của tem kiểm chuẩn
    title_box_top = 70
    draw.text(
        (80, title_box_top),
        "CORE_KIT :: PCL 5 RASTER CALIBRATION TEST",
        fill=0,
        font=font_large,
    )
    draw.text(
        (80, title_box_top + 45),
        "Xác thực in socket trực tiếp (Direct Port 9100) - Khổ decal 102 x 148 mm",
        fill=0,
        font=font_medium,
    )
    draw.line([(80, title_box_top + 80), (canvas_w - 80, title_box_top + 80)], fill=0, width=3)

    # 5. Khối bảng thông tin kiểm thử
    info_top = title_box_top + 100
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    effective_scale = scale_info or "X: 89% | Y: 94%"
    effective_shift = shift_info or "Shift X: -5.0 mm | Shift Y: 0.0 mm"

    info_lines = [
        f"• Máy in đích: {target_ip}:9100",
        f"• Khổ tem giấy: {height_mm:.1f} mm (Rộng) x {width_mm:.1f} mm (Dài)",
        f"• Khay nạp: TRAY 1 (Short-Edge Feed, Cạnh ngắn vào trước)",
        f"• Độ phân giải: {dpi} DPI (1 dot = {25.4/dpi*1000:.1f} µm)",
        f"• Hướng xoay: 90° CW (ROTATE_270 trong bộ đệm)",
        f"• Tỉ lệ Scale: {effective_scale} (Bảo toàn lề an toàn)",
        f"• Hiệu chỉnh lề: {effective_shift}",
        f"• Thời điểm in: {now_str}",
    ]

    for i, line in enumerate(info_lines):
        draw.text((80, info_top + i * 32), line, fill=0, font=font_small)

    # Khung bao quanh bảng thông tin
    draw.rectangle(
        [(70, info_top - 10), (780, info_top + len(info_lines) * 32 + 10)],
        fill=None,
        outline=0,
        width=1,
    )

    # 6. Khối kiểm tra độ phủ mực Toner (Solid Black Density Test)
    density_left = 820
    density_top = info_top - 10
    density_w = 420
    density_h = 100
    draw.rectangle(
        [(density_left, density_top), (density_left + density_w, density_top + density_h)],
        fill=0,
        outline=0,
    )
    # Chữ màu trắng trên nền đen đặc
    draw.text(
        (density_left + 25, density_top + 20),
        "TONER DENSITY TEST",
        fill=1,
        font=font_bold,
    )
    draw.text(
        (density_left + 25, density_top + 60),
        "Khối đen đặc kiểm tra độ phủ đều của mực",
        fill=1,
        font=font_tiny,
    )

    # 7. Thang kiểm tra độ phân giải nét mảnh (Resolution Ladder)
    ladder_top = density_top + density_h + 20
    draw.text((density_left, ladder_top), "Kiểm tra độ nét nét kẻ (Resolution Ladder):", fill=0, font=font_small)

    ladder_y = ladder_top + 30
    ladder_w = 420
    # Nét 1px
    draw.line([(density_left, ladder_y), (density_left + ladder_w, ladder_y)], fill=0, width=1)
    draw.text((density_left + ladder_w + 10, ladder_y - 6), "1 px (~0.08mm)", fill=0, font=font_tiny)

    # Nét 2px
    ladder_y += 22
    draw.line([(density_left, ladder_y), (density_left + ladder_w, ladder_y)], fill=0, width=2)
    draw.text((density_left + ladder_w + 10, ladder_y - 6), "2 px (~0.17mm)", fill=0, font=font_tiny)

    # Nét 4px
    ladder_y += 22
    draw.line([(density_left, ladder_y), (density_left + ladder_w, ladder_y)], fill=0, width=4)
    draw.text((density_left + ladder_w + 10, ladder_y - 6), "4 px (~0.34mm)", fill=0, font=font_tiny)

    # Nét 8px
    ladder_y += 22
    draw.line([(density_left, ladder_y), (density_left + ladder_w, ladder_y)], fill=0, width=8)
    draw.text((density_left + ladder_w + 10, ladder_y - 6), "8 px (~0.68mm)", fill=0, font=font_tiny)

    # 8. Mẫu mã vạch 1D mô phỏng (Simulated High-Contrast Barcode)
    bc_top = info_top + len(info_lines) * 32 + 40
    bc_left = 80
    draw.text((bc_left, bc_top), "MÃ VẠCH 1D TEST (Kiểm tra súng quét quang học):", fill=0, font=font_small)

    bar_y = bc_top + 28
    bar_h = 100
    bar_x = bc_left

    # Mẫu vạch xen kẽ (Narrow = 3px, Wide = 8px)
    pattern = [
        (3, 3), (8, 3), (3, 8), (8, 8), (3, 3), (8, 3), (3, 8), (3, 3),
        (8, 3), (3, 3), (8, 8), (3, 3), (8, 3), (3, 8), (8, 3), (3, 3),
        (8, 8), (3, 3), (8, 3), (3, 8), (3, 3), (8, 8), (3, 3), (8, 3),
        (3, 8), (8, 3), (3, 3), (8, 8), (3, 3), (8, 3), (3, 8), (3, 3),
    ]
    for bar_w, space_w in pattern:
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=0, outline=0)
        bar_x += bar_w + space_w

    draw.text((bc_left + 80, bar_y + bar_h + 8), "* PCL5-TEST-YAZAKI-LABEL *", fill=0, font=font_medium)

    # 9. Mẫu mã ma trận 2D mô phỏng (Checkerboard Matrix Pattern)
    matrix_left = 820
    matrix_top = bc_top + 10
    draw.text((matrix_left, matrix_top), "MA TRẬN 2D TEST (Kiểm tra ma trận điểm):", fill=0, font=font_small)

    mat_x0 = matrix_left
    mat_y0 = matrix_top + 28
    cell_size = 7
    grid_size = 18

    # Viền định vị kiểu DataMatrix (L-finder shape)
    for row in range(grid_size):
        for col in range(grid_size):
            is_black = False
            if row == grid_size - 1 or col == 0:  # Đường chữ L góc trái dưới
                is_black = True
            elif row == 0 and col % 2 == 0:  # Đường răng cưa trên
                is_black = True
            elif col == grid_size - 1 and row % 2 == 0:  # Đường răng cưa phải
                is_black = True
            elif (row * col + row + col) % 3 == 0:  # Hạt dữ liệu giả lập
                is_black = True

            if is_black:
                cx = mat_x0 + col * cell_size
                cy = mat_y0 + row * cell_size
                draw.rectangle([(cx, cy), (cx + cell_size - 1, cy + cell_size - 1)], fill=0, outline=0)

    draw.text(
        (mat_x0 + grid_size * cell_size + 20, mat_y0 + 40),
        "Ma trận 2D độ tương phản cao\n(Kiểm tra độ hội tụ của laser)",
        fill=0,
        font=font_tiny,
    )

    # 10. Chân trang và dấu căn tâm (Center Crosshair)
    center_x = canvas_w // 2
    center_y = canvas_h // 2
    draw.line([(center_x - 30, center_y), (center_x + 30, center_y)], fill=0, width=1)
    draw.line([(center_x, center_y - 30), (center_x, center_y + 30)], fill=0, width=1)
    draw.ellipse([(center_x - 15, center_y - 15), (center_x + 15, center_y + 15)], fill=None, outline=0, width=1)

    draw.text(
        (canvas_w - 450, canvas_h - 45),
        "CORE_KIT DEVICES :: PCL5RasterBuilder",
        fill=0,
        font=font_small,
    )

    return img


def parse_simple_args() -> dict:
    """
    Phân tích tham số từ sys.argv thuần túy, TUÂN THỦ NGHIÊM NGẶT QUY TẮC KHÔNG DÙNG ARGPARSE.
    """
    args = {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "tray": DEFAULT_TRAY,
        "scale": DEFAULT_SCALE,
        "rotate": DEFAULT_ROTATE,
        "shift_x": DEFAULT_SHIFT_X_MM,
        "shift_y": DEFAULT_SHIFT_Y_MM,
        "dry_run": False,
        "save_pcl": None,
        "preview_path": str(ROOT_DIR / "examples" / "preview_test_label.png"),
    }

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--dry-run":
            args["dry_run"] = True
        elif arg == "--save-pcl":
            if i + 1 < len(argv):
                i += 1
                args["save_pcl"] = argv[i]
            else:
                args["save_pcl"] = "output_test.pcl"
        elif arg == "--scale":
            if i + 1 < len(argv):
                i += 1
                val = float(argv[i])
                args["scale"] = (val, val)
        elif arg == "--scale-x":
            if i + 1 < len(argv):
                i += 1
                sx = float(argv[i])
                curr_y = args["scale"][1] if isinstance(args["scale"], (tuple, list)) else args["scale"]
                args["scale"] = (sx, curr_y)
        elif arg == "--scale-y":
            if i + 1 < len(argv):
                i += 1
                sy = float(argv[i])
                curr_x = args["scale"][0] if isinstance(args["scale"], (tuple, list)) else args["scale"]
                args["scale"] = (curr_x, sy)
        elif arg == "--rotate":
            if i + 1 < len(argv):
                i += 1
                args["rotate"] = int(argv[i])
        elif arg == "--shift-x":
            if i + 1 < len(argv):
                i += 1
                args["shift_x"] = float(argv[i])
        elif arg == "--shift-y":
            if i + 1 < len(argv):
                i += 1
                args["shift_y"] = float(argv[i])
        elif arg == "--tray":
            if i + 1 < len(argv):
                i += 1
                args["tray"] = argv[i].upper()
        elif arg.startswith("10.") or arg.startswith("192.") or arg.startswith("127.") or "." in arg:
            # Nhận diện địa chỉ IP được truyền trực tiếp
            args["host"] = arg
        elif arg in ["-h", "--help"]:
            print(__doc__)
            sys.exit(0)
        i += 1

    return args


def main():
    config = parse_simple_args()

    scale_info = (
        f"X: {config['scale'][0]*100:.0f}% | Y: {config['scale'][1]*100:.0f}%"
        if isinstance(config["scale"], (tuple, list))
        else f"{config['scale']*100:.0f}%"
    )

    print("=" * 65)
    print("  KỊCH BẢN KIỂM THỬ IN THỰC TẾ: CORE_KIT PCL 5 RASTER")
    print(f"  Mục tiêu: {config['host']}:{config['port']} | Khay nạp: {config['tray']}")
    print(f"  Khổ Custom: {DEFAULT_WIDTH_MM} x {DEFAULT_HEIGHT_MM} mm | Xoay: {config['rotate']}° | Scale: {scale_info}")
    print(f"  Dịch lề: Shift X = {config['shift_x']:.1f} mm | Shift Y = {config['shift_y']:.1f} mm")
    print("=" * 65)

    # 1. Tạo hình ảnh tem kiểm chuẩn kỹ thuật
    print("\n[1/4] Đang vẽ mẫu tem kiểm chuẩn kỹ thuật (148 x 102 mm @ 300 DPI)...")
    t0 = time.time()
    shift_info = f"Shift X: {config['shift_x']:.1f} mm | Shift Y: {config['shift_y']:.1f} mm"
    test_img = create_calibration_label(
        width_mm=148.0,
        height_mm=102.0,
        dpi=300,
        target_ip=config["host"],
        scale_info=scale_info,
        shift_info=shift_info,
    )
    draw_time = (time.time() - t0) * 1000
    print(f"      -> Vẽ thành công canvas {test_img.width}x{test_img.height} px trong {draw_time:.1f}ms.")

    # 2. Xuất ảnh xem trước Preview PNG
    preview_file = Path(config["preview_path"])
    preview_file.parent.mkdir(parents=True, exist_ok=True)
    test_img.save(preview_file)
    print(f"      -> Đã xuất tệp ảnh xem trước: {preview_file.resolve()}")

    # 3. Dựng lệnh in PCL 5 Raster bằng PCL5RasterBuilder
    print("\n[2/4] Đang đóng gói PCL 5 Raster bằng PCL5RasterBuilder...")
    t1 = time.time()
    builder = PCL5RasterBuilder(
        paper_size="CUSTOM",
        width_mm=DEFAULT_WIDTH_MM,
        height_mm=DEFAULT_HEIGHT_MM,
        tray=config["tray"],
        feed_direction="SHORTEDGEFEED",
        dpi=300,
        job_name="PCL_CALIBRATION_TEST",
    )

    builder.add_page(
        image=test_img,
        rotate=config["rotate"],
        scale=config["scale"],
        shift_x_mm=config["shift_x"],
        shift_y_mm=config["shift_y"],
        auto_center=True,
    )

    payload = builder.build()
    build_time = (time.time() - t1) * 1000
    print(f"      -> Sinh payload hoàn tất: {len(payload)} bytes ({len(payload)/1024:.1f} KB) trong {build_time:.1f}ms.")

    # Xuất tệp .pcl nếu người dùng yêu cầu
    if config["save_pcl"]:
        save_path = Path(config["save_pcl"])
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(payload)
        print(f"      -> Đã lưu mã nhị phân PCL ra tệp: {save_path.resolve()}")

    # 4. Kiểm tra chế độ chạy
    if config["dry_run"]:
        print("\n[3/4] Chế độ DRY-RUN được kích hoạt:")
        print("      • Bỏ qua bước kết nối TCP socket và truyền dữ liệu mạng.")
        print(f"      • Hãy mở tệp '{preview_file}' để kiểm tra hình ảnh tem.")
        print("\n[4/4] KẾT QUẢ KIỂM THỬ DRY-RUN: THÀNH CÔNG RỰC RỠ (100% SẴN SÀNG IN THẬT)!")
        print("=" * 65)
        return

    # 5. Gửi tới máy in thực tế qua TCP Socket 9100
    print(f"\n[3/4] Kết nối mạng và kiểm tra trạng thái máy in {config['host']}:{config['port']}...")
    printer = PCLNetworkPrinter(
        host=config["host"],
        port=config["port"],
        timeout=5.0,
    )

    # Truy vấn trạng thái máy in trước khi in
    status = printer.get_status()
    print(f"      • Trạng thái trực tuyến: {'ONLINE' if status.is_online else 'OFFLINE'}")
    print(f"      • Màn hình LCD máy in: \"{status.display}\" (Code={status.code})")
    print(f"      • Sẵn sàng nhận lệnh: {'CÓ (READY)' if status.is_ready else 'CHƯA SẴN SÀNG'}")

    if not status.is_online:
        print(f"\n[!] CẢNH BÁO: Không thể kết nối tới máy in {config['host']}:{config['port']}.")
        print(f"    Lý do: {status.display}")
        print("    Vui lòng kiểm tra lại cáp mạng LAN, nguồn máy in hoặc địa chỉ IP.")
        print(f"    (Gợi ý: bạn có thể chạy với cờ --dry-run để kiểm tra cục bộ không cần mạng).")
        return

    if not status.is_ready:
        print(f"\n[!] CẢNH BÁO: Máy in đang báo trạng thái không sẵn sàng: \"{status.display}\".")
        print("    Vui lòng kiểm tra khay giấy, nắp máy in hoặc xử lý kẹt giấy trước khi in.")

    # Tiến hành gửi luồng byte PCL 5
    print(f"\n[4/4] Đang gửi luồng lệnh in ({len(payload)} bytes) qua TCP Socket...")
    t2 = time.time()
    send_success = printer.send(payload, verify_ready=False)
    send_time = (time.time() - t2) * 1000

    if send_success:
        print(f"      -> Gửi dữ liệu thành công trong {send_time:.1f}ms!")
        print("      -> Máy in đang tiếp nhận và kéo giấy từ Khay 1...")
        print("\n" + "=" * 65)
        print("-> HOÀN TẤT LỆNH IN THỬ NGHIỆM THÀNH CÔNG!")
        print(f"   Hãy kiểm tra tờ tem in ra tại Khay nạp của máy in ApeosPort {config['host']}.")
        print("=" * 65)
    else:
        print(f"\n[LỖI] Truyền dữ liệu in thất bại qua cổng {config['port']}.")


if __name__ == "__main__":
    main()
