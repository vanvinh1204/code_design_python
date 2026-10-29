"""
Công cụ tự động hóa nâng phiên bản (Version Bumper) cho core_kit.
Tuân thủ nghiêm ngặt quy tắc dự án: KHÔNG SỬ DỤNG THƯ VIỆN ARGPARSE.

Cách dùng:
    python tools/bump_version.py patch     # Ví dụ: 0.2.0 -> 0.2.1
    python tools/bump_version.py minor     # Ví dụ: 0.2.0 -> 0.3.0
    python tools/bump_version.py major     # Ví dụ: 0.2.0 -> 1.0.0
    python tools/bump_version.py 0.3.5     # Gán trực tiếp phiên bản cụ thể
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Đảm bảo console Windows in chuẩn UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
INIT_PATH = ROOT_DIR / "src" / "core_kit" / "__init__.py"


def get_current_version() -> str:
    """Đọc phiên bản hiện tại từ pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        print(f"[LỖI] Không tìm thấy {PYPROJECT_PATH}")
        sys.exit(1)

    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        print("[LỖI] Không tìm thấy trường 'version' trong pyproject.toml")
        sys.exit(1)

    return match.group(1)


def calculate_next_version(current: str, bump_type: str) -> str:
    """Tính toán số phiên bản kế tiếp theo SemVer."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current)
    if not match:
        print(f"[LỖI] Phiên bản hiện tại '{current}' không đúng chuẩn SemVer (X.Y.Z)")
        sys.exit(1)

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))

    b_type = bump_type.lower().strip()
    if b_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif b_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif b_type == "major":
        return f"{major + 1}.0.0"
    else:
        # Nếu truyền trực tiếp số phiên bản cụ thể (ví dụ 0.3.5)
        if re.match(r"^\d+\.\d+\.\d+.*$", b_type):
            return b_type
        print(f"[LỖI] Loại nâng cấp '{bump_type}' không hợp lệ. Chọn patch, minor, major hoặc số phiên bản cụ thể.")
        sys.exit(1)


def update_pyproject(new_version: str) -> None:
    """Cập nhật version trong pyproject.toml."""
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    updated = re.sub(
        r'^version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT_PATH.write_text(updated, encoding="utf-8")


def update_init(new_version: str) -> None:
    """Cập nhật __version__ trong src/core_kit/__init__.py."""
    if not INIT_PATH.exists():
        print(f"[LỖI] Không tìm thấy {INIT_PATH}")
        sys.exit(1)

    content = INIT_PATH.read_text(encoding="utf-8")
    updated = re.sub(
        r'^__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    INIT_PATH.write_text(updated, encoding="utf-8")


def print_usage() -> None:
    print(__doc__.strip())


def main() -> None:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    flags = [arg for arg in sys.argv[1:] if arg.startswith("-")]

    if "-h" in flags or "--help" in flags or not args:
        print_usage()
        sys.exit(0)

    bump_arg = args[0]
    current_version = get_current_version()
    new_version = calculate_next_version(current_version, bump_arg)

    print("=" * 60)
    print(f"  NÂNG PHIÊN BẢN CORE_KIT: {current_version} -> {new_version}")
    print("=" * 60)

    update_pyproject(new_version)
    print(f"  [✓] Đã cập nhật: {PYPROJECT_PATH.relative_to(ROOT_DIR)}")

    update_init(new_version)
    print(f"  [✓] Đã cập nhật: {INIT_PATH.relative_to(ROOT_DIR)}")

    print("\nBước tiếp theo:")
    print(f"  1. Cập nhật nội dung phiên bản mới vào: CHANGELOG.md")
    print(f"  2. Chạy lệnh commit:")
    print(f'     git commit -am "chore(release): bump version to {new_version}"')
    print(f"  3. Đánh dấu Git Tag:")
    print(f'     git tag -a v{new_version} -m "Release v{new_version}"')
    print("=" * 60)


if __name__ == "__main__":
    main()
