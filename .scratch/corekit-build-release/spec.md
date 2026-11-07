# `corekit build` & `corekit release` Specification

Status: ready-for-agent
Labels: ready-for-agent

## Problem Statement

Chuẩn dự án (`PROJECT_STANDARD.md` v1.2.0) hứa rằng `core_kit` cung cấp lệnh `corekit` để build EXE và phát hành bản giao khách, nhưng `core_kit` v0.2.0 chưa có CLI nào như vậy. Mỗi app phải tự viết lệnh đóng gói dài, tự nén zip, tự đặt tag, và dễ lọt `.env` thật vào bản gửi khách. Schema `[[tool.corekit.build.targets]]` trong file mẫu chỉ có `name/entry/icon/windowed/datas`, không đủ để một app thật dùng (`deepseek_python` đã phải lệch chuẩn, xem ADR 0001 của repo đó), và `entry` mẫu còn trỏ sai (`src/my_app/__main__.py` thay vì `main.py`).

Ngoài ra, code runtime của `core_kit` (tìm thư mục migration) chỉ nhận diện bản đóng gói kiểu PyInstaller (`sys.frozen`, `sys._MEIPASS`), nên bản build bằng Nuitka sẽ tìm sai đường dẫn khi CWD khác thư mục exe.

## Solution

`core_kit` thêm một CLI duy nhất `corekit` (extra `build`) với hai lệnh con:

- **`corekit build`**: đọc `[[tool.corekit.build.targets]]` trong `pyproject.toml` của app ở thư mục hiện tại, gọi **Nuitka** để build từng target ra `build/<chế độ>/<name>/`, chép kèm `.env` và các mục `copy` ra cạnh exe để bấm là chạy được. Chọn chế độ (nhanh / giao khách) và target qua menu đánh số; mọi lựa chọn có cờ tương ứng cho CI.
- **`corekit release`**: kiểm git sạch → chọn version → build giao khách mọi target → đóng **Bản giao khách** (zip, `.env.example` thay cho `.env`, kèm tài liệu) → commit + tag `<tên app>-vX.Y.Z` → hỏi rồi mới push và tạo GitHub Release để lưu trữ.

`core_kit` thêm `app_dir()` / `bundle_dir()` nhận diện đúng dev, Nuitka standalone, Nuitka onefile (và PyInstaller cũ), dùng cho migration, `.env` và thư mục log khi chạy bản đóng gói.

## User Stories

1. As an app developer, I want to type `uv run corekit build` in my app folder, so that I don't hand-write long Nuitka commands per project.
2. As an app developer, I want a numbered menu to pick fast or customer build, so that I don't have to remember flags.
3. As an app developer, I want Enter on the mode menu to pick the customer build, so that the default output is always safe to ship.
4. As an app developer, I want a fast mode without LTO and with Nuitka's compatibility checks kept, so that I iterate quickly and see missing-module hints.
5. As an app developer, I want fast builds to attach to my console even for windowed apps, so that I see tracebacks when testing from cmd.
6. As an app developer, I want customer builds with LTO and `--deployment`, so that the shipped exe is optimised and has no dev-only checks.
7. As a CI maintainer, I want `--fast` / `--release` flags, so that builds run unattended.
8. As a CI maintainer, I want a non-interactive run without a mode flag to fail with guidance, so that a build mode is never chosen silently.
9. As an app developer with several exes (UI + CLI tool), I want a target menu with "all" as default, so that I can rebuild just one.
10. As a CI maintainer, I want a repeatable `--target <name>` flag, so that I can build specific targets unattended; without it all targets build.
11. As an app developer, I want targets built one after another and stop at the first failure with a non-zero exit code, so that failures are obvious.
12. As an app developer, I want every target to have its own output folder, so that targets with different plugins/console modes don't interfere.
13. As an app developer, I want `entry = "main.py"` per the standard, so that the exe starts exactly like `py main.py`.
14. As an app developer, I want `icon`, `windowed`, `onefile`, `plugins` per target, so that each exe is configured explicitly in `pyproject.toml`.
15. As an app developer, I want `datas` (folders and files) bundled with their relative paths kept, so that read-only resources are found at runtime.
16. As an app developer, I want `copy` items placed next to the exe, not inside it, so that customers can edit or replace them (models, printer config).
17. As an app developer, I want `extra_args` passed straight to Nuitka, so that unusual needs don't force me off the standard.
18. As an app developer, I want the exe version resource taken from `[project].version` (pre-release suffix stripped) and `company` from config, so that Windows shows correct file properties.
19. As an app developer, I want my `.env` copied next to the exe automatically, so that double-clicking the exe just works on my machine.
20. As an app developer, I want `.env.example` copied with a warning when `.env` is missing, so that I notice the build has no real config.
21. As an app developer, I want the old output folder removed before each build, so that stale files never leak into a new build.
22. As an app developer, I want Nuitka to auto-download its C compiler, so that the first build on a fresh machine doesn't hang on a prompt.
23. As an app developer, I want a summary (path, size, time) after each target, so that I know where the result is.
24. As an app developer, I want clear errors when `pyproject.toml`, the target block, the entry file, the icon, or a `datas`/`copy` path is missing, so that I fix config before a long build.
25. As an app developer, I want `uv run corekit release`, so that shipping a version is one command.
26. As an app developer, I want release to refuse a dirty git tree, so that every shipped build maps to a commit.
27. As an app developer, I want a version menu (patch/minor/major/keep), so that I don't edit `pyproject.toml` by hand.
28. As a CI maintainer, I want `--bump patch|minor|major|keep`, so that releases run unattended.
29. As an app developer, I want "keep" refused when the tag already exists, so that a tag never points at two different builds.
30. As an app developer, I want `pyproject.toml` (and `uv.lock`) restored if the build fails, so that a failed release leaves no trace.
31. As an app developer, I want release to always build all targets in customer mode without asking, so that a release is never a fast build.
32. As an app developer, I want one zip per target named `<name>-<version>-win-x64.zip` in `dist/`, so that I can send only what a customer needs.
33. As an app developer, I want the zip to contain a single `<name>-<version>/` root folder, so that customers can unpack several versions side by side.
34. As an app developer, I want the real `.env` never included in the zip, and `.env.example` always included, so that secrets never reach customers.
35. As an app developer, I want release to fail early if `.env.example` is missing, so that customers always get a config template.
36. As an app developer, I want `[tool.corekit.release].include` to add guides/changelog to the zip root, so that delivery docs travel with the build.
37. As an app developer, I want release to commit `chore(release): <app> vX.Y.Z` and tag `<app>-vX.Y.Z`, so that versions of several apps in one repo don't collide.
38. As an app developer, I want release to ask before pushing anything, so that nothing leaves my machine without consent.
39. As an app developer, I want the push to create a GitHub Release with the zips attached, so that I can retrieve exactly what a customer received.
40. As an app developer, I want release notes taken from the matching `CHANGELOG.md` section, falling back to GitHub's generated notes, so that notes need no extra work.
41. As an app developer, I want a warning and a continue prompt when `CHANGELOG.md` has no section for the new version, so that I can stop and write it.
42. As an app developer, I want a clear error when `gh` is not installed, with the local commit and tag kept, so that I can push manually.
43. As a desktop app developer, I want `core_kit` to resolve `migrations/`, `.env` and `logs/` relative to the exe in packaged builds, so that the app works when started from a shortcut with a different working directory.
44. As a maintainer of `core_kit`, I want `core_kit` tags named `core_kit-vX.Y.Z`, so that the template's `[tool.uv.sources]` pin works.

## Implementation Decisions

- **Nuitka only.** No PyInstaller backend. Nuitka is invoked as `<python của venv app> -m nuitka`, so it sees the app's dependencies. `core_kit` gains extra `build = ["nuitka>=2.8", "zstandard", "tomli (py<3.11)"]` and console script `corekit`. Apps add `core-kit[build]` to their `dev` dependency group.
- **CLI shape** (no argparse, per repo rule): `corekit build [--fast|--release] [--target NAME]...`, `corekit release [--bump patch|minor|major|keep] [--publish|--no-publish]`, `corekit --help`. Only `pyproject.toml` in the current directory is read.
- **Interactive rules:** menus are numbered and read through the `ask` port. Mode default = customer build; target default = all; version default = patch; publish default = no. When stdin is not a terminal: missing mode flag → error; missing `--target` → all; missing `--bump` → error; missing publish flag → no publish.
- **Build modes:**
  - fast: `--lto=no`, no `--deployment`, `--windows-console-mode=attach`, output `build/fast/<name>/`.
  - release: `--lto=yes`, `--deployment`, console `disable` if `windowed` else `force`, output `build/release/<name>/`.
  - both: `--mode=standalone|onefile`, `--assume-yes-for-downloads`, `--remove-output`, `--jobs=<cpu>`, `--output-filename=<name>.exe`, `--product-name`, `--product-version`/`--file-version` (numeric prefix of `[project].version`, max 4 parts), `--company-name` if set, `--windows-icon-from-ico`, `--enable-plugins`, `--include-data-dir`/`--include-data-files`, then `extra_args`, then the entry file.
- **Output layout:** Nuitka writes into a staging folder; corekit moves the result so each target always ends up in `build/<mode>/<name>/` (standalone: the dist folder contents; onefile: `<name>.exe` inside that folder). Then `.env` (or `.env.example` + warning) and `copy` items are placed next to the exe. Runtime folders `data/ logs/ secrets/` are never copied. No smoke run.
- **Schema:**
  - `[tool.corekit.build] company` (optional).
  - `[[tool.corekit.build.targets]]`: `name` (required), `entry` (default `main.py`), `icon`, `windowed` (default false), `onefile` (default false), `datas`, `plugins`, `copy`, `extra_args` (lists default empty).
  - `[tool.corekit.release] include` (list, default empty).
  - Unknown keys in a target → error (catches typos).
- **Release sequence:** git clean check → choose version (and refuse existing tag) → validate `.env.example`, `include`, CHANGELOG section (warn + ask) → write version into `[project]` of `pyproject.toml` (+ `uv lock` when `uv.lock` exists) → build all targets in release mode → zip per target → commit only the version files + annotated tag. Any failure before the commit restores `pyproject.toml`/`uv.lock` and removes zips created in this run. Publish (optional) = check `gh` present → `git push origin HEAD` + push tag → `gh release create <tag> <zips> --title ... (--notes-file | --generate-notes)`.
- **Tag name:** `<[project].name>-v<version>`; commit message `chore(release): <name> v<version>`.
- **Ports seam:** the CLI entry is `main(argv, ports)`. `Ports` bundles `ask`, `is_interactive`, `echo`, `which` and one process runner `run(cmd, cwd)` that serves Nuitka, git, uv and gh (one runner instead of separate git/gh ports keeps a single fake). Real ports are the default.
- **Runtime paths (`core_kit.utils.paths`):**
  - `is_packaged()`: Nuitka (`__compiled__`) or `sys.frozen`.
  - `app_dir()`: folder holding the exe. Nuitka onefile → `__compiled__.containing_dir`; Nuitka standalone / PyInstaller → parent of `sys.executable`; dev → CWD.
  - `bundle_dir()`: folder holding bundled read-only `datas`. Nuitka → parent of `sys.executable` (temp extraction folder for onefile); PyInstaller → `sys._MEIPASS`; dev → CWD.
  - `resolve_script_location` checks `bundle_dir()`, then `app_dir()`, then CWD. `BaseAppSettings` reads `app_dir()/.env` and `setup_logger` anchors a relative `log_dir` at `app_dir()` only when packaged; dev behaviour is unchanged.

## Testing Decisions

- A good test drives the CLI the way a user does — `main(argv, fake_ports)` against a throwaway app in `tmp_path` — and asserts only on observable results: the Nuitka command recorded by the fake runner, the files under `build/` and `dist/`, the zip contents, the git/gh commands issued, the exit code and printed errors, and `pyproject.toml` after a rollback. The internal build plan is not tested directly.
- The fake runner emulates Nuitka by creating the dist folder / onefile exe it would produce, and answers git/uv/gh commands from scripted results.
- `app_dir()` / `bundle_dir()` are tested on their own by faking `__compiled__`, `sys.frozen`, `sys._MEIPASS`, `sys.executable`.
- One real end-to-end test, marker `nuitka` (excluded by default like `hardware` in the app standard), builds a hello-world app in fast mode, standalone and onefile, runs the exe and checks `app_dir()` from inside it.
- Prior art: `tests/test_crypto_env.py` calls the `encrypt-env` CLI `main()` directly; `tests/test_database_migration.py` uses `tmp_path` apps.

## Out of Scope

- PyInstaller backend, Nuitka multidist, installers (Inno Setup/MSI), code signing.
- Automatic smoke run of built exes (`smoke_args` may come later).
- Writing CHANGELOG entries; release only reads them.
- `corekit fetch-models`.
- Non-Windows targets (zip suffix is fixed to `win-x64`).
- Setting up CI.

## Further Notes

- `deepseek_python` keeps its hand-written PyInstaller `.spec` (its ADR 0001). The ADR's trigger ("when `corekit build` accepts a key pointing to a `.spec`") will not happen because corekit moved to Nuitka; that ADR should get a note.
- The app template in `project_standard` must be fixed: `entry = "main.py"`, the real repo URL `code_design_python.git`, tag `core_kit-v0.3.0`, new fields, `core-kit[build]` in `dev`. `PROJECT_STANDARD.md` goes to v1.3.0.
- The `__compiled__.containing_dir` behaviour for onefile is read from Nuitka 2.8.8 source, not yet observed; the `nuitka` test confirms it.
