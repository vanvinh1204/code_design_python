# 02: Deep AuthManager Module with Centralized Token & Credential Governance

**What to build:**
Create a cohesive `AuthManager` class in `core_kit.auth` that encapsulates secret key storage, algorithm parameters, and expiration defaults provided via constructor or `AuthManager.from_settings(settings)`. Expose a clean, high-leverage interface: `issue_token()`, `verify_token()`, `hash_password()`, and `verify_password()`. Callers across FastAPI routes and PySide6 apps never need to touch or pass `secret_key` repeatedly. Keep standalone hashing functions at the module level for convenience.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Implement `AuthManager` class with token issuance, decoding, expiration validation, and password verification
- [ ] Implement `AuthManager.from_settings(settings)` classmethod reading `secret_key`, `jwt_algorithm`, `access_token_expire_minutes`
- [ ] Maintain standalone `hash_password()` and `verify_password()` in `core_kit.auth`
- [ ] Write unit tests for `AuthManager` covering token expiration, tampering, custom claims, and password matching
