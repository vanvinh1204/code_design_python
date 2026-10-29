"""Thử 3 cách khai báo khổ giấy 102x148 mm tới máy Brother-based (ApeosPrint 4620 SDW).

Ảnh thử: portrait 102 x 148 mm @300dpi, KHÔNG xoay/scale/shift, để đo lệch thô.
Dùng: python -I paper_probe.py <host> [--dry-run]
"""
import socket
import struct
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DPI = 300
W_MM, H_MM = 102.0, 148.0
OUT = Path(__file__).resolve().parent
UEL = b"\x1b%-12345X"


def px(mm: float) -> int:
    return int(round(mm / 25.4 * DPI))


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def make_image(tag: str, desc: str) -> Image.Image:
    w, h = px(W_MM), px(H_MM)
    img = Image.new("1", (w, h), 1)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=0, width=3)
    d.rectangle([px(5), px(5), w - 1 - px(5), h - 1 - px(5)], outline=0, width=1)
    f_small, f_big = font(22), font(90)
    for mm in range(1, int(W_MM)):
        x = px(mm)
        ln = 40 if mm % 10 == 0 else 22 if mm % 5 == 0 else 10
        d.line([(x, 0), (x, ln)], fill=0, width=2 if mm % 10 == 0 else 1)
        if mm % 10 == 0:
            d.text((x + 3, 40), str(mm), fill=0, font=f_small)
    for mm in range(1, int(H_MM)):
        y = px(mm)
        ln = 40 if mm % 10 == 0 else 22 if mm % 5 == 0 else 10
        d.line([(0, y), (ln, y)], fill=0, width=2 if mm % 10 == 0 else 1)
        if mm % 10 == 0:
            d.text((44, y - 10), str(mm), fill=0, font=f_small)
    cx, cy = w // 2, h // 2
    d.line([(cx - 60, cy), (cx + 60, cy)], fill=0, width=2)
    d.line([(cx, cy - 60), (cx, cy + 60)], fill=0, width=2)
    d.text((px(15), px(30)), tag, fill=0, font=f_big)
    for i, line in enumerate(desc.split("\n")):
        d.text((px(15), px(45) + i * 34), line, fill=0, font=font(28))
    d.text((px(15), h - px(15)), "MEP DUOI (bottom edge)", fill=0, font=font(28))
    return img


def pjl(job: str, lang: str, extra: list[str]) -> bytes:
    lines = [f'@PJL JOB NAME = "{job}"', "@PJL SET MEDIASOURCE = TRAY2", *extra,
             f"@PJL ENTER LANGUAGE = {lang}"]
    return UEL + b"@PJL\r\n" + "".join(l + "\r\n" for l in lines).encode()


def pjl_end(job: str) -> bytes:
    return UEL + f'@PJL EOJ NAME = "{job}"\r\n'.encode() + UEL


# ---------- PA1: PCL5 + khổ chuẩn P4X6 ----------
def job_pcl5(img: Image.Image) -> bytes:
    b = bytearray(pjl("PA1", "PCL", ["@PJL SET PAPER = P4X6"]))
    b += b"\x1bE"  # reset
    b += b"\x1b&l74A\x1b&l0O\x1b&l0E\x1b&l0L"
    b += b"\x1b*t300R\x1b*p0x0Y\x1b*r1A"
    stride = (img.width + 7) // 8
    raw = img.tobytes()
    for r in range(img.height):
        row = bytes(x ^ 0xFF for x in raw[r * stride:(r + 1) * stride])
        b += f"\x1b*b{len(row)}W".encode() + row
    b += b"\x1b*rB\x0c\x1bE"
    b += pjl_end("PA1")
    return bytes(b)


# ---------- PA2: PCL XL + CustomMediaSize ----------
def a_ubyte(v, aid):
    return bytes([0xC0, v, 0xF8, aid])


def a_uint16(v, aid):
    return b"\xc1" + struct.pack("<H", v) + bytes([0xF8, aid])


def a_uint16_xy(x, y, aid):
    return b"\xd1" + struct.pack("<HH", x, y) + bytes([0xF8, aid])


def a_real32_xy(x, y, aid):
    return b"\xd5" + struct.pack("<ff", x, y) + bytes([0xF8, aid])


def job_pclxl(img: Image.Image) -> bytes:
    b = bytearray(pjl("PA2", "PCLXL", []))
    b += b") HP-PCL XL;2;0;Comment paper probe\n"
    # BeginSession: UnitsPerMeasure, Measure=eInch, ErrorReport=eErrorPage
    b += a_uint16_xy(DPI, DPI, 0x89) + a_ubyte(0, 0x86) + a_ubyte(2, 0x8F) + b"\x41"
    # OpenDataSource: SourceType=eDefaultDataSource, DataOrg=eBinaryLowByteFirst
    b += a_ubyte(0, 0x88) + a_ubyte(1, 0x82) + b"\x48"
    # BeginPage: Orientation=portrait, MediaSource=eDefaultSource, CustomMediaSize mm
    b += a_ubyte(0, 0x28) + a_ubyte(0, 0x26)
    b += a_real32_xy(W_MM, H_MM, 0x2F) + a_ubyte(1, 0x30) + b"\x43"
    # SetColorSpace eGray
    b += a_ubyte(1, 0x03) + b"\x6a"
    # SetCursor (0,0)
    b += a_uint16_xy(0, 0, 0x4C) + b"\x6b"
    # BeginImage: eDirectPixel, e1Bit, SourceWidth/Height, DestinationSize
    b += a_ubyte(0, 0x64) + a_ubyte(0, 0x62) + a_uint16(img.width, 0x6C)
    b += a_uint16(img.height, 0x6B) + a_uint16_xy(img.width, img.height, 0x67) + b"\xb0"
    # ReadImage: rows padded to 4 byte; gray 1-bit: 0=black,1=white (khớp PIL '1')
    stride = (img.width + 7) // 8
    pad = (stride + 3) // 4 * 4
    raw = img.tobytes()
    data = b"".join(raw[r * stride:(r + 1) * stride] + b"\xff" * (pad - stride)
                    for r in range(img.height))
    b += a_uint16(0, 0x6D) + a_uint16(img.height, 0x63) + a_ubyte(0, 0x65) + b"\xb1"
    b += b"\xfa" + struct.pack("<I", len(data)) + data
    b += b"\xb2"  # EndImage
    b += a_uint16(1, 0x31) + b"\x44"  # EndPage PageCopies=1
    b += b"\x49\x42"  # CloseDataSource, EndSession
    b += pjl_end("PA2")
    return bytes(b)


# ---------- PA3: PostScript + setpagedevice PageSize ----------
def job_ps(img: Image.Image) -> bytes:
    wpt, hpt = W_MM / 25.4 * 72, H_MM / 25.4 * 72
    head = (
        "%!PS-Adobe-3.0\n"
        f"<< /PageSize [{wpt:.2f} {hpt:.2f}] >> setpagedevice\n"
        f"/picstr {(img.width + 7) // 8} string def\n"
        f"{wpt:.2f} {hpt:.2f} scale\n"
        f"{img.width} {img.height} 1 [{img.width} 0 0 -{img.height} 0 {img.height}]\n"
        "{currentfile picstr readhexstring pop} image\n"
    )
    hexdata = img.tobytes().hex()
    body = "\n".join(hexdata[i:i + 120] for i in range(0, len(hexdata), 120))
    ps = head + body + "\nshowpage\n%%EOF\n"
    return pjl("PA3", "POSTSCRIPT", []) + ps.encode("ascii") + b"\x04" + pjl_end("PA3")


def send(host: str, payload: bytes):
    with socket.create_connection((host, 9100), timeout=10) as s:
        s.sendall(payload)
        s.shutdown(socket.SHUT_WR)
        time.sleep(1)


def main():
    host = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jobs = [
        ("PA1", "PCL5 + P4X6\nESC&l74A + PJL PAPER=P4X6", job_pcl5),
        ("PA2", "PCL XL\nCustomMediaSize 102x148mm", job_pclxl),
        ("PA3", "PostScript\nPageSize 289x420pt", job_ps),
    ]
    for tag, desc, fn in jobs:
        img = make_image(tag, desc)
        img.save(OUT / f"{tag}.png")
        payload = fn(img)
        (OUT / f"{tag}.prn").write_bytes(payload)
        print(f"{tag}: {len(payload)} bytes", flush=True)
        if not dry:
            send(host, payload)
            print(f"{tag}: sent", flush=True)
            time.sleep(8)


if __name__ == "__main__":
    main()
