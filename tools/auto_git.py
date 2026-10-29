"""
Công cụ tự động hóa Git (auto_git) cho core_kit:
- Tự động kiểm tra thay đổi trong thư mục làm việc.
- Cho phép nhập thông điệp commit trực tiếp từ giao diện CLI (hoặc tự sinh nếu để trống).
- Gom tệp (git add), tạo commit và tự động nhận diện nhánh để đẩy (git push) kèm toàn bộ Git Tags.
- Tuân thủ quy tắc dự án: KHÔNG SỬ DỤNG THƯ VIỆN ARGPARSE.

Cách dùng:
    python tools/auto_git.py
    # Công cụ sẽ hỏi: "Nhập thông điệp commit (nhấn Enter để dùng mặc định): "
"""
from __future__ import annotations

from datetime import datetime
import subprocess
import sys

# Thiết lập bảng mã UTF-8 cho console Windows
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


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Thực thi một lệnh git và trả về kết quả."""
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
    )


def get_current_branch() -> str:
    """Lấy tên nhánh git hiện tại."""
    try:
        res = run_git(["branch", "--show-current"])
        branch = res.stdout.strip()
        if branch:
            return branch
    except Exception:
        pass

    try:
        res = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = res.stdout.strip()
        if branch and branch != "HEAD":
            return branch
    except Exception:
        pass

    return "main"


def has_working_tree_changes() -> bool:
    """Kiểm tra xem có tệp nào được sửa đổi hoặc chưa được track không."""
    res = run_git(["status", "--porcelain"])
    return bool(res.stdout.strip())


def main() -> None:
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    print("=" * 65)
    print("  AUTO GIT: TỰ ĐỘNG HÓA COMMIT VÀ PUSH")
    print("=" * 65)

    branch = get_current_branch()
    print(f"[*] Nhánh Git hiện tại: '{branch}'")

    has_changes = has_working_tree_changes()

    if has_changes:
        # 1. Nhập thông điệp commit từ bàn phím
        commit_msg = ""
        # Nếu có truyền đối số ngoài CLI thì ưu tiên lấy, còn lại hỏi tương tác
        cli_args = [a for a in sys.argv[1:] if not a.startswith("-")]
        if cli_args:
            commit_msg = " ".join(cli_args).strip()
        else:
            try:
                prompt_text = "Nhập thông điệp commit (nhấn Enter để dùng mặc định): "
                user_input = input(prompt_text).strip()
                if user_input:
                    commit_msg = user_input
            except (EOFError, KeyboardInterrupt):
                print("\n[!] Đã nhận tín hiệu hủy hoặc kết thúc.")
                sys.exit(0)

        # 2. Nếu để trống thì tự sinh thông điệp mặc định kèm ngày giờ
        if not commit_msg:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"chore: auto update {now_str}"
            print(f"[*] Sử dụng thông điệp mặc định: \"{commit_msg}\"")
        else:
            print(f"[*] Thông điệp commit: \"{commit_msg}\"")

        # 3. Stage toàn bộ tệp thay đổi
        print("\n[1/3] Đang gom toàn bộ tệp thay đổi (git add -A)...")
        res_add = run_git(["add", "-A"], check=False)
        if res_add.returncode != 0:
            print(f"[LỖI] git add thất bại:\n{res_add.stderr}")
            sys.exit(res_add.returncode)
        print("      -> Gom tệp thành công.")

        # 4. Commit
        print(f"\n[2/3] Đang tạo commit...")
        res_commit = run_git(["commit", "-m", commit_msg], check=False)
        if res_commit.returncode != 0:
            print(f"[LỖI] git commit thất bại:\n{res_commit.stderr}")
            sys.exit(res_commit.returncode)
        print(f"      -> Đã commit thành công:")
        for line in res_commit.stdout.strip().splitlines()[:2]:
            print(f"         {line}")
    else:
        print("\n[i] Thư mục làm việc sạch (không có tệp thay đổi mới để commit).")
        print("    -> Chuyển thẳng sang bước kiểm tra và đẩy các commit/tag còn tồn đọng.")

    # 5. Push lên GitHub (cả nhánh và tags)
    print(f"\n[3/3] Đang đẩy lên remote origin (git push origin {branch} --tags)...")
    # Sử dụng subprocess chạy trực tiếp để hiển thị tiến trình đẩy
    proc = subprocess.run(
        ["git", "push", "origin", branch, "--tags"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if proc.returncode == 0:
        print("      -> Đẩy code và tags lên GitHub thành công rực rỡ!")
        if proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                print(f"         {line}")
        if proc.stderr.strip():
            # Git push thường in thông tin tiến trình vào stderr
            for line in proc.stderr.strip().splitlines():
                print(f"         {line}")
        print("\n" + "=" * 65)
        print("-> HOÀN TẤT: Toàn bộ mã nguồn và tag đã được đồng bộ lên GitHub!")
        print("=" * 65)
    else:
        print(f"\n[LỖI] git push thất bại (mã thoát {proc.returncode}):")
        if proc.stderr:
            print(proc.stderr)
        if proc.stdout:
            print(proc.stdout)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()

