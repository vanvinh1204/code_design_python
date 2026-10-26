# 04: Encapsulated ConfigVault & Argparse-Free CLI

**What to build:**
Create a unified `ConfigVault` class in `core_kit.config.vault` (or `core_kit.utils.crypto`) encapsulating Fernet key resolution, secret token detection (`enc:`), transparent recursive model decryption, value encryption, and in-place `.env` modification (`update_env_file()`) that preserves existing comments and formatting. Refactor `core_kit.tools.encrypt_env` to parse command-line arguments using `sys.argv` directly, completely removing the prohibited `argparse` dependency in strict compliance with `.agents/rules/python.md`. Maintain full backward compatibility for all existing utility functions in `core_kit.utils.crypto`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Implement `ConfigVault` with `encrypt()`, `decrypt()`, `decrypt_mapping()`, and `update_env_file()`
- [ ] Connect `BaseAppSettings` validator to use `ConfigVault.decrypt_mapping()`
- [ ] Rewrite `encrypt_env.py` using `sys.argv` without importing `argparse`
- [ ] Preserve existing functions in `core_kit.utils.crypto` for backward compatibility
- [ ] Write unit tests for `ConfigVault` and verify `encrypt_env.py` without `argparse`
