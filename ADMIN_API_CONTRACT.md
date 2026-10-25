# Admin API Contract

**Source snapshot:** `main` @ `774539d` (`feat: Added REDIS_URL to env`)
**Review date:** 2026-10-23
**Scope:** The FastAPI backend in this repository only. This document describes implementation behavior, not intended or future behavior.
**Audience:** Frontend engineers integrating an admin console, and reviewers assessing production readiness.

> **Read this first**
>
> 1. `POST /admin/register` is **public** and creates a fully privileged `ADMIN` account. Until that is changed, every admin-only route is effectively reachable by anyone who can call the registration endpoint.
> 2. `GET /wallet/deposit/{id}` and `GET /wallet/withdrawal/{id}` require any authenticated user, not an admin, and do **not** check ownership. Any logged-in user can read another user's deposit or withdrawal by guessing an ID. They are documented in the appendix and are **not** part of the 34-route admin inventory.
> 3. `POST /plan/create` returns **`401`** for a duplicate plan title even when the caller is a valid admin. A global "401 means log out" interceptor will incorrectly log admins out.
> 4. Deletes are hard deletes for users and assets, and foreign keys cascade into financial history. Do not expose them as casual one-click actions.

This document uses three certainty labels:

| Label | Meaning |
|---|---|
| **Confirmed** | Read directly from the implementation, and where practical verified with a non-mutating runtime probe. |
| **Inferred** | Derived from framework or database semantics rather than a live end-to-end test in this review. |
| **Unverified** | Could not be tested without live MySQL/Redis or would require creating, changing, or deleting data. |

No production base URL is defined in this repository. Examples use `https://<backend-host>` as a placeholder. Never commit real hosts, tokens, passwords, or user data to this document.

---

## A. Overview

### A.1 Purpose

This contract gives a frontend integration agent everything needed to build and review an admin console against the current backend:

- The complete admin-related route inventory, including which routes are public, admin-only, or shared with normal users.
- Request and response shapes, field types, validation constraints, status codes, and exact error strings.
- Authentication, session, Redis, email, database, and financial side effects.
- Pagination, filtering, and sorting behavior.
- Known bugs, security gaps, inconsistencies, and missing capabilities.
- File-level source traceability for every claim.

The contract intentionally documents two related non-admin routes in a separate appendix because an admin UI is likely to call them and because their authorization is unsafe.

### A.2 Scope and method

| Item | Value |
|---|---|
| Framework | FastAPI (`fastapi 0.136.1` in the reviewed environment) |
| Validation | Pydantic v2 (`pydantic 2.13.4`) |
| Database | MySQL via `mysql-connector-python`, `autocommit=False` |
| Session store | Redis (async client), required at startup |
| App entry point | `app.main:app` |
| Local runner | `python run.py` → host `0.0.0.0`, port from `PORT`, default **8001** |
| Direct uvicorn | `uvicorn app.main:app` → uvicorn default **8000** |
| Base URL in examples | `https://<backend-host>` (placeholder only) |
| OpenAPI | `GET /openapi.json`, `GET /docs`, `GET /redoc` |

**Method:** every route module, service, helper, Pydantic model, query, migration, and admin integration test in the repository was read. The live route table was enumerated by importing `app.main`. Non-mutating probes were used to confirm the missing-auth response, the validation-error shape, and extra-field handling. Integration tests were reviewed but **not executed**, because they require live MySQL/Redis and create/delete users, admins, deposits, withdrawals, plans, instruments, and trades.

### A.3 Routing model

All routes are included from `app/main.py:101-109` with no global prefix. The admin-related routes live under these prefixes:

| Prefix | Router file | Admin-related routes |
|---|---|---:|
| `/admin` | `app/routes/admin_routes.py` | 15 |
| `/wallet` | `app/routes/wallet_routes.py` | 6 admin routes (+2 related non-admin) |
| `/plan` | `app/routes/plan_routes.py` | 3 |
| `/assets` | `app/routes/asset_routes.py` | 4 |
| `/instruments` | `app/routes/instrument_routes.py` | 4 |
| `/portfolio` | `app/routes/portfolio_routes.py` | 2 |
| **Total** | | **34** |

There is no API version prefix (no `/v1`). There is no trailing-slash normalization contract beyond FastAPI's default redirect behavior.

### A.4 Authentication model

#### A.4.1 Bearer JWT

Protected routes use FastAPI's `HTTPBearer` security scheme:

```http
Authorization: Bearer <access_token>
```

`app/utils/jwt.py:65-88`:

1. Reads the bearer credential.
2. Decodes the JWT with `ACCESS_SECRET_KEY` and the configured `ALGORITHM`.
3. Requires a `user_id` claim; otherwise `401 {"detail":"Invalid token"}`.
4. Reads the exact access token from Redis under `user:{user_id}:access_token:{role}`.
5. Rejects if the stored token is missing or is not byte-for-byte equal to the presented token: `401 {"detail":"Token is not valid or has been revoked"}`.
6. Returns `CurrentUser(user_id, role)` from the JWT payload.

`require_admin` then checks `role == "ADMIN"`; a valid non-admin token gets `403 {"detail":"Admin privileges required."}` (`app/utils/jwt.py:91-103`).

There are no scopes, permissions, tenant IDs, `iss`, `aud`, `nbf`, `iat`, or `jti` claims. There is one role level: `ADMIN`. Every admin can manage every other admin.

#### A.4.2 Token types and lifetimes

| Token | Secret env var | Default lifetime | Redis key | Redis TTL |
|---|---|---:|---|---:|
| Access | `ACCESS_SECRET_KEY` | 2 hours | `user:{id}:access_token:{ROLE}` | 7200 s |
| Refresh | `ACCESS_REFRESH_SECRET_KEY` | 7 days | `user:{id}:refresh_token:{ROLE}` | 604800 s |
| Password reset | `PASSWORD_RESET_SECRET_KEY` | 1 hour | `user:{id}:reset_password_token:ADMIN` | 3600 s |
| OTP secret | n/a | 5 minutes | `user:{id}:otp:ADMIN` | 300 s |

`{ROLE}` is `ADMIN` for admin tokens and `USER` for user tokens. Redis stores the **exact token string**, so a new login overwrites the previous session for that role. Logging in on a second device invalidates the first device's access token because only one access token per admin ID is stored.

The refresh endpoint does **not** rotate the refresh token. It issues a new access token and leaves the same refresh token in Redis (`app/services/user_services.py:514-523`).

#### A.4.3 Authorization categories

| Category | Count | Routes |
|---|---:|---|
| Public | 6 | `POST /admin/register`, `/admin/login`, `/admin/refresh`, `/admin/forgot-password`, `/admin/verify-otp`, `/admin/reset-password` |
| Admin-only | 26 | All routes marked **Admin** in Section B |
| Shared any-auth | 2 | `GET /plan`, `GET /assets` |
| Related non-admin (appendix) | 2 | `GET /wallet/deposit/{id}`, `GET /wallet/withdrawal/{id}` |

`GET /plan` is role-sensitive: an admin sees **all** plans (including `INACTIVE`); a normal user sees only `ACTIVE` plans. `GET /assets` returns all assets to any authenticated caller and does not change behavior by role. Both are included in the 34-route inventory because an admin UI needs them.

#### A.4.4 Auth failure matrix

| Condition | Status | Body | Notes |
|---|---:|---|---|
| No `Authorization` header | 401 | `{"detail":"Not authenticated"}` | `WWW-Authenticate: Bearer` **Confirmed** |
| Non-Bearer scheme | 401 | `{"detail":"Not authenticated"}` | `WWW-Authenticate: Bearer` **Confirmed** |
| Malformed JWT | 401 | `{"detail":"Invalid token"}` | No `WWW-Authenticate` in the probe **Confirmed** |
| Expired access token | 401 | `{"detail":"Access token has expired"}` | **Confirmed** in code |
| Expired refresh token | 401 | `{"detail":"Refresh token has expired"}` | Used by `/admin/refresh` |
| Expired reset token | 401 | `{"detail":"Password reset token has expired"}` | Used by `/admin/reset-password` |
| Token not in Redis / replaced | 401 | `{"detail":"Token is not valid or has been revoked"}` | **Confirmed** in code |
| Valid non-admin token on admin route | 403 | `{"detail":"Admin privileges required."}` | Requires a valid `USER` session |
| Refresh token for a user on `/admin/refresh` | 403 | `{"detail":"Admin privileges required."}` | Role check before Redis lookup |
| Redis unavailable during auth | 500 | Plain text `Internal Server Error` (likely) | Not wrapped by a route handler; **Inferred** |

Missing/expired authentication is not uniformly `403`: `HTTPBearer` handles missing/invalid scheme as `401`, while an authenticated non-admin gets `403`.

### A.5 Request and response conventions

| Convention | Behavior |
|---|---|
| Content type | JSON (`application/json`) for all request bodies. |
| Success status | **Always `200`**. No `201`, `202`, or `204` anywhere in these routes. |
| Envelope | No generic success wrapper. Each endpoint returns its model directly, except lists and plan lists. |
| Decimal fields | Serialized as JSON **strings** (Pydantic v2 behavior), e.g. `"100.00"`. Parse with a decimal library, not `parseFloat` for money. |
| Datetime fields | ISO 8601 strings from MySQL `TIMESTAMP` values, generally without a timezone offset, e.g. `"2026-10-23T10:15:00"`. Treat as server-local/naive unless deployment timezone is known. **Inferred** |
| Nulls | Optional fields are present with `null` when the response model includes them. |
| Booleans | Real JSON booleans. |
| Enums | Uppercase for roles, plan status, risk management, trade type; lowercase for deposit/withdrawal status. |
| Extra request fields | Ignored by Pydantic's default `extra="ignore"`. Confirmed by probing `POST /admin/register` with an unknown field. |
| Unknown query params | Ignored by FastAPI. |
| Response model filtering | Fields declared on the response model are returned; extra SQL columns are not. Several routes have no response model (register, login, logout, forgot/verify/reset, delete routes), so their literal dicts are returned. |
| Arrays | Returned as bare JSON arrays, not `{"data":[...]}`. `GET /plan` is the exception: `{"plans":[...]}`. |
| Empty search | Usually `[]`; `GET /assets` is a notable `404`. See Section F.4. |

### A.6 Error format and status semantics

There are three error shapes.

**1. Handled `HTTPException` (most business errors):**

```json
{"detail": "Deposit is not pending or does not exist."}
```

`detail` is always a single string in the reviewed routes. FastAPI would normally allow a list/object, but none of these routes raise one.

**2. Request validation error (custom handler):**

```json
{"detail": "password: String should have at least 8 characters"}
```

`app/main.py:52-90` collapses Pydantic errors to the **first** error only. The location is joined with dots and excludes `body`, `query`, and `path`. The `Value error, ` prefix is stripped. Examples confirmed by probe:

- Missing email: `{"detail":"email: Field required"}`
- Short password: `{"detail":"password: String should have at least 8 characters"}`
- Long password: `{"detail":"password: String should have at most 100 characters"}`
- Bad email: `{"detail":"email: value is not a valid email address: An email address must have an @-sign."}`

Only the first validation error is returned, so a form should validate all fields client-side rather than relying on the server to list them.

**3. Unhandled exception:**

Plain-text `Internal Server Error` with status `500` (Starlette default when debug is off), or a handled `500 {"detail":"<exception text>"}` where a service catches `Exception` and calls `str(e)`. Many services do the latter, which can leak database and Redis error text. Redis errors inside auth dependencies are not caught and are likely plain text. **Inferred/partly confirmed**

**Status code usage across these routes:**

| Status | Used for |
|---:|---|
| 200 | Every success, including creates and deletes. |
| 400 | Business-rule violations: invalid state transition, non-positive amount/price, duplicate plan feature, empty admin patch, self-delete, insufficient quantity/pool. |
| 401 | Missing/invalid/expired/revoked token; invalid login; duplicate plan title on create (bug); reset-token mismatch. |
| 403 | Valid non-admin token on an admin route; user refresh token on admin refresh. |
| 404 | Missing record, invalid foreign key reference, empty asset list, no-op asset update. |
| 409 | Duplicate admin email or instrument symbol. |
| 422 | Pydantic request validation. |
| 500 | Database/Redis/unexpected failures; missing deposit detail (bug). |

### A.7 Startup and operational dependencies

`app/main.py:31-47` runs a lifespan hook that:

1. Pings Redis. If Redis is unavailable, startup fails.
2. Starts three email worker threads.
3. Starts the subscription settlement worker (24-hour default interval).

Consequences for the admin frontend:

- The API will not start without Redis.
- Email sending is asynchronous and best-effort; a `200` from forgot-password means "queued", not "delivered".
- Expired subscriptions may be settled by a background worker while an admin is using the console. This is outside the admin routes but can change subscription and money-flow data.

---

## B. Complete Route Inventory

### B.1 Admin-related routes (34)

Auth legend: **Public** = no token; **Admin** = `require_admin`; **Any-auth** = any valid `USER` or `ADMIN` token.

| # | Method | Path | Auth | Group | Purpose |
|---:|---|---|---|---|---|
| 1 | POST | `/admin/register` | Public | Auth | Create an admin and return tokens. **Critical: unauthenticated.** |
| 2 | POST | `/admin/login` | Public | Auth | Exchange admin email/password for tokens. |
| 3 | GET | `/admin/me` | Admin | Auth | Return the current admin. |
| 4 | POST | `/admin/refresh` | Public | Auth | Exchange an admin refresh token for a new access token. |
| 5 | POST | `/admin/logout` | Admin | Auth | Revoke the current admin's access and refresh tokens. |
| 6 | POST | `/admin/forgot-password` | Public | Auth | Generate and email a password-reset OTP. |
| 7 | POST | `/admin/verify-otp` | Public | Auth | Verify the OTP and issue a reset token. |
| 8 | POST | `/admin/reset-password` | Public | Auth | Set a new password with a reset token. |
| 9 | GET | `/admin/users` | Admin | Users | Paginated user list. |
| 10 | GET | `/admin/users/{user_id}` | Admin | Users | Single user detail. |
| 11 | DELETE | `/admin/users/{user_id}` | Admin | Users | **Hard-delete** a user and cascaded financial data. |
| 12 | GET | `/admin/list` | Admin | Admins | Paginated admin list. |
| 13 | GET | `/admin/{admin_id}` | Admin | Admins | Single admin detail. |
| 14 | PATCH | `/admin/{admin_id}` | Admin | Admins | Update another admin's email/password and revoke sessions. |
| 15 | DELETE | `/admin/{admin_id}` | Admin | Admins | Delete another admin; self-delete rejected. |
| 16 | GET | `/wallet/admin/deposits` | Admin | Wallet | Paginated deposit list, optional status filter. |
| 17 | GET | `/wallet/admin/withdrawals` | Admin | Wallet | Paginated withdrawal list, optional status filter. |
| 18 | POST | `/wallet/deposits/{deposit_id}/confirm` | Admin | Wallet | Confirm a pending deposit and credit the wallet. |
| 19 | POST | `/wallet/deposits/{deposit_id}/reject` | Admin | Wallet | Reject a pending deposit. |
| 20 | POST | `/wallet/withdrawals/{withdrawal_id}/confirm` | Admin | Wallet | Confirm a pending withdrawal and consume locked funds. |
| 21 | POST | `/wallet/withdrawals/{withdrawal_id}/reject` | Admin | Wallet | Reject a pending withdrawal and unlock funds. |
| 22 | GET | `/plan` | Any-auth | Plans | Admin sees all plans; user sees active plans only. |
| 23 | POST | `/plan/create` | Admin | Plans | Create an active plan and its features. |
| 24 | POST | `/plan/update` | Admin | Plans | Replace plan fields and features. |
| 25 | GET | `/assets` | Any-auth | Assets | List all assets. |
| 26 | POST | `/assets` | Admin | Assets | Create an asset. |
| 27 | PUT | `/assets/{asset_id}` | Admin | Assets | Full replacement update. |
| 28 | DELETE | `/assets/{asset_id}` | Admin | Assets | **Hard-delete** an asset and cascaded financial data. |
| 29 | GET | `/instruments` | Admin | Instruments | Paginated instrument list, optional active filter. |
| 30 | POST | `/instruments` | Admin | Instruments | Create an instrument. |
| 31 | PUT | `/instruments/{instrument_id}` | Admin | Instruments | Partial update / activate / deactivate. |
| 32 | DELETE | `/instruments/{instrument_id}` | Admin | Instruments | Soft-delete by setting `is_active=false`. |
| 33 | POST | `/portfolio/admin/buy/{user_id}` | Admin | Trading | Buy an instrument on behalf of a user. |
| 34 | POST | `/portfolio/admin/sell/{user_id}` | Admin | Trading | Sell an instrument on behalf of a user. |

### B.2 Related non-admin routes (2, not part of the 34)

| ID | Method | Path | Auth | Why it matters |
|---|---|---|---|---|
| R1 | GET | `/wallet/deposit/{id}` | Any-auth | No admin check and no ownership check. Missing ID becomes a `500`. |
| R2 | GET | `/wallet/withdrawal/{id}` | Any-auth | No admin check and no ownership check. |

These are specified in Section C.9. They are **not** counted in the 34 admin-related routes and should not be used as admin detail endpoints without an authorization fix.

### B.3 Counts

| Auth category | Count |
|---|---:|
| Public admin-auth routes | 6 |
| Admin-only routes | 26 |
| Shared any-auth admin-relevant reads | 2 |
| **Total admin-related** | **34** |
| Related non-admin detail routes (appendix) | 2 |
| **Total paths documented** | **36** |

### B.4 Route ordering and path conflicts

FastAPI matches routes in registration order. The literal routes precede the dynamic ones where it matters:

- `GET /admin/me` (line 45) and `GET /admin/list` (line 143) are registered before `GET /admin/{admin_id}` (line 155), so they are not swallowed by the dynamic route.
- `/admin/users` and `/admin/users/{user_id}` are a distinct literal segment, so they do not conflict with `/admin/{admin_id}`.
- `/wallet/deposit/{id}` (singular) and `/wallet/deposits/{deposit_id}/confirm` (plural) do not conflict.
- `/wallet/withdrawal/{id}` (singular) and `/wallet/withdrawals/{withdrawal_id}/confirm` (plural) do not conflict.
- `GET /plan` is registered on the empty sub-path `/plan`, not `/plan/`. A request to `/plan/` may redirect or 404 depending on client behavior. **Inferred**
- `GET /assets` and `POST /assets` share the same path with different methods.
- There is no admin catch-all route.

### B.5 Capabilities that do not exist

The following are absent from the route table, despite some helpers existing in the service layer:

- Plan delete, activate, deactivate, or status toggle.
- Asset get-by-id or search.
- Deposit/withdrawal admin detail endpoints.
- Admin view of a user's wallet, deposits, withdrawals, subscriptions, or trades.
- User suspension, ban, role change, or password reset by an admin.
- Admin dashboard metrics or aggregate reporting.
- Category CRUD.
- Payment-method CRUD.
- Audit log or "acted by admin" fields.
- Bulk operations, CSV export, or idempotency keys.
- Search or sorting options beyond fixed SQL ordering.

---

## C. Detailed Endpoint Specifications

Each specification lists request, success response, errors, side effects, and integration notes. Example values are illustrative and synthetic.

### C.1 Admin authentication and account management

#### C.1.1 `POST /admin/register`

**Auth:** Public.
**Source:** `app/routes/admin_routes.py:24-30`, `app/services/admin_services.py:343-398`, `app/Models/auth_models.py:11-16`, `app/db/queries/admin_queries.py:9-18`.

**Request body**

```json
{
  "email": "new-admin@example.com",
  "password": "Password123"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `email` | string | Yes | Pydantic `EmailStr`; must be a valid email. |
| `password` | string | Yes | 8–100 characters. No complexity, breach, or reuse check. |

Unknown fields are ignored.

**Success — 200**

```json
{
  "id": 7,
  "message": "Admin created",
  "token": "<access-jwt>",
  "refresh_token": "<refresh-jwt>"
}
```

The new row receives the database default role `ADMIN` (`app/db/Migration/migrations/025_create_admin.sql`). The access token is stored in Redis for 7200 s and the refresh token for 604800 s. The password is bcrypt-hashed.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | first validation message | Invalid email, password length, missing field. |
| 409 | `Email already in use.` | Duplicate admin email (caught `IntegrityError`). |
| 500 | `<exception text>` | Any other DB/Redis failure. |

**Side effects and risks**

- **Critical:** no authentication, invitation, approval, email verification, or rate limit. Anyone can self-register as an admin and immediately use the tokens.
- The DB commit happens **before** Redis token storage. If Redis fails after the commit, the client receives `500` but the admin row may already exist. The rollback in the exception handler cannot undo a committed row.
- Registration and login both overwrite the single Redis access/refresh slot for that admin ID.
- Duplicate-email detection can be case-insensitive depending on the database collation; that detail is **inferred**.

**Frontend note:** do not expose this endpoint in a normal admin console. It should be removed from the public surface or moved behind a protected provisioning flow.

#### C.1.2 `POST /admin/login`

**Auth:** Public.
**Source:** `app/routes/admin_routes.py:33-42`, `app/services/admin_services.py:401-460`.

**Request**

```json
{
  "email": "admin@example.com",
  "password": "Password123"
}
```

Both required; password 8–100 characters.

**Success — 200**

```json
{
  "token": "<access-jwt>",
  "refresh_token": "<refresh-jwt>"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | first validation message | Invalid email or password length. |
| 401 | `Invalid credentials` | No admin row for the email. |
| 401 | `Password is incorrect` | Email exists but bcrypt check fails. |
| 500 | `<exception text>` | DB/Redis failure (including Redis unavailable). |

**Side effects and risks**

- The two different 401 messages enable account enumeration.
- No lockout, throttling, CAPTCHA, or MFA.
- A successful login overwrites the previous Redis access and refresh tokens, so any earlier session for that admin is invalidated.
- The login does not check that the stored role is `ADMIN`; it creates a token with the role from the row. Admin rows normally default to `ADMIN`, but a manually altered `USER` row could log in and then be rejected by `require_admin` on admin routes.
- If Redis is down, the service catches the error and returns `500`; the `conn.rollback()` in that path is called after no writes, so it is harmless but the cursor/connection variables are assumed to exist.

**Frontend note:** show a single generic "Unable to sign in" message to avoid leaking which field was wrong, even though the backend distinguishes them.

#### C.1.3 `GET /admin/me`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:45-51`, `app/services/admin_services.py:463-499`.

**Request:** no body. Optional `Authorization: Bearer <access_token>` required.

**Success — 200**

```json
{
  "id": 7,
  "email": "admin@example.com",
  "role": "ADMIN"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | `Not authenticated` / `Invalid token` / `Access token has expired` / `Token is not valid or has been revoked` | Auth failure. |
| 403 | `Admin privileges required.` | Valid non-admin token. |
| 404 | `Admin not found` | Token valid but admin row no longer exists. |
| 500 | `<exception text>` | DB failure. |

**Notes:** this is the canonical session probe after page load. It returns only `id`, `email`, and `role`; no name, timestamps, or permissions.

#### C.1.4 `POST /admin/refresh`

**Auth:** Public (the refresh token is the credential).
**Source:** `app/routes/admin_routes.py:54-60`, `app/services/admin_services.py:502-524`, `app/services/user_services.py:467-523`, `app/utils/jwt.py:44-62`.

**Request**

```json
{"token": "<admin-refresh-jwt>"}
```

`token` is required; any non-empty string passes Pydantic and is then decoded.

**Success — 200**

```json
{"token": "<new-access-jwt>"}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | first validation message | Missing `token`. |
| 401 | `Invalid token` | Malformed JWT. |
| 401 | `Refresh token has expired` | Expired JWT. |
| 403 | `Admin privileges required.` | JWT role is not `ADMIN`. |
| 401 | `Invalid refresh token` | Redis stored value differs, or admin row missing. |
| 500 | `<exception text>` | Redis/DB failure. |

**Side effects and risks**

- Validates the JWT type by using `ACCESS_REFRESH_SECRET_KEY` (via `decode_token(..., type="refresh")`).
- Checks the role claim **before** looking up Redis.
- Compares the presented token to the exact Redis value.
- Generates a new 2-hour access token and overwrites the Redis access slot. The refresh token is not rotated.
- Uses `generate_new_token(..., allow_admin=True)`, which also re-checks that the admin row still exists.
- Does not return a new refresh token. The client must keep the old one until it expires or the session is revoked.

#### C.1.5 `POST /admin/logout`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:63-69`, `app/services/admin_services.py:527-540`.

**Request:** no body; bearer token required.

**Success — 200**

```json
{"message": "Admin logged out"}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | auth details | Missing/invalid/revoked token. |
| 403 | `Admin privileges required.` | Non-admin token. |
| 500 | `<exception text>` | Redis failure while deleting keys. |

**Side effects:** deletes `user:{id}:access_token:ADMIN` and `user:{id}:refresh_token:ADMIN`. It does not delete OTP or reset-password keys. The current request has already passed auth, so it succeeds even though the token is deleted mid-request.

#### C.1.6 `POST /admin/forgot-password`

**Auth:** Public.
**Source:** `app/routes/admin_routes.py:72-78`, `app/services/admin_services.py:543-591`, `app/utils/otp.py`.

**Request**

```json
{"email": "admin@example.com"}
```

**Success — 200**

```json
{
  "message": "OTP sent to email",
  "timeout": 300
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | validation message | Invalid/missing email. |
| 404 | `Admin not found` | No admin row for the email. |
| 500 | `<exception text>` | DB, Redis, or template failure. |

**Side effects**

- Generates a random base32 OTP secret and a 6-digit TOTP.
- Stores the secret at `user:{id}:otp:ADMIN` with a 300-second TTL.
- Renders `templates/otp_mail.html` and **queues** an email with subject `Password Reset OTP`.
- The email queue is asynchronous. SMTP failures are logged after retries and are **not** returned to the caller; `200` does not guarantee delivery.
- No throttling: repeated calls overwrite the secret and queue more emails.

**Risk:** `404 Admin not found` allows admin-email enumeration. The response for an existing admin also differs from a non-existing one.

#### C.1.7 `POST /admin/verify-otp`

**Auth:** Public.
**Source:** `app/routes/admin_routes.py:81-87`, `app/services/admin_services.py:594-655`, `app/utils/otp.py:20-26`.

**Request**

```json
{
  "email": "admin@example.com",
  "otp": "123456"
}
```

`otp` must be exactly 6 characters (not necessarily digits at the Pydantic layer; TOTP verification enforces the value).

**Success — 200**

```json
{
  "message": "OTP verified successfully",
  "password_reset_token": "<reset-jwt>"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | validation message | Invalid email, missing/short/long OTP. |
| 404 | `Admin not found` | No admin row. |
| 400 | `OTP has expired or is invalid` | No OTP secret in Redis (expired or never requested). |
| 400 | `Invalid OTP` | TOTP mismatch. |
| 500 | `<exception text>` | DB/Redis failure. |

**Side effects**

- On success, deletes the OTP secret.
- Creates a password-reset JWT valid for 1 hour and stores it at `user:{id}:reset_password_token:ADMIN` with a 3600-second TTL.
- The reset token is a bearer credential. Anyone who obtains it can reset the password without the OTP.

**Notes:** `pyotp.TOTP.verify` is called with its default window, so only the current 30-second step is accepted; minor clock skew can cause a false `Invalid OTP`. **Inferred**

#### C.1.8 `POST /admin/reset-password`

**Auth:** Public (the reset token is the credential).
**Source:** `app/routes/admin_routes.py:90-96`, `app/services/admin_services.py:658-723`.

**Request**

```json
{
  "email": "admin@example.com",
  "new_password": "NewPassword456",
  "reset_token": "<reset-jwt>"
}
```

`new_password` is 8–100 characters. `reset_token` is required.

**Success — 200**

```json
{"message": "Password reset successfully"}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 422 | validation message | Invalid email, password length, missing token. |
| 404 | `Admin not found` | No admin row for `email`. |
| 401 | `Invalid token` / `Password reset token has expired` | JWT decode failure. |
| 401 | `Invalid password reset token for this admin` | JWT `user_id` does not match the email's admin ID. |
| 401 | `Invalid or expired password reset token` | Redis stored token differs or is missing. |
| 500 | `<exception text>` | DB/Redis failure. |

**Side effects**

- Re-hashes and updates `admins.password_hash`.
- Deletes the access token, refresh token, and reset token from Redis.
- Does **not** require the old password, does not check password history, and does not force re-login beyond revoking the stored session.

**Partial-failure risk:** the password commit happens before Redis revocation. If a Redis delete fails, the caller receives `500` while the password has already changed and some tokens may remain valid. The reset token may also remain until its TTL if a later delete fails.

### C.2 Admin user management

#### C.2.1 `GET /admin/users`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:104-113`, `app/services/admin_services.py:90-128`, `app/services/pagination_service.py`, `app/db/queries/user_queries.py:46-51`.

**Query parameters**

| Name | Type | Default | Constraints |
|---|---|---|---|
| `limit` | integer | 10 | 1–100 |
| `offset` | integer | 0 | ≥ 0 |

**Success — 200**

```json
[
  {
    "id": 42,
    "email": "user@example.com",
    "full_name": "Ada Example",
    "username": "ada",
    "role": "USER"
  }
]
```

`username` may be `null`. The SQL also selects `created_at`, but `AdminUserListItem` does not declare it, so it is omitted. Ordering is `created_at DESC`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 422 | e.g. `limit: Input should be less than or equal to 100` | Invalid paging. |
| 500 | `<exception text>` | DB failure. |

**Notes:** no total count, no search, no role filter, no sorting options. Offset paging can drift when users are inserted or deleted between pages.

#### C.2.2 `GET /admin/users/{user_id}`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:116-124`, `app/services/user_services.py:175-223`, `app/db/queries/user_queries.py:8-26`.

**Path parameter:** `user_id` integer; invalid values are `422`.

**Success — 200**

```json
{
  "id": 42,
  "country": "NG",
  "email": "user@example.com",
  "full_name": "Ada Example",
  "phone": "08000000000",
  "dob": "1990-01-01",
  "username": "ada",
  "address1": "1 Example Street",
  "address2": null,
  "city": "Lagos",
  "state": "Lagos",
  "zip": "100001",
  "role": "USER"
}
```

All address fields can be `null` when the user has no `user_addresses` row. `dob` is formatted as `YYYY-MM-DD` or `null`. `email`, `full_name`, `phone`, and `role` are required by the model; a database row missing them would produce a `500` serialization error.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `User not found` | No row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB/serialization failure. |

**Notes:** this endpoint exposes PII (email, phone, date of birth, full address). There is no field-level permission or masking. The query left-joins addresses; if multiple address rows exist for one user, `fetchone()` returns an arbitrary one. **Inferred**

#### C.2.3 `DELETE /admin/users/{user_id}`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:127-135`, `app/services/admin_services.py:131-174`, `app/db/queries/user_queries.py:40-44`.

**Path parameter:** `user_id` integer.

**Success — 200**

```json
{
  "message": "User deleted",
  "id": 42
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `User not found` | `DELETE` affected zero rows. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | FK/DB failure or Redis failure after commit. |

**Side effects — destructive and broad**

This is a **hard delete**, not a soft delete. Foreign keys with `ON DELETE CASCADE` remove:

- `user_addresses`
- `user_preferences`
- `wallet` (available and locked balances)
- `deposits`
- `withdrawal_destination`, and through it `crypto_destinations` / `bank_destinations`
- `withdrawals` (also cascaded directly by `user_id`)
- `subscriptions`
- `transactions`

In short, deleting a user erases their financial and trading history. `transaction.subscription_id` is `ON DELETE SET NULL`, but the transaction row itself is deleted because it also references `user_id` with cascade.

After commit, the user's access token is deleted from Redis. The refresh token is **not** deleted explicitly, but `/auth/refresh` re-checks that the user row exists and returns `401 Invalid refresh token`, so refresh is effectively blocked.

**Risks**

- No confirmation token, reason field, audit record, or soft-delete/recovery path.
- No protection against deleting a user with funds, open positions, or pending withdrawals. The cascade removes the evidence.
- If Redis deletion fails after the DB commit, the API returns `500` even though the user is gone, and the access token may remain until its TTL.
- Any admin can delete any user, including themselves if the user ID happens to belong to an admin? Admin IDs live in a separate `admins` table, so `users` and `admins` IDs are independent; this route only touches `users`.

### C.3 Admin account management

#### C.3.1 `GET /admin/list`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:143-152`, `app/services/admin_services.py:177-213`, `app/db/queries/admin_queries.py:39-44`.

**Query parameters:** `limit` 1–100 (default 10), `offset` ≥ 0 (default 0).

**Success — 200**

```json
[
  {
    "id": 7,
    "email": "admin@example.com",
    "role": "ADMIN"
  }
]
```

Ordering: `created_at DESC`. The SQL selects `created_at` but `AdminPublic` omits it.

**Errors:** auth 401/403; paging `422`; DB `500`.

**Notes:** no total, search, or filter. Because registration is public, this list can grow without an invitation workflow.

#### C.3.2 `GET /admin/{admin_id}`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:155-163`, `app/services/admin_services.py:463-499`.

**Path parameter:** `admin_id` integer. Literal `/admin/me` and `/admin/list` are registered earlier and win over this route.

**Success — 200**

```json
{
  "id": 7,
  "email": "admin@example.com",
  "role": "ADMIN"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Admin not found` | No row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Notes:** any admin can read any other admin's email. There is no "self only" restriction and no permissions field.

#### C.3.3 `PATCH /admin/{admin_id}`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:166-175`, `app/services/admin_services.py:216-282`, `app/db/queries/admin_queries.py:25-31`.

**Request body**

```json
{
  "email": "renamed-admin@example.com",
  "password": "NewPassword456"
}
```

Both fields are optional, but at least one must be non-null.

| Field | Type | Constraints |
|---|---|---|
| `email` | string or null | `EmailStr` when present. |
| `password` | string or null | 8–100 characters when present. |

An empty object `{}` or `{"email":null,"password":null}` is handled as `400 Nothing to update.`; a present but empty password is a `422`.

**Success — 200**

```json
{
  "id": 7,
  "email": "renamed-admin@example.com",
  "role": "ADMIN"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Nothing to update.` | Both fields null/omitted. |
| 404 | `Admin not found` | Target admin missing. |
| 409 | `Email already in use.` | Duplicate email integrity error. |
| 422 | validation message | Invalid email/password. |
| 500 | `<exception text>` | DB/Redis failure. |

**Side effects**

- Updates `email` and/or `password_hash`; the role is never changed.
- On success, deletes the target admin's access and refresh tokens from Redis. This means an admin can update another admin's password and immediately revoke their session.
- If only the email is changed and it is identical to the current value, MySQL may report zero changed rows; the service does not check rowcount and still returns `200`.
- Commit happens before Redis revocation. A Redis failure returns `500` after the DB change is already durable.

**Security note:** there is no restriction preventing an admin from changing another admin's email/password. Combined with public registration, any admin can take over any other admin account. Self-service password changes by an admin are not a separate route; this endpoint is used for that too.

#### C.3.4 `DELETE /admin/{admin_id}`

**Auth:** Admin.
**Source:** `app/routes/admin_routes.py:178-188`, `app/services/admin_services.py:285-335`, `app/db/queries/admin_queries.py:20-23`.

**Path parameter:** `admin_id` integer.

**Success — 200**

```json
{
  "message": "Admin deleted",
  "id": 7
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Admins cannot delete themselves.` | `admin_id == current user_id`. |
| 404 | `Admin not found` | No row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB/Redis failure. |

**Side effects:** hard-deletes the `admins` row, then deletes that admin's access and refresh tokens from Redis. There are no foreign keys from other tables to `admins`, so no business history is cascaded. The deleted admin's audit identity, if it existed anywhere, would be lost; in practice there is no audit table.

**Risk:** any admin can delete any other admin (except themselves). There is no last-admin protection; if the only admin is deleted by another admin or by a database operator, the system has no admin left until someone registers again (which is public, so recovery is trivial but insecure).

### C.4 Deposit and withdrawal administration

#### C.4.1 `GET /wallet/admin/deposits`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:208-225`, `app/services/wallet_services.py:504-536`, `app/utils/wallet/deposits.py:50-58`, `app/db/queries/deposits_queries.py:97-118`.

**Query parameters**

| Name | Type | Default | Constraints |
|---|---|---|---|
| `status` | enum `pending` / `confirmed` / `rejected` | none | Invalid value → `422`. |
| `limit` | integer | 10 | 1–100 |
| `offset` | integer | 0 | ≥ 0 |

The status filter is applied with `WHERE (%s IS NULL OR d.status = %s)`.

**Success — 200**

```json
[
  {
    "id": 101,
    "user_id": 42,
    "payment_method": "Crypto",
    "asset": "Tether",
    "amount": "100.00000000",
    "status": "pending",
    "date": "2026-10-23T10:15:00"
  }
]
```

`payment_method` is the payment-method **name**, `asset` is the asset **name**, and `amount` is the raw `DECIMAL(20,8)` value (so it often has eight decimal places). This differs from the detail/confirm response, which quantizes to two decimals. `status` is a plain string here, not an enum, so the model does not enforce the allowed values on output.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 422 | validation message | Invalid status/limit/offset. |
| 500 | `<exception text>` | DB failure. |

**Notes:** ordered `created_at DESC`. No total, no user filter, no date range, no search. Empty result is `[]`.

#### C.4.2 `GET /wallet/admin/withdrawals`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:228-245`, `app/services/wallet_services.py:539-571`, `app/utils/wallet/withdraws.py:180-187`, `app/db/queries/withdraw_queries.py:126-144`.

**Query parameters:** same shape as deposits: `status` (`pending`/`confirmed`/`rejected`), `limit` 1–100 (default 10), `offset` ≥ 0.

**Success — 200**

```json
[
  {
    "id": 201,
    "user_id": 42,
    "amount": "40.00000000",
    "status": "pending",
    "created_at": "2026-10-23T10:20:00",
    "asset_symbol": "USDT",
    "asset_name": "Tether",
    "destination_type": "BANK"
  }
]
```

`amount` is raw `DECIMAL(20,8)`. The list does **not** include the destination label, account number, or address; those appear only in the detail route (appendix) and in the confirm/reject response.

**Errors:** auth 401/403; `422` for invalid status/paging; `500` DB. Empty result `[]`.

**Notes:** ordered `created_at DESC`. No total, user filter, date range, destination filter, or search.

#### C.4.3 `POST /wallet/deposits/{deposit_id}/confirm`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:77-90`, `app/services/wallet_services.py:116-157`, `app/utils/wallet/deposits.py:81-92`, `app/utils/wallet/wallet.py:52-60`.

**Path parameter:** `deposit_id` integer.

**Request body:** none.

**Success — 200**

```json
{
  "id": 101,
  "amount": "100.00",
  "status": "confirmed",
  "created_at": "2026-10-23T10:15:00",
  "confirmed_at": "2026-10-23T10:30:00",
  "asset_id": 1,
  "asset_symbol": "USDT",
  "asset_name": "Tether",
  "payment_method_id": 1,
  "payment_method_name": "Crypto",
  "payment_method_type": "CRYPTO",
  "bank_name": null,
  "account_name": null,
  "account_number": null
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Deposit is not pending or does not exist.` | `UPDATE ... WHERE status='pending'` affected zero rows. |
| 404 | `Deposit not found.` | The status update succeeded but the joined detail fetch returned no row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | Any other DB failure. |

**Side effects**

1. `UPDATE deposits SET status='confirmed', confirmed_at=<UTC now> WHERE id=? AND status='pending'`.
2. Fetch the deposit joined with asset and payment method.
3. Quantize the stored amount to **2 decimal places** and add it to `wallet.available` for the deposit's `user_id`.
4. Commit.

The wallet credit uses `_credit_available`, which executes an `UPDATE` but **does not check rowcount**. If the user has no wallet row, the deposit still becomes `confirmed` and the commit succeeds, but no funds are credited.

**Idempotency and concurrency:** a second confirm returns `400` because the status is no longer `pending`. The conditional `UPDATE` plus InnoDB row locking should make concurrent confirms safe: one wins, the other sees zero rows. **Inferred.**

**Money precision:** the deposit is stored as `DECIMAL(20,8)`, but the wallet is credited after `quantize(Decimal("0.01"))`. Sub-cent precision is lost (rounding mode is the `decimal` context default, `ROUND_HALF_EVEN`). The response also shows the two-decimal amount. **Confirmed code; exact rounding behavior inferred.**

#### C.4.4 `POST /wallet/deposits/{deposit_id}/reject`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:93-106`, `app/services/wallet_services.py:215-247`, `app/utils/wallet/deposits.py:95-106`.

**Path parameter:** `deposit_id` integer. No body.

**Success — 200:** same `DepositFundsResponse` shape as confirm, with `"status":"rejected"` and `"confirmed_at":null`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Deposit is not pending or does not exist.` | Not pending or missing. |
| 404 | `Deposit not found.` | Status update succeeded but detail fetch failed. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Side effects:** only a status change. No wallet credit or debit. The amount is not refunded because a pending deposit was never credited. A second reject returns `400`.

#### C.4.5 `POST /wallet/withdrawals/{withdrawal_id}/confirm`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:248-261`, `app/services/wallet_services.py:574-611`, `app/utils/wallet/withdraws.py:190-201`, `app/utils/wallet/wallet.py:103-111`.

**Path parameter:** `withdrawal_id` integer. No body.

**Success — 200**

```json
{
  "id": 201,
  "amount": "40.00",
  "status": "confirmed",
  "created_at": "2026-10-23T10:20:00",
  "confirmed_at": "2026-10-23T10:35:00",
  "asset_id": 1,
  "asset_symbol": "USDT",
  "asset_name": "Tether",
  "destination_id": 5,
  "destination_label": "My bank",
  "destination_type": "BANK",
  "address": null,
  "bank_name": "Example Bank",
  "account_name": "Ada Example",
  "account_number": "0123456789"
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Withdrawal is not pending or does not exist.` | Not pending or missing. |
| 404 | `Withdraw record '<id>' not found.` | Status update succeeded but detail fetch failed. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Side effects**

1. `UPDATE withdrawals SET status='confirmed', confirmed_at=<UTC now> WHERE id=? AND status='pending'`.
2. Fetch the withdrawal with asset and destination details.
3. `UPDATE wallet SET locked = locked - amount WHERE user_id=?`.
4. Commit.

The available balance is not changed at confirm time; it was reduced when the withdrawal was submitted. The locked balance is consumed. `_consume_lock_funds` **does not check rowcount** and has no `locked >= amount` guard, so a data inconsistency or concurrent operation can drive `locked` negative.

**Idempotency:** a second confirm returns `400`. Concurrent confirm/reject is serialized by the conditional status update and InnoDB locking. **Inferred.**

#### C.4.6 `POST /wallet/withdrawals/{withdrawal_id}/reject`

**Auth:** Admin.
**Source:** `app/routes/wallet_routes.py:264-277`, `app/services/wallet_services.py:614-649`, `app/utils/wallet/withdraws.py:204-215`, `app/utils/wallet/wallet.py:92-100`.

**Path parameter:** `withdrawal_id` integer. No body.

**Success — 200:** same `WithdrawFundsResponse` shape as confirm, with `"status":"rejected"` and `"confirmed_at":null`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 400 | `Withdrawal is not pending or does not exist.` | Not pending or missing. |
| 404 | `Withdraw record '<id>' not found.` | Status update succeeded but detail fetch failed. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Side effects**

1. Set status to `rejected`.
2. Fetch the withdrawal.
3. `UPDATE wallet SET available = available + amount, locked = locked - amount WHERE user_id=?`.
4. Commit.

The funds return to available. `_unlock_funds` also has **no rowcount or non-negative guard**. A second reject returns `400`.

**Important:** the wallet mutation uses the raw stored `amount`, while the response shows a two-decimal quantized value. If the stored amount has more than two decimals, the UI's displayed amount will not exactly match the wallet delta.

### C.5 Plans

#### C.5.1 `GET /plan`

**Auth:** Any authenticated user (shared).
**Source:** `app/routes/plan_routes.py:25-35`, `app/services/plan_services.py:33-68`, `app/utils/plans/plan_helpers.py:136-169`, `app/utils/plans/responses.py:82-110`.

**Request:** no body. Bearer token required.

**Behavior**

- `ADMIN`: returns **all** plans, including `INACTIVE`.
- `USER`: returns only `ACTIVE` plans.

**Success — 200**

```json
{
  "plans": [
    {
      "id": 3,
      "title": "Growth",
      "min_amount": "5000.00",
      "duration": 30,
      "roi": "12.00",
      "risk_management": "STANDARD",
      "description": "Diversified growth plan.",
      "status": "ACTIVE",
      "features": ["Forex", "Crypto"],
      "created_at": "2026-10-01T09:00:00",
      "updated_at": "2026-10-01T09:00:00"
    }
  ]
}
```

Ordering: `created_at DESC`. `min_amount` is quantized to two decimals; `roi` is the raw `DECIMAL(5,2)`. `features` is ordered by feature `id`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | auth details | Missing/invalid token. |
| 500 | `<exception text>` | DB failure. |

**Notes:** empty plans returns `{"plans":[]}`. The endpoint has no pagination, status filter, or search. Because an admin sees inactive plans, the admin UI can display them but cannot reactivate them through the API.

#### C.5.2 `POST /plan/create`

**Auth:** Admin.
**Source:** `app/routes/plan_routes.py:38-52`, `app/services/plan_services.py:71-132`, `app/utils/plans/plan_helpers.py:104-110,123-133,217-253`, `app/Models/plans_models.py:27-49`.

**Request body**

```json
{
  "plan": {
    "title": "Growth",
    "min_amount": "5000",
    "duration": 30,
    "roi": "12",
    "risk_management": "STANDARD",
    "description": "Diversified growth plan."
  },
  "features": ["Forex", "Crypto"]
}
```

| Field | Type | Required | Constraints / notes |
|---|---|---|---|
| `plan.title` | string | Yes | No length constraint in the model; database column is `VARCHAR(100) UNIQUE`. |
| `plan.min_amount` | decimal | Yes | Must be `> 0`. |
| `plan.duration` | integer | Yes | Must be `> 0`; interpreted as days. |
| `plan.roi` | decimal | Yes | Must be `> 0`; database is `DECIMAL(5,2)`. |
| `plan.risk_management` | enum | Yes | `STANDARD`, `ADVANCED_HEDGING`, `TAILORED_MULTI_LAYER`. |
| `plan.description` | string | Yes | Database `TEXT`; empty string allowed by the model. |
| `features` | array of strings | Yes | May be empty. Duplicates within the array are rejected one by one. |

**Success — 200:** a `PlanResponse` with the newly created `id`, `status:"ACTIVE"`, features, and timestamps. The insert always sets `status='ACTIVE'`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Admin not found` | The JWT admin ID has no `admins` row. |
| **401** | **`Plan title already used.`** | **Duplicate title. This is a bug: it is not an auth failure.** |
| 400 | `Minimum amount must be greater than zero.` | `min_amount <= 0`. |
| 400 | `ROI must be greater than zero.` | `roi <= 0`. |
| 400 | `Duration must be greater than zero.` | `duration <= 0`. |
| 400 | `Feature already exists.` | Duplicate feature, including duplicates within the request array. |
| 422 | validation message | Missing/invalid enum, non-numeric decimal, missing field. |
| 500 | `<exception text>` | DB failure, e.g. overlong title. |

**Transaction behavior:** all inserts happen in one transaction. A duplicate feature or validation failure rolls back the plan and all features. The duplicate-title check is a separate `SELECT`, so two concurrent creates can still race and one may hit the database unique constraint as a generic `500`.

**Critical frontend note:** do not run a global "on 401, refresh/logout" handler without excluding this case. The session is valid; the error means duplicate title. Ideally the backend changes this to `409`, but the frontend must cope with `401` + `Plan title already used.` today.

#### C.5.3 `POST /plan/update`

**Auth:** Admin.
**Source:** `app/routes/plan_routes.py:55-69`, `app/services/plan_services.py:135-197`, `app/utils/plans/plan_helpers.py:196-210,261-281,373-377`.

**Request body**

```json
{
  "plan_id": 3,
  "plan": {
    "title": "Growth Plus",
    "min_amount": "6000",
    "duration": 45,
    "roi": "14",
    "risk_management": "ADVANCED_HEDGING",
    "description": "Updated description."
  },
  "features": ["Forex", "Metals"]
}
```

All `plan` fields are required and replace the existing values. `features` **replaces** the entire feature set: existing features are deleted, then the supplied list is inserted. An empty list removes all features.

**Success — 200:** updated `PlanResponse`. The plan `status` is not changed by this route; it remains whatever it was.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Plan not found.` | No plan with `plan_id`. |
| 400 | `A plan with this title already exists.` | Title used by another plan. |
| 400 | `Minimum amount must be greater than zero.` / `ROI ...` / `Duration ...` | Non-positive values. |
| 400 | `Feature already exists.` | Duplicate feature. |
| 422 | validation message | Missing/invalid fields. |
| 500 | `<exception text>` | DB failure. |

**Notes**

- Unlike create, duplicate title is correctly `400`.
- The full replacement means a client must send every field, not a patch. Fetch the current plan first if the form is partial.
- Existing subscriptions reference the plan by ID; changing `min_amount`, `roi`, or `duration` does not rewrite existing subscription terms.
- There is no optimistic concurrency check (no `updated_at` precondition). Two admins editing the same plan can overwrite each other.

### C.6 Assets

#### C.6.1 `GET /assets`

**Auth:** Any authenticated user (shared).
**Source:** `app/routes/asset_routes.py:26-37`, `app/services/asset_services.py:26-50`, `app/utils/wallet/assets.py:23-37`, `app/db/queries/asset_queries.py:7-11`.

**Success — 200**

```json
[
  {
    "id": 1,
    "symbol": "USDT",
    "name": "Tether",
    "address": null,
    "is_active": true,
    "created_at": "2026-10-01T09:00:00",
    "updated_at": "2026-10-01T09:00:00"
  }
]
```

All assets are returned, including inactive ones. Ordering is `id ASC`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | auth details | Missing/invalid token. |
| **404** | **`No assets found.`** | **The table is empty. This differs from every other list endpoint.** |
| 500 | `<exception text>` | DB failure. |

**Notes:** no pagination, filter, or search. The `404` for an empty table is easy to mishandle in a list UI; treat it as an empty list only if that matches the deployment's expectations, and surface the discrepancy to the backend team.

#### C.6.2 `POST /assets`

**Auth:** Admin.
**Source:** `app/routes/asset_routes.py:40-54`, `app/services/asset_services.py:53-96`, `app/Models/asset_models.py:6-11`, `app/db/queries/asset_queries.py:13-20`.

**Request body**

```json
{
  "symbol": "USDT",
  "name": "Tether",
  "address": "0x0000000000000000000000000000000000000000",
  "is_active": true
}
```

All fields except `address` are required. There is no model-level length or uniqueness validation.

**Success — 200:** `AssetResponse` with the new `id` and timestamps.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 422 | validation message | Missing field or wrong type. |
| 500 | `<exception text>` | DB failure (including a duplicate if a future unique constraint is added). |

**Side effects and risks**

- `assets.symbol` has **no unique constraint** in the reviewed migrations (`012_create_assets.sql`). Duplicate symbols are accepted.
- There is no address format validation, chain validation, or symbol normalization.
- The insert commits before the response is built; a post-commit read failure would surface as `500` with the row persisted.
- An asset can be created inactive and still be referenced by deposits/withdrawals? Deposit validation only checks that the asset exists, not that it is active (`_validate_asset` uses `GET_ASSET` with no `is_active` filter). This is a data-quality risk.

#### C.6.3 `PUT /assets/{asset_id}`

**Auth:** Admin.
**Source:** `app/routes/asset_routes.py:57-73`, `app/services/asset_services.py:99-151`, `app/Models/asset_models.py:13-17`, `app/db/queries/asset_queries.py:22-30`.

**Path parameter:** `asset_id` integer.

**Request body:** same four fields as create, **all required**. This is a full replacement, not a partial patch.

**Success — 200:** updated `AssetResponse`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| **404** | **`Asset '<id>' not found.`** | **No row, or the update changed no values.** |
| 422 | validation message | Missing field or wrong type. |
| 500 | `<exception text>` | DB failure. |

**Critical quirk:** the service checks `cursor.rowcount == 0` after the `UPDATE`. MySQL reports zero changed rows when the new values are identical to the old ones, so a no-op update returns `404 Asset '<id>' not found.` even though the asset exists. The frontend should avoid sending an unchanged form or should treat this `404` as a possible no-op.

There is no unique-symbol check, no address validation, and no optimistic locking. Updating an asset's symbol does not update existing deposits/withdrawals, which reference it by ID.

#### C.6.4 `DELETE /assets/{asset_id}`

**Auth:** Admin.
**Source:** `app/routes/asset_routes.py:76-90`, `app/services/asset_services.py:154-192`, `app/db/queries/asset_queries.py:32-35`.

**Path parameter:** `asset_id` integer.

**Success — 200**

```json
{
  "id": 1,
  "message": "Asset deleted successfully."
}
```

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Asset '<id>' not found.` | No row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | FK/DB failure. |

**Side effects — destructive**

This is a **hard delete**. Foreign keys cascade:

- `deposits.asset_id` → deposits are deleted.
- `withdrawals.asset_id` → withdrawals are deleted.
- `crypto_destinations.asset_id` → crypto destination detail rows are deleted. The parent `withdrawal_destination` row remains, potentially leaving a CRYPTO destination with no address/asset; any withdrawals referencing it may also be deleted by the asset cascade.

Deleting an asset therefore removes financial records that used it. There is no soft-delete flag, dependency check, or warning. The response says "deleted successfully" without counting affected rows.

**Recommendation:** do not expose this to non-technical operators without a dependency check and a typed confirmation. Prefer deactivating the asset (`PUT` with `is_active:false`) once a soft-delete path exists; currently `is_active` only affects display and some asset-list consumers, not deposit validation.

### C.7 Instruments

#### C.7.1 `GET /instruments`

**Auth:** Admin.
**Source:** `app/routes/instrument_routes.py:25-39`, `app/services/instrument_services.py:43-80`, `app/utils/instruments.py:53-64`, `app/db/queries/instrument_queries.py:50-67`.

**Query parameters**

| Name | Type | Default | Constraints |
|---|---|---|---|
| `is_active` | boolean | none | `true`/`false`; omitted means all. |
| `limit` | integer | 10 | 1–100 |
| `offset` | integer | 0 | ≥ 0 |

**Success — 200**

```json
[
  {
    "id": 9,
    "symbol": "EURUSD",
    "name": "EUR/USD",
    "category_id": 1,
    "category": "Forex",
    "current_price": "1.08500000",
    "is_active": true,
    "created_at": "2026-10-01T09:00:00",
    "updated_at": "2026-10-01T09:00:00"
  }
]
```

Ordering: `created_at DESC`. Inactive instruments are included unless `is_active=false` (or `true`) is supplied. Empty result is `[]`.

**Errors:** auth 401/403; paging/filter `422`; DB `500`.

**Notes:** no total, symbol search, category filter, or price range. This is the only instrument read route and it is admin-only; there is no public instrument list in the reviewed route table.

#### C.7.2 `POST /instruments`

**Auth:** Admin.
**Source:** `app/routes/instrument_routes.py:42-53`, `app/services/instrument_services.py:83-134`, `app/utils/instruments.py:11-50`, `app/Models/instrument_models.py:7-12`.

**Request body**

```json
{
  "symbol": "EURUSD",
  "name": "EUR/USD",
  "category_id": 1,
  "current_price": "1.085"
}
```

| Field | Constraints |
|---|---|
| `symbol` | 1–50 characters. Must be unique (checked and enforced by a unique key). |
| `name` | 1–255 characters. |
| `category_id` | Must reference an existing `categories` row. |
| `current_price` | Must be `> 0`. |

**Success — 200:** `InstrumentResponse`. `is_active` defaults to `true` in the database.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Category not found.` | Bad `category_id`. |
| 400 | `Current price must be greater than zero.` | `<= 0` or null. |
| 409 | `Instrument symbol already in use.` | Duplicate symbol. |
| 422 | validation message | Missing/overlong fields, bad decimal. |
| 500 | `<exception text>` | DB failure. |

**Side effects:** inserts an instrument; no transaction history is created. Symbol comparison uses the database collation, so case sensitivity depends on the schema. **Inferred**

#### C.7.3 `PUT /instruments/{instrument_id}`

**Auth:** Admin.
**Source:** `app/routes/instrument_routes.py:56-69`, `app/services/instrument_services.py:137-200`, `app/utils/instruments.py:11-50`, `app/Models/instrument_models.py:14-19`.

**Path parameter:** `instrument_id` integer.

**Request body:** all fields optional:

```json
{
  "symbol": "EURUSD",
  "name": "Euro / US Dollar",
  "category_id": 1,
  "current_price": "1.09",
  "is_active": false
}
```

The service merges supplied values with the current row; omitted fields are preserved. This is the only way to reactivate an instrument.

**Success — 200:** updated `InstrumentResponse`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Instrument not found.` | No row. |
| 404 | `Category not found.` | Supplied category does not exist. |
| 400 | `Current price must be greater than zero.` | Supplied price `<= 0`. |
| 409 | `Instrument symbol already in use.` | Supplied symbol used by another instrument. |
| 422 | validation message | Overlong strings, bad decimal, etc. |
| 500 | `<exception text>` | DB failure. |

**Notes**

- A no-op update returns `200` (unlike assets) because there is no rowcount check.
- Deactivating an instrument (`is_active:false`) prevents new buys but **not** sells: the sell path looks up instruments with `active_only=False` so holders can exit. Holdings and trade history remain visible.
- Price changes affect future trades only; existing transactions store the execution price.
- There is no price history, price timestamp, or market-data integration. `current_price` is a manually maintained value.

#### C.7.4 `DELETE /instruments/{instrument_id}`

**Auth:** Admin.
**Source:** `app/routes/instrument_routes.py:72-84`, `app/services/instrument_services.py:203-238`, `app/db/queries/instrument_queries.py:106-110`.

**Path parameter:** `instrument_id` integer.

**Success — 200:** the instrument with `"is_active": false`.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `Instrument not found.` | No row. |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Side effects:** soft delete only: `UPDATE instruments SET is_active=FALSE WHERE id=?`. Trade history and foreign-key relationships are preserved. The operation is idempotent: deleting an already-inactive instrument returns it as-is with `200`. There is no separate "hard delete" API; the `transactions.instrument_id` cascade is only relevant if someone deletes rows directly in the database.

### C.8 Admin trading

Admin trading operates on a **user's subscription pool**, not on the user's wallet available balance. This is a common integration mistake. A user must have an active subscription with enough `pool` for a buy. Wallet deposits are separate from subscription pools.

#### C.8.1 `POST /portfolio/admin/buy/{user_id}`

**Auth:** Admin.
**Source:** `app/routes/portfolio_routes.py:40-55`, `app/services/portfolio_services.py:28-93`, `app/utils/portfolio_helpers.py:41-88`, `app/utils/plans/subscription_helpers.py:231-279`, `app/db/queries/subscription_queries.py:106-117`, `app/db/queries/transaction_queries.py:1-5`.

**Path parameter:** `user_id` integer — the user on whose behalf the trade is placed.

**Request body**

```json
{
  "instrument_id": 9,
  "quantity": "2",
  "subscription_id": 55
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `instrument_id` | integer | Yes | Must be an **active** instrument for buy. |
| `quantity` | decimal | Yes | Must be `> 0`. |
| `subscription_id` | integer | Yes | Must be an `ACTIVE` subscription **owned by `user_id`**. |

**Success — 200**

```json
{
  "message": "Instrument purchased successfully.",
  "transaction_id": 501
}
```

**Validation order**

1. User exists (`404 User not found.`).
2. Instrument exists and is active (`404 Instrument not found.`).
3. Quantity positive (`400 Quantity must be greater than zero.`).
4. Subscription belongs to the user and is active (`404 Active subscription not found.`).
5. Pool debit with `pool >= cost` (`400 Insufficient subscription pool.`).
6. Insert BUY transaction at the instrument's current price.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `User not found.` | Bad `user_id`. |
| 404 | `Instrument not found.` | Missing or inactive instrument. |
| 400 | `Quantity must be greater than zero.` | `quantity <= 0`. |
| 404 | `Active subscription not found.` | Subscription missing, not active, or not owned by the user. |
| 400 | `Insufficient subscription pool.` | Cost exceeds the subscription's pool. |
| 422 | validation message | Missing/bad fields. |
| 500 | `<exception text>` | DB failure. |

**Side effects**

- Debits `subscriptions.pool` by `current_price * quantity`.
- Inserts a `transactions` row: `user_id`, `instrument_id`, `subscription_id`, `type='BUY'`, `quantity`, `price`, `executed_at=now`.
- Does **not** touch `wallet.available` or `wallet.locked`.
- Does not record which admin placed the trade.
- No idempotency key: retrying a successful request creates another trade and debits the pool again.

**Concurrency:** the pool debit is a conditional `UPDATE ... WHERE pool >= amount`, so two simultaneous buys cannot overdraw the pool at the database level; one will get `Insufficient subscription pool.` **Inferred.** The price is read before the update and is not locked, so a concurrent instrument price update can result in a trade at the older price.

#### C.8.2 `POST /portfolio/admin/sell/{user_id}`

**Auth:** Admin.
**Source:** `app/routes/portfolio_routes.py:58-73`, `app/services/portfolio_services.py:96-178`, `app/utils/portfolio_helpers.py:41-106`, `app/utils/plans/subscription_helpers.py:201-217,231-257`, `app/db/queries/transaction_queries.py:6-9`.

**Path parameter:** `user_id` integer.

**Request body:** same shape as buy.

**Success — 200**

```json
{
  "message": "Instrument sold successfully.",
  "transaction_id": 502
}
```

**Validation order**

1. User exists.
2. Instrument exists; **inactive instruments are allowed** for sell.
3. Quantity positive.
4. Subscription is active and owned by the user.
5. Net quantity under **that subscription and instrument** must cover the sell (`400 Insufficient quantity.`).
6. Insert SELL at current price and credit the subscription pool with proceeds.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401/403 | auth details | Auth/role failure. |
| 404 | `User not found.` | Bad `user_id`. |
| 404 | `Instrument not found.` | Missing instrument. |
| 400 | `Quantity must be greater than zero.` | `quantity <= 0`. |
| 404 | `Active subscription not found.` | Subscription not active/owned. |
| 400 | `Insufficient quantity.` | Sell exceeds net quantity in that subscription. |
| 422 | validation message | Missing/bad fields. |
| 500 | `<exception text>` | DB failure. |

**Side effects**

- Inserts a `SELL` transaction.
- Credits `subscriptions.pool` by `current_price * quantity`.
- Does not move money back to the wallet; proceeds remain in the subscription pool.
- No admin audit trail and no idempotency.

**Concurrency risk:** the net-quantity check is a read followed by an insert, with no row lock or database constraint. Two simultaneous sells can both pass the check and oversell the subscription's position. **Inferred.** This should be tested and fixed before high-volume use.

### C.9 Related non-admin detail routes (appendix)

These are **not** part of the 34-route admin inventory. They are documented because an admin UI may try to use them for deposit/withdrawal detail and because their authorization is unsafe.

#### C.9.1 `GET /wallet/deposit/{id}`

**Auth:** Any authenticated user. **No admin check. No ownership check.**
**Source:** `app/routes/wallet_routes.py:109-120`, `app/services/wallet_services.py:191-212`, `app/utils/wallet/deposits.py:61-76`.

**Path parameter:** `id` integer.

**Success — 200:** `DepositFundsResponse` (same shape as C.4.3), with the deposit's asset, payment method, and bank details.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | auth details | Missing/invalid token. |
| **500** | **`404: Deposit not found.`** | **Missing record is raised as `HTTPException(404)`, caught by the generic `except Exception`, and re-raised as `500`.** |
| 422 | path validation message | Non-integer ID. |
| 500 | other exception text | DB failure. |

**Security:** any logged-in user can read any deposit by ID, including another user's amount, asset, payment method, and bank account details when present. This is an IDOR. Do not build the admin detail view on this route until ownership/admin checks are added.

#### C.9.2 `GET /wallet/withdrawal/{id}`

**Auth:** Any authenticated user. **No admin check. No ownership check.**
**Source:** `app/routes/wallet_routes.py:159-170`, `app/services/wallet_services.py:373-399`, `app/utils/wallet/withdraws.py:149-163`.

**Path parameter:** `id` integer.

**Success — 200:** `WithdrawFundsResponse` (same shape as C.4.5), including destination label, address, bank name, account name, and account number.

**Errors**

| Status | `detail` | Condition |
|---:|---|---|
| 401 | auth details | Missing/invalid token. |
| 404 | `Withdraw record '<id>' not found.` | Missing record (HTTPException is preserved by the service). |
| 422 | path validation message | Non-integer ID. |
| 500 | `<exception text>` | DB failure. |

**Security:** same IDOR as deposits. It also exposes full payout destination details. Do not use it in an admin UI without a server-side authorization fix.

---

## D. Shared Models and Enums

This section is the type reference for the payloads above. All models are Pydantic v2 unless marked otherwise.

### D.1 Auth and account models

| Model | Fields | Notes |
|---|---|---|
| `Admin` | `email: EmailStr`, `password: str` (8–100) | Request model for registration. |
| `AdminPublic` | `id: int`, `email: str`, `role: UserRole` | Response for admin detail/list. `email` is a plain string here, not re-validated as `EmailStr`. |
| `AdminUserListItem` | `id: int`, `email: EmailStr`, `full_name: str`, `username: str \| null`, `role: UserRole` | User list item. `created_at` is intentionally not exposed. |
| `AdminUpdateRequest` | `email: EmailStr \| null`, `password: str \| null` (8–100) | At least one must be non-null at the service layer. |
| `LoginUserRequest` | `email: EmailStr`, `password: str` (8–100) | Shared by user and admin login. |
| `RefreshTokenRequest` | `token: str` | No length or format validation; decoded later. |
| `ForgotPasswordRequest` | `email: EmailStr` | Admin forgot-password. |
| `VerifyOTPRequest` | `email: EmailStr`, `otp: str` (exactly 6 chars) | OTP is a string, not an integer. |
| `ResetPasswordRequest` | `email: EmailStr`, `new_password: str` (8–100), `reset_token: str` | `reset_token` is required and not length-validated. |
| `UserResponse` | `id`, `country?`, `email: EmailStr`, `full_name`, `phone`, `dob?`, `username?`, `address1?`, `address2?`, `city?`, `state?`, `zip?`, `role` | Used by admin user detail. Address fields nullable. `dob` is a string in `YYYY-MM-DD`. |
| `UserRole` | `USER`, `ADMIN` | Serialized uppercase. |
| `CurrentUser` | `user_id: int`, `role: UserRole` | Internal auth dependency return, not a response model. |
| `CreateUserResponse` | `id`, `message`, `token`, `refresh_token` (TypedDict) | Registration response shape; not a Pydantic response model. |

**Admin vs user identity:** admin accounts live in the separate `admins` table. `users` also has a `role` column defaulting to `USER`, but `/admin/register` inserts into `admins`, not `users`. IDs can overlap between the two tables; do not assume an ID is globally unique across both.

### D.2 Wallet models

| Model | Fields | Notes |
|---|---|---|
| `PaymentMethod` (IntEnum) | `CRYPTO = 1`, `BANK = 2` | Used in deposit requests. Values are integers, not strings. |
| `Deposit` | `amount: Decimal`, `asset_id: int`, `payment_method: PaymentMethod` | Nested under `DepositFundsRequest`. |
| `DepositFundsRequest` | `deposit: Deposit` | Nested body, not flat. |
| `DepositStatus` | `pending`, `confirmed`, `rejected` | Lowercase serialized values. |
| `DepositFundsResponse` | `id`, `amount`, `status`, `created_at`, `confirmed_at?`, `asset_id`, `asset_symbol`, `asset_name`, `payment_method_id`, `payment_method_name`, `payment_method_type`, `bank_name?`, `account_name?`, `account_number?` | Amount quantized to 2 dp. Used by detail/confirm/reject. |
| `AdminDepositResponse` / `DepositResponse` | `id`, `user_id` (admin only), `payment_method: str`, `asset: str`, `amount: Decimal`, `status: str`, `date: datetime` | List shape. Amount is **not** quantized. `payment_method` and `asset` are names, not IDs. |
| `WithdrawStatus` | `pending`, `confirmed`, `rejected` | Lowercase. |
| `WithdrawFundsRequest` | `amount: Decimal`, `destination_id: int` | Used by the user withdrawal route, not admin. |
| `WithdrawFundsResponse` | `id`, `amount`, `status`, `created_at`, `confirmed_at?`, `asset_id`, `asset_symbol`, `asset_name`, `destination_id`, `destination_label`, `destination_type`, `address?`, `bank_name?`, `account_name?`, `account_number?` | Amount quantized to 2 dp. Used by detail/confirm/reject. |
| `UserWithdrawalRecordsResponse` | `id`, `amount`, `status`, `created_at`, `asset_symbol`, `asset_name`, `destination_type` | User list shape; amount raw. |
| `AdminWithdrawalRecordsResponse` | same as above + `user_id` | Admin list shape; amount raw. |
| `DestinationType` | `CRYPTO`, `BANK` | Uppercase. |
| `MoneyFlowType` / `MoneyFlowDirection` | `DEPOSIT`, `WITHDRAWAL`, `SUBSCRIPTION_INVESTMENT`, `SUBSCRIPTION_PAYOUT` / `IN`, `OUT` | Not part of admin inventory but relevant to wallet data. |

**Money fields:** `amount`, `available`, and `locked` are `DECIMAL(20,8)` in MySQL. Responses that build a detailed deposit/withdrawal quantize to 2 dp; list responses pass the raw DB value. This produces strings like `"100.00"` in one endpoint and `"100.00000000"` in another for the same record.

### D.3 Plan models

| Model | Fields | Notes |
|---|---|---|
| `PlanStatus` | `ACTIVE`, `INACTIVE` | Uppercase. |
| `RiskManagement` | `STANDARD`, `ADVANCED_HEDGING`, `TAILORED_MULTI_LAYER` | Uppercase. |
| `Plan` | `title`, `min_amount: Decimal`, `duration: int`, `roi: Decimal`, `risk_management`, `description` | Nested in create/update requests. |
| `CreatePlanRequest` | `plan: Plan`, `features: list[str]` | Features may be empty. |
| `UpdatePlanRequest` | `plan_id: int`, `plan: Plan`, `features: list[str]` | Full replacement; features replace the set. |
| `PlanResponse` | `id`, `title`, `min_amount`, `duration`, `roi`, `risk_management`, `description`, `status`, `features`, `created_at`, `updated_at` | `min_amount` quantized to 2 dp; `roi` raw `DECIMAL(5,2)`; `features` ordered by feature ID. |
| `PlansResponse` | `plans: list[PlanResponse]` | The only wrapped list response in this contract. |

The `plans` table has `title VARCHAR(100) UNIQUE`, `min_amount DECIMAL(20,8)`, `duration INT`, `roi DECIMAL(5,2)`, `status` enum default `ACTIVE`, and `description TEXT`.

### D.4 Asset and instrument models

| Model | Fields | Notes |
|---|---|---|
| `AddAssetRequest` | `symbol: str`, `name: str`, `address: str \| null`, `is_active: bool` | All required except `address`. No length constraints. |
| `UpdateAssetRequest` | same as add | Full replacement. |
| `AssetResponse` | `id`, `symbol`, `name`, `address?`, `is_active`, `created_at`, `updated_at` | `address` nullable. |
| `DeleteAssetResponse` | `id: int`, `message: str` | Message is fixed: `Asset deleted successfully.` |
| `AddInstrumentRequest` | `symbol` (1–50), `name` (1–255), `category_id: int`, `current_price: Decimal` | `is_active` is not accepted on create; DB default true. |
| `UpdateInstrumentRequest` | `symbol?`, `name?`, `category_id?`, `current_price?`, `is_active?` | Partial merge. |
| `InstrumentResponse` | `id`, `symbol`, `name`, `category_id`, `category: str`, `current_price: Decimal`, `is_active`, `created_at?`, `updated_at?` | `category` is the joined category name. Price raw `DECIMAL(20,8)`. |

### D.5 Portfolio and trading models

| Model | Fields | Notes |
|---|---|---|
| `BuyInstrumentRequest` | `instrument_id: int`, `quantity: Decimal`, `subscription_id: int` | No min/max constraints on quantity in the model. |
| `SellInstrumentRequest` | same as buy | |
| `TransactionResponse` | `message: str`, `transaction_id: int` | Buy/sell success shape. |
| `TradeType` | `BUY`, `SELL` | Used by user trade filters, not by admin trading. |
| `HoldingResponse`, `PortfolioOverviewResponse`, `PortfolioProfitLossResponse`, `TradeOverviewResponse`, `TradeResponse` | Various read models | Used by user portfolio/trade routes; not produced by the two admin trading routes except indirectly through holdings. |

### D.6 Enum values at a glance

| Context | Values | Case |
|---|---|---|
| Role | `USER`, `ADMIN` | Uppercase |
| Deposit status | `pending`, `confirmed`, `rejected` | Lowercase |
| Withdrawal status | `pending`, `confirmed`, `rejected` | Lowercase |
| Plan status | `ACTIVE`, `INACTIVE` | Uppercase |
| Risk management | `STANDARD`, `ADVANCED_HEDGING`, `TAILORED_MULTI_LAYER` | Uppercase |
| Trade type | `BUY`, `SELL` | Uppercase |
| Destination type | `CRYPTO`, `BANK` | Uppercase |
| Payment method input | `1` (CRYPTO), `2` (BANK) | Integer |
| Payment method response type | `CRYPTO`, `BANK TRANSFER` | Uppercase string from DB |
| Money-flow type | `DEPOSIT`, `WITHDRAWAL`, `SUBSCRIPTION_INVESTMENT`, `SUBSCRIPTION_PAYOUT` | Uppercase |
| Money-flow direction | `IN`, `OUT` | Uppercase |

### D.7 Serialization and validation rules

1. **Decimals are strings.** Pydantic v2 serializes `Decimal` to a JSON string to avoid precision loss. Do not use JavaScript `Number` for money. Use a decimal library or integer cents on the client.
2. **Date/times are ISO strings.** MySQL `TIMESTAMP` values are returned as naive datetimes. Pydantic serializes them with a `T` separator and no `Z` unless the database driver supplies a timezone. Display in the user's timezone only after confirming the server's timezone.
3. **`EmailStr` validation** applies to request models and some response models. It requires an `@` and a valid domain form; the exact error text comes from Pydantic and is embedded in the single-string `detail`.
4. **Extra fields are ignored.** A request with unknown properties is accepted if the known properties validate. Do not rely on this for forward compatibility; the backend may later set `extra="forbid"`.
5. **No coercion of enums from labels.** Send exact values/case. Sending `"Pending"` or `"active"` where lowercase/uppercase is expected yields `422`.
6. **`null` vs omitted:** optional response fields are present as `null` where the model declares them. For requests, omitted and explicit `null` can differ at the service layer (notably `PATCH /admin/{admin_id}`).
7. **Validation errors stop at the first error.** The client should present field-specific messages from its own validation and use the server message as a fallback.
8. **Response models filter output.** SQL columns not declared on the response model are not returned. This is why `created_at` disappears from user/admin list items.
9. **No response envelope for errors.** Errors always use `detail`; success bodies never do.

### D.8 Routes with and without a response model

| Has a Pydantic response model | No response model (literal dict) |
|---|---|
| `/admin/me`, `/admin/users`, `/admin/users/{id}`, `/admin/list`, `/admin/{id}`, `PATCH /admin/{id}` | `/admin/register`, `/admin/login`, `/admin/refresh`, `/admin/logout`, `/admin/forgot-password`, `/admin/verify-otp`, `/admin/reset-password` |
| `/wallet/admin/deposits`, `/wallet/admin/withdrawals`, deposit confirm/reject, withdrawal confirm/reject | `DELETE /admin/users/{id}`, `DELETE /admin/{id}` |
| `/plan`, `/plan/create`, `/plan/update` | |
| `/assets`, `POST/PUT/DELETE /assets` | |
| `/instruments`, `POST/PUT/DELETE /instruments` | |
| `/portfolio/admin/buy/{user_id}`, `/portfolio/admin/sell/{user_id}` | |

A route with a response model may still return a `500` object or plain text before serialization if an exception escapes.

---

## E. Database and Side-Effect Reference

### E.1 Tables touched by admin operations

| Table | Admin operations | Notes |
|---|---|---|
| `admins` | `SELECT`, `INSERT`, `UPDATE`, `DELETE` | Registration, login lookup, list/detail, patch, delete. No FKs point to it. |
| `users` | `SELECT`, `DELETE` | List/detail/hard delete. |
| `user_addresses` | Cascaded delete | Removed with the user. |
| `user_preferences` | Cascaded delete | Removed with the user. |
| `wallet` | `UPDATE` on deposit confirm, withdrawal confirm/reject; cascaded delete | No direct admin read endpoint. |
| `deposits` | `SELECT`, `UPDATE status`; cascaded delete via user/asset | Created by the user deposit route, not admin. |
| `withdrawals` | `SELECT`, `UPDATE status`; cascaded delete via user/asset/destination | Created by the user withdraw route. |
| `withdrawal_destination` | `SELECT` (detail joins); cascaded delete via user | Parent destination row. |
| `crypto_destinations` | `SELECT` (detail joins); cascaded delete via asset/user | May be removed by asset delete while parent remains. |
| `bank_destinations` | `SELECT` (detail joins); cascaded delete via user | |
| `assets` | `SELECT`, `INSERT`, `UPDATE`, `DELETE` | Hard delete. No symbol uniqueness constraint. |
| `plans` | `SELECT`, `INSERT`, `UPDATE` | No delete/status route. |
| `plan_features` | `SELECT`, `INSERT`, `DELETE` | Replaced on plan update; cascaded if a plan is deleted outside the API. |
| `instruments` | `SELECT`, `INSERT`, `UPDATE`, soft delete | `is_active` flag; no hard delete API. |
| `categories` | `SELECT` | Only existence validation; no CRUD. |
| `subscriptions` | `SELECT`, pool `UPDATE` via admin trading; cascaded delete via user | Admin trading requires an active subscription. |
| `transactions` | `INSERT` via admin buy/sell; `SELECT` via holdings | No admin transaction list. |
| `payment_methods` | `SELECT` | Validated on deposit; no CRUD. |

There is **no `admin_audit_log`**, **no `created_by`/`updated_by`**, and **no soft-delete column** on users or assets. Financial tables record `user_id` but not the admin who confirmed/rejected/traded.

### E.2 Cascades caused by documented deletes

| Operation | Direct delete | Cascaded effects |
|---|---|---|
| `DELETE /admin/users/{id}` | `users` row | `user_addresses`, `user_preferences`, `wallet`, `deposits`, `withdrawal_destination` → `crypto_destinations`/`bank_destinations`, `withdrawals`, `subscriptions`, `transactions`. Financial and trading history is erased. |
| `DELETE /assets/{id}` | `assets` row | `deposits` and `withdrawals` referencing the asset; `crypto_destinations` referencing the asset. Parent `withdrawal_destination` rows may remain orphaned. |
| `DELETE /admin/{id}` | `admins` row | No FK cascades. Sessions are revoked in Redis. |
| `DELETE /instruments/{id}` | none (soft delete) | No cascade. Trade history preserved. |
| Plan delete | no API | If done directly in SQL, `plan_features` and `subscriptions` cascade. Do not do this manually in production. |
| Payment-method delete | no API | Direct SQL would cascade deposits and payment-method detail rows. Do not do this manually. |

### E.3 Financial operation map

| Operation | Status transition | Wallet effect | Other effects | Idempotency |
|---|---|---|---|---|
| Deposit confirm | `pending → confirmed` | `available += amount` quantized to 2 dp | `confirmed_at = UTC now` | Status guard; second call `400` |
| Deposit reject | `pending → rejected` | none | No `confirmed_at` | Status guard; second call `400` |
| Withdrawal confirm | `pending → confirmed` | `locked -= amount` raw | `confirmed_at = UTC now` | Status guard; second call `400` |
| Withdrawal reject | `pending → rejected` | `available += amount`, `locked -= amount` raw | None | Status guard; second call `400` |
| Admin buy | none | none | `subscriptions.pool -= price * quantity`; insert `BUY` transaction | None; retry duplicates the trade |
| Admin sell | none | none | `subscriptions.pool += price * quantity`; insert `SELL` transaction | None; retry duplicates the trade |

**Wallet vs subscription pool:** wallet deposits/withdrawals and subscription trading use different balances. A confirmed deposit credits `wallet.available`. A subscription creates a `subscriptions.pool` from the invested amount. Admin buy/sell debits/credits only the pool. Do not show "wallet available" as "available to trade" without explaining the difference.

**Missing rowcount checks:** the deposit credit, withdrawal lock consumption, and withdrawal unlock have no `rowcount` assertion. The confirm/reject status update does check rowcount, so duplicate transitions are blocked, but a missing wallet row or a data inconsistency can still produce a `200` with no wallet effect or a negative `locked` balance.

### E.4 Redis and session side effects

| Action | Redis effect |
|---|---|
| Register | Set access (2 h) and refresh (7 d) for the new admin. |
| Login | Overwrite access and refresh for that admin. |
| Refresh | Overwrite access only; refresh stays. |
| Logout | Delete access and refresh. |
| Forgot password | Set OTP secret (5 min), overwriting any previous OTP. |
| Verify OTP | Delete OTP secret; set reset token (1 h). |
| Reset password | Delete access, refresh, and reset token after the DB update. |
| Update admin | Delete target's access and refresh. |
| Delete admin | Delete target's access and refresh. |
| Delete user | Delete user's access only; refresh remains but fails the DB existence check on `/auth/refresh`. |

Redis is a hard dependency at startup and during every authenticated request. If Redis is flushed, all sessions are invalid even though JWTs have not expired. This is by design in the current implementation (server-side token revocation), but it means a Redis outage logs everyone out and can make admin operations unavailable.

### E.5 Email side effects

- Only `POST /admin/forgot-password` sends email.
- Subject: `Password Reset OTP`.
- Body: plain text `Your password reset OTP.` plus an HTML template with the 6-digit OTP.
- The email is placed on an in-process `queue.Queue`; three daemon worker threads send it with three retries and exponential backoff.
- `send_email()` returns immediately after enqueueing. SMTP failures do not change the HTTP response.
- On process shutdown, the service attempts to drain the queue and join workers, but a crash can lose queued mail.
- No delivery webhook, bounce handling, or resend cooldown exists.

### E.6 Audit, idempotency, and rate limiting

| Control | Status |
|---|---|
| Admin audit log | **Absent.** No record of which admin confirmed a deposit, changed a plan, deleted a user, etc. |
| Idempotency keys | **Absent.** Create/trade endpoints can duplicate on retry; status transitions are naturally guarded. |
| Rate limiting | **Absent** in application code. Login, registration, forgot-password, OTP verification, and all financial actions are unthrottled unless a reverse proxy adds limits outside this repo. |
| Request IDs / correlation IDs | **Absent.** |
| Optimistic concurrency (`If-Match`, version) | **Absent.** Last write wins. |
| Soft delete / recycle bin | **Absent** for users and assets. Instruments use a soft-delete flag. |
| Approval workflow (maker/checker) | **Absent.** A single admin can confirm a withdrawal or trade immediately. |

### E.7 Background settlement worker

`app/services/settlement_service.py` starts a daemon thread from the app lifespan. Every `SETTLEMENT_INTERVAL_SECONDS` (default 86,400 seconds / 24 hours), it:

1. Selects active subscriptions whose expiration date has passed.
2. Settles each in its own transaction (market value of open positions, pool, payout).
3. Commits per subscription and logs failures.

Implications for the admin console:

- Subscription status, pool, and settled amounts can change without an admin action.
- An admin trading request that targets a subscription may race with settlement; if the subscription is no longer `ACTIVE`, the trade returns `404 Active subscription not found.`
- The worker is not exposed through an admin endpoint and cannot be triggered manually from the API.

### E.8 Partial-commit and failure windows

Several operations commit the database change **before** a Redis or read-back step that can fail. In those cases the API can return `500` while the database change is already durable.

| Operation | Commit point | Later failure that yields 500 | Result |
|---|---|---|---|
| Admin register | After admin insert | Redis token storage | Admin row exists, client has no tokens. |
| Admin update | After DB update | Redis revocation | Email/password changed, old session may remain until TTL. |
| Admin delete | After DB delete | Redis revocation | Admin gone, token may remain until TTL. |
| User delete | After DB delete | Redis access-token delete | User and history gone, token may remain until TTL. |
| Password reset | After hash update | Redis access/refresh/reset deletion | Password changed, tokens may remain. |
| Asset create | After insert | Read-back of created row | Asset exists, client sees 500. |
| Asset update | After update | Read-back | Asset updated, client sees 500. |
| Deposit confirm | After wallet credit + status | Response build | Deposit confirmed and credited, client may see 500. |
| Withdrawal confirm/reject | After wallet mutation + status | Response build | Wallet/status changed, client may see 500. |

For financial operations, a client that retries after a `500` should first re-read the record's status rather than blindly retrying. For creates, use a client-generated correlation in a separate field only if the backend supports it (it currently does not), or reconcile by listing.

---

## F. Pagination, Filtering, and Sorting

### F.1 Paginated endpoints

| Endpoint | Default `limit` | Max `limit` | `offset` | Filter | Sort |
|---|---:|---:|---|---|---|
| `GET /admin/users` | 10 | 100 | ≥ 0 | none | `created_at DESC` |
| `GET /admin/list` | 10 | 100 | ≥ 0 | none | `created_at DESC` |
| `GET /wallet/admin/deposits` | 10 | 100 | ≥ 0 | `status` (deposit enum) | `created_at DESC` |
| `GET /wallet/admin/withdrawals` | 10 | 100 | ≥ 0 | `status` (withdrawal enum) | `created_at DESC` |
| `GET /instruments` | 10 | 100 | ≥ 0 | `is_active` (bool) | `created_at DESC` |

All paging is **offset-based**. There are no cursor tokens, page numbers, total counts, `Link` headers, or `X-Total-Count` headers. A page is just a JSON array.

Invalid paging values produce `422` with a single-string detail, e.g.:

```json
{"detail": "limit: Input should be less than or equal to 100"}
```

### F.2 Non-paginated endpoints

| Endpoint | Result size | Notes |
|---|---|---|
| `GET /plan` | all plans (admin) / all active plans (user) | No paging. Could grow unbounded. |
| `GET /assets` | all assets | No paging. |
| `GET /admin/users/{id}` | one | |
| `GET /admin/{id}` | one | |
| Deposit/withdrawal confirm/reject | one | |
| `POST /plan/create`, `/plan/update` | one | |
| Asset/instrument creates/updates/deletes | one | |
| Admin buy/sell | one transaction result | |

`GET /assets` returning every asset without paging is usually fine for a small reference table, but it becomes a problem if the asset catalog grows or includes per-chain tokens.

### F.3 Sorting

There are no sort parameters. Each query has a fixed order:

- Users and admins: newest first (`created_at DESC`).
- Deposits, withdrawals, instruments: newest first (`created_at DESC`).
- Assets: `id ASC` (creation order, oldest first).
- Plans: `created_at DESC`.
- Plan features: `id ASC` (insertion order).
- No endpoint supports sorting by amount, status, email, symbol, or name.

If the UI needs a different order (e.g., pending deposits oldest first), it must sort the current page client-side, which is misleading across pages. Request a backend sort parameter rather than implementing cross-page client sorting.

### F.4 Empty-result behavior

| Endpoint | Empty result |
|---|---|
| `GET /admin/users` | `200 []` |
| `GET /admin/list` | `200 []` |
| `GET /wallet/admin/deposits` | `200 []` |
| `GET /wallet/admin/withdrawals` | `200 []` |
| `GET /instruments` | `200 []` |
| `GET /plan` | `200 {"plans":[]}` |
| `GET /assets` | **`404 {"detail":"No assets found."}`** |
| Detail routes | `404`, except missing deposit detail which becomes `500` |

The asset behavior is inconsistent with every other collection. A generic "404 means the resource is missing" handler will show an error page for an empty asset table. Treat `404 No assets found.` on `GET /assets` as an empty list only after confirming this is the deployed behavior; otherwise surface a setup warning.

### F.5 Recommended frontend paging strategy

1. Start with `limit=10` or `limit=50` and `offset=0`. Do not exceed 100.
2. Request pages until a page returns fewer than `limit` rows; there is no total to stop on.
3. Keep filters stable between page requests. Changing `status` while paging should reset `offset` to 0.
4. Because deletes and inserts shift offsets, refresh the first page after a destructive action rather than trying to patch the local array.
5. For pending-work queues (deposits/withdrawals), default to `status=pending` and sort/process oldest first on the client only within the current page; ask the backend for an ascending sort if the queue is large.
6. Never infer "no more pages" from a `404` on these list endpoints; only `GET /assets` has that quirk.

---

## G. Gaps, Risks, and Missing Behavior

### G.1 Critical authorization and security findings

| ID | Severity | Finding | Evidence | Impact |
|---|---|---|---|---|
| S1 | **Critical** | `POST /admin/register` is public and creates a privileged admin with valid tokens. | `admin_routes.py:24-30` has no dependency; `admin_services.py:343-381` always inserts into `admins` and returns tokens. | Anyone who can reach the API can become an admin and use all 26 admin-only routes. All other admin authorization is moot until this is fixed. |
| S2 | **High** | Deposit detail is readable by any authenticated user with no ownership check. | `wallet_routes.py:109-120` uses `get_current_user`; service fetches by ID only. | IDOR: full deposit, asset, payment method, and bank details of any user. |
| S3 | **High** | Withdrawal detail is readable by any authenticated user with no ownership check. | `wallet_routes.py:159-170` uses `get_current_user`; service fetches by ID only. | IDOR: full payout destination, bank name, account name, and account number of any user. |
| S4 | **High** | Any admin can change any other admin's email and password, then revoke their session. | `PATCH /admin/{admin_id}` has no self/role restriction; `delete_admin` only blocks self-delete. | Admin account takeover; no superadmin or ownership boundary. |
| S5 | **High** | No audit trail for financial or destructive admin actions. | No audit table or `admin_id` columns in any migration; confirm/reject/delete/trade services do not record the caller. | Fraud, mistake, and insider-action investigations are impossible from the database. |
| S6 | **High** | No rate limiting, lockout, MFA, or CAPTCHA on login, registration, forgot-password, OTP verification, or financial actions. | No throttling code or middleware in `app/main.py` or the services. | Credential stuffing, OTP brute force, email bombing, and accidental double actions. |
| S7 | **Medium** | Login and forgot-password reveal whether an admin email exists (`401 Invalid credentials` vs `401 Password is incorrect`; `404 Admin not found`). | `admin_services.py:413-424`, `554-558`. | Admin account enumeration and targeted phishing. |
| S8 | **Medium** | Error text from caught exceptions is returned to clients. | Many services do `detail=str(e)`. | May leak SQL, Redis, schema, or infrastructure details. |
| S9 | **Medium** | No re-authentication or step-up confirmation for withdrawal approval, user deletion, asset deletion, or admin password changes. | No such check in the routes/services. | A stolen admin session can perform irreversible actions immediately. |
| S10 | **Medium** | Password policy is only 8–100 characters. | `auth_models.py` fields. | Weak passwords are accepted; no breach-list or reuse check. |
| S11 | **Medium** | JWT has no `iss`, `aud`, `jti`, or key rotation metadata. | `jwt.py:18-41`. | Token handling relies entirely on secret strength and Redis revocation; no per-token identification. |
| S12 | **Medium** | Redis is a single point of failure for all sessions. | Startup ping; every auth checks Redis; token storage errors return 500. | A Redis outage logs out every admin and blocks the console. |
| S13 | **Low/Medium** | CORS defaults to `*` when `ALLOWED_ORIGINS` is unset, with credentials disabled. | `main.py:25-28,93-99`. | Bearer tokens are not sent automatically, so classic CSRF is limited, but any origin can call the API if it obtains a token. Restrict origins in production. |
| S14 | **Low** | OpenAPI/docs are enabled with no auth. | FastAPI defaults; no route guard. | Schema disclosure. Often acceptable, but confirm for production. |
| S15 | **Low** | No explicit HTTPS/HSTS enforcement in the app. | No middleware. | Tokens and passwords can be intercepted if deployed without TLS termination. |

**CSRF note:** authentication uses the `Authorization` header, not cookies. A browser will not attach the bearer token cross-site automatically, so traditional CSRF is not the primary risk. XSS, token storage, and permissive CORS are the relevant concerns.

### G.2 Financial and data-integrity risks

| ID | Severity | Finding | Consequence |
|---|---|---|---|
| F1 | **High** | `DELETE /admin/users/{id}` hard-deletes the user and cascades wallet, deposits, withdrawals, subscriptions, and transactions. | Irreversible loss of financial history and audit evidence. No soft delete or restore. |
| F2 | **High** | `DELETE /assets/{id}` hard-deletes the asset and cascades deposits/withdrawals/crypto destinations. | Irreversible loss of financial records; orphaned destination parents possible. |
| F3 | **High** | Withdrawal confirm/reject wallet updates do not check rowcount and have no non-negative guard. | `locked` can become negative; a missing wallet can yield a successful status change with no balance effect. |
| F4 | **High** | Deposit confirm credits the wallet without checking the wallet update rowcount. | A missing wallet row yields a confirmed deposit with no credit. |
| F5 | **High** | Admin buy/sell have no idempotency key. | A retry after timeout duplicates a trade and moves the pool twice. |
| F6 | **High** | Sell quantity check is a non-locking read followed by insert. | Concurrent sells can oversell a subscription's position. |
| F7 | **High** | Plan create returns `401` for duplicate title. | A global 401 interceptor can log the admin out or enter a refresh loop. |
| F8 | **Medium** | Deposit amounts are quantized to 2 decimals for the wallet credit while stored at 8 decimals. | Sub-cent value is lost or rounded; ledger and display can diverge. |
| F9 | **Medium** | List endpoints return raw 8-decimal amounts; detail/confirm endpoints return 2-decimal amounts. | The same record shows different values in list vs detail; reconciliation is harder. |
| F10 | **Medium** | `PUT /assets/{id}` returns `404` when no values changed. | A valid no-op update looks like a missing asset. |
| F11 | **Medium** | `GET /wallet/deposit/{id}` converts a missing record into `500`. | Clients cannot distinguish "not found" from a server failure, and error dashboards get noise. |
| F12 | **Medium** | Registration/update/delete/reset commit before Redis operations. | A `500` can leave a durable DB change with an inconsistent session state. |
| F13 | **Medium** | Asset symbols are not unique. | Duplicate symbols confuse deposits, withdrawals, and reporting. |
| F14 | **Medium** | Deposit validation accepts inactive assets. | Users can deposit into an asset that is meant to be disabled. |
| F15 | **Medium** | No last-admin protection. | Deleting the final other admin can leave the platform without an operator (public registration makes recovery insecure but possible). |
| F16 | **Low/Medium** | Offset pagination has no total and drifts after inserts/deletes. | Admin queues can skip or duplicate rows between pages. |
| F17 | **Low** | No plan status toggle or delete route. | Inactive plans cannot be reactivated through the API; a typo cannot be retired without direct SQL. |
| F18 | **Low** | No admin view of a user's wallet, subscriptions, deposits, withdrawals, or trades. | Operators must use unrelated user routes or direct database access, increasing error risk. |

### G.3 Contract inconsistencies and rough edges

| ID | Inconsistency | Details |
|---|---|---|
| C1 | `401` used for duplicate plan title | `POST /plan/create` → `401 Plan title already used.`; `POST /plan/update` → `400 A plan with this title already exists.` |
| C2 | Empty assets is `404` | All other list endpoints return `[]`; `GET /assets` returns `404 No assets found.` |
| C3 | No-op asset update is `404` | Rowcount is checked after `UPDATE`; MySQL reports zero changed rows for identical values. |
| C4 | Missing deposit detail is `500` | The 404 `HTTPException` is caught by a broad `except Exception` and re-raised as 500 with `404: Deposit not found.` |
| C5 | Every success is `200` | No `201 Created` for creates, no `204 No Content` for deletes. Clients must not expect REST-typical codes. |
| C6 | Wrapped vs bare lists | `GET /plan` returns `{"plans":[...]}`; users/admins/deposits/withdrawals/instruments/assets return bare arrays. |
| C7 | Enum case mix | Roles/plans/trades uppercase; deposit/withdrawal status lowercase; payment method input integer but output string. |
| C8 | Amount representation mix | Raw 8-decimal strings in lists vs 2-decimal strings in detail/confirm. |
| C9 | Inconsistent not-found strings | `User not found` (no period) in admin user routes vs `User not found.` (period) in portfolio; `Deposit not found.` vs `Withdraw record '<id>' not found.` |
| C10 | First validation error only | A form with three invalid fields receives only the first message. |
| C11 | `PATCH /admin/{id}` empty body semantics | `{}` is a business `400`, not a validation `422`, because both fields are optional. |
| C12 | Duplicate title check is race-prone | A `SELECT` pre-check plus a DB unique key can still race; the loser may get a generic `500`. |
| C13 | `AdminPublic.email` is a plain `str` | Unlike `AdminUserListItem.email`, it is not re-validated on output. |
| C14 | Payment method type naming | Request enum uses `BANK`; response/database type uses `BANK TRANSFER`. |

### G.4 Missing administrative capabilities

The current backend does not provide:

- **Dashboard metrics:** total users, deposits, withdrawals, AUM, pending counts, revenue, or time-series charts.
- **User administration beyond read/delete:** no suspend, ban, reactivate, role change, admin-initiated password reset, wallet adjustment, KYC status, or notes.
- **Financial detail:** no admin deposit/withdrawal detail endpoint, no receipt, no ledger, no reconciliation, no manual adjustment, and no refund.
- **Transaction/trade administration:** no admin list of a user's trades, no cancellation, no correction, no audit of who traded.
- **Subscription administration:** no admin list/detail/cancel/settle; only the background worker and user routes.
- **Plan lifecycle:** no delete, activate, deactivate, duplicate, archive, or status toggle.
- **Asset lifecycle:** no get-by-id, search, dependency check, soft delete, or symbol uniqueness.
- **Instrument lifecycle:** no price history, market-data sync, hard delete, or bulk import.
- **Reference data:** no category CRUD and no payment-method CRUD.
- **Operations:** no audit log, approval workflow, idempotency, rate limits, exports, or bulk actions.
- **Notifications:** no admin notification feed, email log, or delivery status.
- **Search/sort:** no user/email/symbol search and no sort parameters.
- **Pagination metadata:** no totals or cursor tokens.

### G.5 Verification performed in this review

**Confirmed by source review**

- 73 total FastAPI routes (including docs and root); 34 admin-related routes; 2 related non-admin detail routes.
- Route ordering and auth dependencies for all 34.
- Redis key formats and TTLs.
- Exact error strings and status codes listed in Section C.
- Financial mutation sequences and missing rowcount checks.
- Migration foreign keys and cascades.
- Absence of audit, idempotency, rate limiting, plan status, and admin detail routes.

**Confirmed by non-mutating runtime probes**

| Probe | Result |
|---|---|
| `GET /admin/me` with no header | `401`, `WWW-Authenticate: Bearer`, `{"detail":"Not authenticated"}` |
| `GET /admin/me` with `Authorization: Basic ...` | `401`, `{"detail":"Not authenticated"}` |
| `GET /admin/me` with `Bearer not-a-jwt` | `401`, `{"detail":"Invalid token"}`, no `WWW-Authenticate` |
| `POST /admin/register` with `{}` | `422`, `{"detail":"email: Field required"}` |
| `POST /admin/register` with short password | `422`, `{"detail":"password: String should have at least 8 characters"}` |
| `POST /admin/register` with bad email | `422`, email-format message |
| `POST /admin/register` with an extra field | Extra field ignored; request proceeded past validation |
| Route enumeration | Importing `app.main` yielded the expected 34 admin routes |

**Disclosed probe incident**

One extra-field probe on `POST /admin/register` proceeded into the service and reached the database insert. Because `create_admin` commits before storing tokens in Redis, the row persisted even though the request returned `500` when Redis was unavailable. The probe created admin row `id=1333` with a synthetic email. It was deleted immediately, and a follow-up query confirmed no row with that ID or email remains. This incident is itself evidence for the partial-commit risk in Section E.8. No user, wallet, deposit, withdrawal, plan, instrument, trade, or other business data was modified. No further mutation probes were run.

**Not verified**

- Full end-to-end integration tests. They require live MySQL and Redis and create/delete records. They were reviewed but not executed.
- Exact JSON datetime offset behavior (depends on MySQL driver and server timezone).
- MySQL isolation/locking behavior under real concurrency.
- Email delivery through the configured SMTP provider.
- Cascade behavior at runtime (confirmed from migrations, not by deleting a real user/asset).
- Behavior behind a production reverse proxy, including rate limits, TLS, and CORS.
- Case sensitivity of email/symbol uniqueness under the production collation.

### G.6 Risk prioritization for the frontend team

**P0 — block the admin UI release until resolved**

1. Remove or protect `POST /admin/register`.
2. Add admin + ownership checks to the deposit/withdrawal detail routes (or do not use them).
3. Add audit logging and a confirmation/approval flow for irreversible financial and delete actions.

**P1 — fix before broad operator use**

4. Add idempotency and rowcount/non-negative guards to wallet operations.
5. Add rate limits and lockout to auth/OTP endpoints.
6. Restrict admin-to-admin email/password changes and add last-admin protection.
7. Fix the `401` duplicate-plan response so session interceptors do not misfire.

**P2 — correctness and UX**

8. Make asset update no-op return `200`, empty assets return `[]`, and missing deposit detail return `404`.
9. Unify amount precision across list and detail.
10. Add totals/cursors or document offset limitations clearly.
11. Add plan status management, admin financial detail, and user wallet/subscription/trade views.

**P3 — polish**

12. Unify error wording and enum casing.
13. Add search/sort/filter parameters.
14. Document timezone handling and OpenAPI auth requirements.

---

## H. Source Traceability

### H.1 Route-to-code map

| Route | Handler | Service / helper | Query / model |
|---|---|---|---|
| `POST /admin/register` | `app/routes/admin_routes.py:24-30` | `app/services/admin_services.py:343-398` | `INSERT_ADMIN` (`app/db/queries/admin_queries.py:9-18`), `Admin` |
| `POST /admin/login` | `app/routes/admin_routes.py:33-42` | `app/services/admin_services.py:401-460` | `GET_ADMIN_BY_EMAIL` (`admin_queries.py:3-7`), `LoginUserRequest` |
| `GET /admin/me` | `app/routes/admin_routes.py:45-51` | `app/services/admin_services.py:463-499` | `GET_ADMIN_BY_ID` (`admin_queries.py:33-37`) |
| `POST /admin/refresh` | `app/routes/admin_routes.py:54-60` | `app/services/admin_services.py:502-524` → `app/services/user_services.py:467-523` | `decode_token`, Redis refresh key |
| `POST /admin/logout` | `app/routes/admin_routes.py:63-69` | `app/services/admin_services.py:527-540` | Redis access/refresh delete |
| `POST /admin/forgot-password` | `app/routes/admin_routes.py:72-78` | `app/services/admin_services.py:543-591` | OTP generation, `app/utils/redis.py:56-76`, `app/services/email_service.py` |
| `POST /admin/verify-otp` | `app/routes/admin_routes.py:81-87` | `app/services/admin_services.py:594-655` | `app/utils/otp.py:20-26`, reset-token Redis key |
| `POST /admin/reset-password` | `app/routes/admin_routes.py:90-96` | `app/services/admin_services.py:658-723` | `UPDATE_ADMIN_PASSWORD` (`admin_queries.py:46-50`) |
| `GET /admin/users` | `app/routes/admin_routes.py:104-113` | `app/services/admin_services.py:90-128` | `GET_ALL_USERS` (`user_queries.py:46-51`), `PaginationRequest` |
| `GET /admin/users/{user_id}` | `app/routes/admin_routes.py:116-124` | `app/services/user_services.py:175-223` | `GET_USER_BY_ID` (`user_queries.py:8-26`) |
| `DELETE /admin/users/{user_id}` | `app/routes/admin_routes.py:127-135` | `app/services/admin_services.py:131-174` | `DELETE_USER` (`user_queries.py:40-44`) |
| `GET /admin/list` | `app/routes/admin_routes.py:143-152` | `app/services/admin_services.py:177-213` | `GET_ALL_ADMINS` (`admin_queries.py:39-44`) |
| `GET /admin/{admin_id}` | `app/routes/admin_routes.py:155-163` | `app/services/admin_services.py:463-499` | `GET_ADMIN_BY_ID` |
| `PATCH /admin/{admin_id}` | `app/routes/admin_routes.py:166-175` | `app/services/admin_services.py:216-282` | `UPDATE_ADMIN` (`admin_queries.py:25-31`) |
| `DELETE /admin/{admin_id}` | `app/routes/admin_routes.py:178-188` | `app/services/admin_services.py:285-335` | `DELETE_ADMIN` (`admin_queries.py:20-23`) |
| `GET /wallet/admin/deposits` | `app/routes/wallet_routes.py:208-225` | `app/services/wallet_services.py:504-536` | `app/utils/wallet/deposits.py:50-58`, `GET_ALL_DEPOSITS` (`deposits_queries.py:97-118`) |
| `GET /wallet/admin/withdrawals` | `app/routes/wallet_routes.py:228-245` | `app/services/wallet_services.py:539-571` | `app/utils/wallet/withdraws.py:180-187`, `GET_ALL_WITHDRAWALS` (`withdraw_queries.py:126-144`) |
| `POST /wallet/deposits/{id}/confirm` | `app/routes/wallet_routes.py:77-90` | `app/services/wallet_services.py:116-157` | `app/utils/wallet/deposits.py:81-92`, `app/utils/wallet/wallet.py:52-60` |
| `POST /wallet/deposits/{id}/reject` | `app/routes/wallet_routes.py:93-106` | `app/services/wallet_services.py:215-247` | `app/utils/wallet/deposits.py:95-106` |
| `POST /wallet/withdrawals/{id}/confirm` | `app/routes/wallet_routes.py:248-261` | `app/services/wallet_services.py:574-611` | `app/utils/wallet/withdraws.py:190-201`, `app/utils/wallet/wallet.py:103-111` |
| `POST /wallet/withdrawals/{id}/reject` | `app/routes/wallet_routes.py:264-277` | `app/services/wallet_services.py:614-649` | `app/utils/wallet/withdraws.py:204-215`, `app/utils/wallet/wallet.py:92-100` |
| `GET /plan` | `app/routes/plan_routes.py:25-35` | `app/services/plan_services.py:33-68` | `app/utils/plans/plan_helpers.py:136-169`, `app/utils/plans/responses.py:82-110` |
| `POST /plan/create` | `app/routes/plan_routes.py:38-52` | `app/services/plan_services.py:71-132` | `app/utils/plans/plan_helpers.py:104-110,123-133,217-253` |
| `POST /plan/update` | `app/routes/plan_routes.py:55-69` | `app/services/plan_services.py:135-197` | `app/utils/plans/plan_helpers.py:196-210,261-281,373-377` |
| `GET /assets` | `app/routes/asset_routes.py:26-37` | `app/services/asset_services.py:26-50` | `app/utils/wallet/assets.py:23-37`, `GET_ASSETS` (`asset_queries.py:7-11`) |
| `POST /assets` | `app/routes/asset_routes.py:40-54` | `app/services/asset_services.py:53-96` | `ADD_ASSET` (`asset_queries.py:13-20`) |
| `PUT /assets/{id}` | `app/routes/asset_routes.py:57-73` | `app/services/asset_services.py:99-151` | `UPDATE_ASSET` (`asset_queries.py:22-30`) |
| `DELETE /assets/{id}` | `app/routes/asset_routes.py:76-90` | `app/services/asset_services.py:154-192` | `DELETE_ASSET` (`asset_queries.py:32-35`) |
| `GET /instruments` | `app/routes/instrument_routes.py:25-39` | `app/services/instrument_services.py:43-80` | `app/utils/instruments.py:53-64`, `GET_INSTRUMENTS` (`instrument_queries.py:50-67`) |
| `POST /instruments` | `app/routes/instrument_routes.py:42-53` | `app/services/instrument_services.py:83-134` | `app/utils/instruments.py:11-50`, `ADD_INSTRUMENT` (`instrument_queries.py:86-93`) |
| `PUT /instruments/{id}` | `app/routes/instrument_routes.py:56-69` | `app/services/instrument_services.py:137-200` | `app/utils/instruments.py:11-50`, `UPDATE_INSTRUMENT` (`instrument_queries.py:95-104`) |
| `DELETE /instruments/{id}` | `app/routes/instrument_routes.py:72-84` | `app/services/instrument_services.py:203-238` | `DELETE_INSTRUMENT` (`instrument_queries.py:106-110`) |
| `POST /portfolio/admin/buy/{user_id}` | `app/routes/portfolio_routes.py:40-55` | `app/services/portfolio_services.py:28-93` | `app/utils/portfolio_helpers.py:41-88`, `app/utils/plans/subscription_helpers.py:231-279`, `DEBIT_SUBSCRIPTION_POOL` |
| `POST /portfolio/admin/sell/{user_id}` | `app/routes/portfolio_routes.py:58-73` | `app/services/portfolio_services.py:96-178` | `app/utils/portfolio_helpers.py:41-106`, `app/utils/plans/subscription_helpers.py:201-217,231-257` |
| `GET /wallet/deposit/{id}` (appendix) | `app/routes/wallet_routes.py:109-120` | `app/services/wallet_services.py:191-212` | `app/utils/wallet/deposits.py:61-76` |
| `GET /wallet/withdrawal/{id}` (appendix) | `app/routes/wallet_routes.py:159-170` | `app/services/wallet_services.py:373-399` | `app/utils/wallet/withdraws.py:149-163` |

### H.2 Shared infrastructure

| Concern | File | Key lines |
|---|---|---|
| App assembly, CORS, validation handler, routers | `app/main.py` | 25-28, 31-47, 49-109, 112-117 |
| JWT creation/decoding | `app/utils/jwt.py` | 18-62 |
| Bearer auth + admin role | `app/utils/jwt.py` | 65-103 |
| Redis key format and TTL helpers | `app/utils/redis.py` | 9-139 |
| OTP generation/verification | `app/utils/otp.py` | 3-26 |
| Password hashing | `app/utils/password.py` | 4-27 |
| Pagination callback | `app/services/pagination_service.py` | 9-61 |
| Email queue/workers | `app/services/email_service.py` | 16-139 |
| SMTP config | `app/email.py` | 8-30 |
| Background settlement | `app/services/settlement_service.py` | 13-134 |
| DB connection/autocommit | `app/db/connection.py` | 10-41 |
| Local runner/port | `run.py` | 9-23 |

### H.3 Model files

| Area | File |
|---|---|
| Admin/user/auth request and response models | `app/Models/auth_models.py` |
| Deposit/withdrawal/wallet models | `app/Models/wallet_models.py` |
| Plan and subscription models | `app/Models/plans_models.py` |
| Asset models | `app/Models/asset_models.py` |
| Instrument models | `app/Models/instrument_models.py` |
| Portfolio/trade models | `app/Models/portfolio_models.py` |

### H.4 Migration map

| Migration | Relevance |
|---|---|
| `001_create_users_schema.sql` | Users, roles, unique email/phone/username. |
| `002_create_user_address_schema.sql` | Address row, `ON DELETE CASCADE` from users. |
| `003_create_plans.sql` | Plan fields, unique title, status default `ACTIVE`. |
| `004_create_plan_features.sql` | Features, unique `(plan_id, feature)`, cascade from plans. |
| `005_create_subscriptions.sql` | Subscriptions, cascade from users/plans. |
| `006_create_category.sql`, `007_create_instruments.sql` | Categories and instruments; category FK cascade. |
| `008_create_transactions.sql` | Trades; cascade from users/instruments; subscription `SET NULL`. |
| `011_create_wallet.sql` | Wallet balances, unique user, cascade from users. |
| `012_create_assets.sql` | Assets, no unique symbol. |
| `013-018` payment methods and destinations | Payment-method seeds and detail tables. |
| `019_create_deposits.sql` | Deposits, cascade from users/payment methods/assets. |
| `020_create_withdrawal_destinations.sql` | Destination parent, unique `(user_id,label)`, cascade from users. |
| `021_create_crypto_destinations.sql` | Crypto detail, cascade from destination and asset. |
| `022_create_bank_destinations.sql` | Bank detail, cascade from destination. |
| `023_create_withdrawals.sql` | Withdrawals, cascade from users/assets/destinations. |
| `025_create_admin.sql` | Admins table, unique email, role default `ADMIN`. |
| `026_instrument_soft_delete.sql` | Adds `is_active` and unique symbol to instruments. |
| `027_create_user_preferences.sql` | Preferences, cascade from users. |
| `028_add_subscription_pool.sql` | Adds `subscriptions.pool`. |
| `029_add_subscription_settlement.sql` | Adds `settled_amount`, `settled_at`. |
| `030_backfill_subscription_settlements.sql` | Data backfill for settlements. |

### H.5 Tests reviewed (not executed)

| Test file | Relevance | Notes |
|---|---|---|
| `app/tests/integration_tests/admin_auth_test.py` | Register/login/me/refresh/logout/reset flows | Requires MySQL/Redis; creates and deletes admins; reads OTP secrets from Redis. |
| `admin_people_test.py` | User list/detail/delete; admin list/update/delete; session revocation | Requires MySQL/Redis; creates users/admins. |
| `admin_money_ops_test.py` | Deposit/withdrawal list, filters, confirm/reject, wallet balances | Requires MySQL/Redis; creates users, deposits, withdrawals; mutates wallets. |
| `admin_instruments_test.py` | Instrument CRUD, soft delete, buy/sell after deactivation | Requires MySQL/Redis; creates plans, subscriptions, trades. |
| `admin_trading_test.py` | Admin buy/sell on behalf of a user | Requires MySQL/Redis; creates subscriptions/trades. |
| `plans_integration_test.py` | Plan create/duplicate/expired-token expectations | Contains stale expectations (e.g. `Expired signature` vs current `Access token has expired`) and static tokens not stored in Redis; not a reliable current contract. |
| `plan_pool_test.py`, `money_flow_test.py` | Subscription pool and money-flow behavior | User-facing; reviewed for shared helpers. |
| `user_logout_test.py`, `user_settings_test.py` | User auth/settings | Not admin-specific; reviewed for session/Redis behavior. |
| `app/tests/unit_tests/*` | Plan helpers, Redis key format | No live DB required for some, but not run in this review. |

These tests corroborate many behaviors but are not an executable contract in the current environment. They mutate data and need isolated test databases. Do not run them against production.

### H.6 Source snapshot and re-verification

- Repository: `/Users/roland/Documents/broker-backend`
- Branch: `main`
- Commit: `774539d`
- Existing `ADMIN_API_CONTRACT.md` was untracked at review time.

Useful non-mutating checks:

```bash
git rev-parse HEAD
git status --short

python3 - <<'PY'
from app.main import app
routes = [r for r in app.routes if hasattr(r, "methods")]
for r in routes:
    print(",".join(sorted(r.methods)), r.path)
print("total", len(routes))
PY
```

Expected: 73 total route objects including docs/root; 34 admin-related paths as listed in Section B.1.

To count the admin inventory:

```bash
grep -c '^| [0-9]' ADMIN_API_CONTRACT.md   # table row count check, not authoritative
```

The authoritative count is the route table generated from `app.main`, cross-checked against the six route modules.

### H.7 How to keep this document current

When routes change:

1. Re-run the route enumeration and update Section B.
2. Update the endpoint section and its `file:line` references.
3. Re-check the migration map for new cascades.
4. Re-run only the non-mutating probes, or run integration tests against a disposable database.
5. Update the snapshot commit at the top.

---

## I. Frontend Integration Guidance

### I.1 Client configuration

| Setting | Recommendation |
|---|---|
| Base URL | Read from environment, e.g. `VITE_API_BASE_URL`. Use `https://<backend-host>` only as a placeholder. Never hardcode a production host in source. |
| Auth header | `Authorization: Bearer <access_token>` on every admin route except the six public auth routes. |
| Content type | `application/json` for bodies. |
| Cookies | Not used. Do not set `credentials: "include"`; CORS is configured with `allow_credentials=False`. |
| Timeouts | Use a request timeout (e.g. 15–30 s). Financial and delete operations should not be retried automatically. |
| Error parsing | Try JSON `detail`; fall back to plain text for unhandled `500`. |
| Decimal | Parse money strings into a decimal type. Never use binary floating point for balances. |
| Dates | Parse ISO strings; display with an explicit timezone label until the server timezone is confirmed. |

### I.2 Authentication and session flow

**Login**

1. `POST /admin/login` with email/password.
2. Store the access token in memory and the refresh token in a secure storage mechanism appropriate to the threat model. Avoid `localStorage` if XSS is a concern; there is no HttpOnly-cookie option in this backend.
3. Call `GET /admin/me` to confirm the session and obtain the admin identity.
4. Route to the console.

**Every request**

1. Attach the access token.
2. On `401`, inspect `detail` before refreshing. Refresh only for auth-related details:
   - `Not authenticated`
   - `Invalid token`
   - `Access token has expired`
   - `Token is not valid or has been revoked`
   - `Refresh token has expired` (from the refresh endpoint)
3. If the detail is `Plan title already used.`, do **not** refresh or log out. Show a duplicate-title error.
4. On a real session failure, call `POST /admin/refresh` once with the refresh token, replace the access token, and retry the original request once.
5. If refresh returns `401` or `403`, clear local state and go to login. Do not loop.
6. If two requests fail simultaneously, serialize the refresh (single-flight) so only one refresh call is made.

**Refresh**

- Body: `{"token": "<refresh_token>"}`.
- Response: `{"token": "<new_access_token>"}` only.
- Keep the existing refresh token; it is not rotated.
- A successful refresh overwrites the Redis access slot, so the old access token stops working immediately.

**Logout**

1. `POST /admin/logout` with the current access token.
2. Clear local tokens regardless of the response.
3. If the network call fails, still clear local state; the server-side token may remain until TTL, but the user expects logout.

**Password reset**

1. `POST /admin/forgot-password` with email. Show the returned `timeout` (300 s) in the OTP screen.
2. `POST /admin/verify-otp` with email and a 6-character OTP. On success, keep `password_reset_token` in memory only.
3. `POST /admin/reset-password` with email, new password (8–100), and the reset token.
4. On success, clear tokens and route to login. All old sessions are revoked.

**Session semantics**

- One access token and one refresh token per admin are stored in Redis. Logging in elsewhere invalidates the previous session.
- Deleting or updating an admin revokes that admin's session.
- A Redis flush invalidates all sessions even if JWTs are still time-valid.
- There is no "remember me" or multi-device session list.

### I.3 Error handling matrix

| Status / detail | Likely cause | Recommended UX |
|---|---|---|
| `401 Not authenticated` | Missing/malformed header | Redirect to login (or attach token and retry once). |
| `401 Invalid token` | Malformed JWT | Clear session, login. |
| `401 Access token has expired` | Access TTL elapsed | Refresh once, retry. |
| `401 Token is not valid or has been revoked` | Login elsewhere, logout, admin update/delete, Redis flush | Clear session, login. |
| `401 Plan title already used.` | Duplicate plan title | Show field error on the plan title; **do not log out**. |
| `401 Password is incorrect` | Wrong login password | Generic "Unable to sign in". |
| `401 Invalid credentials` | Unknown login email | Generic "Unable to sign in". |
| `401 Invalid password reset token for this admin` | Reset token does not match email | Restart reset flow. |
| `401 Invalid or expired password reset token` | Redis token missing/expired | Restart reset flow. |
| `403 Admin privileges required.` | Valid non-admin token | Clear session; this UI is admin-only. |
| `404 ... not found` | Missing record, bad FK, or asset no-op | Show "not found" with a refresh action. For asset update, re-fetch and compare before treating as missing. |
| `404 No assets found.` | Empty asset table | Show an empty-state/setup message, not a hard error page. |
| `409 Email already in use.` | Duplicate admin email | Field-level error. |
| `409 Instrument symbol already in use.` | Duplicate symbol | Field-level error. |
| `400 Deposit is not pending or does not exist.` | Already processed or missing | Refresh the queue; do not retry blindly. |
| `400 Withdrawal is not pending or does not exist.` | Already processed or missing | Refresh the queue. |
| `400 Insufficient subscription pool.` | Trade exceeds pool | Show pool/cost and ask for a smaller quantity. |
| `400 Insufficient quantity.` | Sell exceeds held quantity | Show current net quantity. |
| `400 Nothing to update.` | Empty admin patch | Disable submit until a field changes. |
| `400 Admins cannot delete themselves.` | Self-delete | Hide the action for the current admin. |
| `422 ...` | Request validation | Show the single returned message near the relevant field; also validate locally. |
| `500` with JSON detail | Handled server/DB error | Show a generic failure; log the detail for support. Do not expose SQL text to end users. |
| `500` plain text | Unhandled error (e.g. Redis) | Show a generic failure and a retry/refresh action. |

### I.4 Data typing

```ts
// Money is a string in every response. Keep it as a string or a decimal type.
type DecimalString = string;

interface AdminPublic {
  id: number;
  email: string;
  role: "ADMIN" | "USER";
}

interface AdminUserListItem {
  id: number;
  email: string;
  full_name: string;
  username: string | null;
  role: "ADMIN" | "USER";
}

interface Plan {
  id: number;
  title: string;
  min_amount: DecimalString;
  duration: number;
  roi: DecimalString;
  risk_management:
    | "STANDARD"
    | "ADVANCED_HEDGING"
    | "TAILORED_MULTI_LAYER";
  description: string;
  status: "ACTIVE" | "INACTIVE";
  features: string[];
  created_at: string;
  updated_at: string;
}

type DepositStatus = "pending" | "confirmed" | "rejected";
type WithdrawStatus = "pending" | "confirmed" | "rejected";
```

Do not model `amount` as `number`. A value like `"0.10000000"` will lose precision or display inconsistently if converted to a float. Use a decimal library (e.g. `decimal.js`) or integer minor units at the edge.

`current_price` and raw list amounts often have eight decimal places. Format for display only; keep the original string for submissions and comparisons.

### I.5 Screen-to-endpoint mapping

| Screen / action | Endpoints | Notes |
|---|---|---|
| Admin login | `POST /admin/login`, `GET /admin/me` | Show generic login errors. |
| Forgot password | `POST /admin/forgot-password` | Show `timeout`; allow resend only after a client cooldown. |
| Verify OTP | `POST /admin/verify-otp` | 6-character input; handle 400 expiry/invalid distinctly. |
| Reset password | `POST /admin/reset-password` | 8–100 chars; on success go to login. |
| Admin profile | `GET /admin/me`, `PATCH /admin/{id}` | Patching own password revokes the current session; force re-login. |
| User list | `GET /admin/users?limit&offset` | Bare array; no total. |
| User detail | `GET /admin/users/{id}` | PII; restrict access in the UI. |
| Delete user | `DELETE /admin/users/{id}` | Typed confirmation; irreversible cascade. |
| Admin list | `GET /admin/list?limit&offset` | Bare array. |
| Admin detail | `GET /admin/{id}` | |
| Create admin | `POST /admin/register` | **Do not expose** until the endpoint is protected/provisioned. |
| Edit admin | `PATCH /admin/{id}` | Any admin can edit any other; warn. |
| Delete admin | `DELETE /admin/{id}` | Block self; warn about last admin. |
| Deposit queue | `GET /wallet/admin/deposits?status=pending` | Bare array; raw amounts. |
| Confirm/reject deposit | `POST /wallet/deposits/{id}/confirm` or `/reject` | Disable while in flight; re-read on 500. |
| Withdrawal queue | `GET /wallet/admin/withdrawals?status=pending` | Bare array; raw amounts. |
| Confirm/reject withdrawal | `POST /wallet/withdrawals/{id}/confirm` or `/reject` | Show destination and amount; irreversible status change. |
| Plan list | `GET /plan` | Admin sees all statuses; wrapped in `plans`. |
| Create plan | `POST /plan/create` | Duplicate title is `401`; do not log out. |
| Edit plan | `POST /plan/update` | Full replacement; features replace the set. |
| Asset list | `GET /assets` | `404` means empty table; no paging. |
| Create asset | `POST /assets` | No symbol uniqueness; warn on duplicates. |
| Edit asset | `PUT /assets/{id}` | Full replacement; no-op may return `404`. |
| Delete asset | `DELETE /assets/{id}` | Hard delete with financial cascades. |
| Instrument list | `GET /instruments?is_active&limit&offset` | Admin-only; includes inactive by default. |
| Create instrument | `POST /instruments` | Category must exist. |
| Edit instrument | `PUT /instruments/{id}` | Partial merge; use `is_active` to toggle. |
| Delete instrument | `DELETE /instruments/{id}` | Soft delete; idempotent. |
| Buy for user | `POST /portfolio/admin/buy/{user_id}` | Needs user ID and subscription ID; no admin subscription lookup exists. |
| Sell for user | `POST /portfolio/admin/sell/{user_id}` | Same; inactive instruments can be sold. |

**Trading screen gap:** there is no admin endpoint to list a user's subscriptions or pool. The operator must obtain a valid `subscription_id` from another system or the user. Do not guess IDs. Consider adding an admin subscription read endpoint before building this screen.

### I.6 Dangerous-action UX

**User deletion**

- Show the user's email/ID and a warning that wallet, deposits, withdrawals, subscriptions, and trades will be erased.
- Require typing the email or a confirmation phrase. Do not use a single "OK" click.
- There is no undo and no server-side dependency summary. You cannot reliably show counts without additional endpoints.
- After success, remove the row and refresh the first page.

**Asset deletion**

- Warn that deposits/withdrawals and crypto destination details using the asset may be deleted.
- Prefer `PUT /assets/{id}` with `is_active:false` if the goal is to stop new use, but note that deposit validation currently accepts inactive assets, so deactivation is not a hard block.
- Require typed confirmation. Do not offer a bulk delete.

**Deposit/withdrawal confirm/reject**

- Show the exact amount, user ID, asset, and (for withdrawals) destination before acting.
- Disable the action after the first click. Do not auto-retry a POST on timeout; re-fetch the record/list and check its status.
- A `400 not pending` usually means another admin already processed it. Refresh the queue and show an informational message, not a scary error.
- A `500` may still mean the operation committed. Re-read the status before retrying.

**Admin edit/delete**

- Hide self-delete; the backend returns `400 Admins cannot delete themselves.`
- Warn that editing another admin's password revokes their session and can lock them out.
- Warn that deleting the last other admin may leave no operator; the backend has no last-admin guard.
- Do not expose public admin registration as an "invite" flow.

**Plan create**

- Handle `401` with `detail: "Plan title already used."` as a field error. Never let a generic 401 interceptor log out the admin.

**Asset update**

- Fetch the current asset and only enable save when something changed. If the backend returns `404 Asset '<id>' not found.` after a no-op, re-fetch before showing "deleted".

### I.7 Pagination UI

- Use a "Load more" or numbered pages based on `offset`, not a total count.
- Default page size 10–50; never exceed 100.
- Stop when a page has fewer rows than the requested limit.
- Reset offset when filters change.
- After create/delete, reset to the first page.
- Do not client-sort across pages; ask for a backend sort parameter if needed.
- For pending queues, show a "refresh" control and a last-updated timestamp; there is no realtime feed.

### I.8 Suggested API client behavior (illustrative)

```ts
type ApiError = { detail?: string };

async function adminFetch(
  path: string,
  init: RequestInit = {},
  retry = true
): Promise<Response> {
  const access = getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status !== 401 || !retry) return res;

  const body = (await res.clone().json().catch(() => ({}))) as ApiError;
  const sessionErrors = new Set([
    "Not authenticated",
    "Invalid token",
    "Access token has expired",
    "Token is not valid or has been revoked",
    "Refresh token has expired",
  ]);

  if (!sessionErrors.has(body.detail ?? "")) {
    // Business 401, e.g. "Plan title already used."
    return res;
  }

  const refreshed = await refreshOnce();
  if (!refreshed) {
    clearSession();
    redirectToLogin();
    return res;
  }
  return adminFetch(path, init, false);
}
```

This is illustrative, not production code. It intentionally excludes the duplicate-plan detail from the refresh path and uses single-flight refresh in `refreshOnce()`.

### I.9 Integration test checklist

Before shipping the console, verify against a disposable environment:

1. Login → `/admin/me` → refresh → logout → old token rejected.
2. Password reset with a real OTP from the test mailbox or Redis, then old session rejected.
3. Non-admin user token gets `403` on every admin route.
4. Missing token gets `401 Not authenticated` with `WWW-Authenticate`.
5. Duplicate plan title returns `401` and the client does not log out.
6. Empty assets returns `404` and the UI shows an empty state.
7. Asset no-op update returns `404` and the UI re-fetches.
8. Deposit confirm/reject twice: second returns `400`.
9. Withdrawal confirm/reject twice: second returns `400`.
10. Deposit confirm credits exactly the displayed amount; check 8-decimal and 2-decimal edge cases.
11. User delete cascades in a disposable DB and the UI warns correctly.
12. Asset delete cascades in a disposable DB and the UI warns correctly.
13. Instrument deactivate blocks buy but allows sell; reactivate restores buy.
14. Buy/sell charges/credits the subscription pool, not the wallet.
15. Pagination stops correctly and resets on filter change.
16. All money values remain strings end-to-end.

### I.10 Production readiness blockers

Do not expose this admin API to real operators until at least these are addressed:

1. Protect or remove public admin registration.
2. Fix IDOR on deposit/withdrawal detail or exclude those routes.
3. Add audit logging for financial and destructive actions.
4. Add rate limiting/lockout for auth and OTP.
5. Add idempotency and wallet integrity guards.
6. Decide and document soft-delete/retention for users and assets.
7. Fix the duplicate-plan `401` and the asset/deposit error inconsistencies.
8. Restrict admin-to-admin account changes and add last-admin protection.
9. Confirm TLS, CORS origins, secret management, and database backups.
10. Run the integration suite against an isolated test environment.

---

## Completion Report

**Deliverable:** `/Users/roland/Documents/broker-backend/ADMIN_API_CONTRACT.md` (replaced the previous untracked file).

**Coverage**

- **34 admin-related routes** documented, matching the current implementation:
  - 8 admin auth/account routes
  - 3 user-management routes
  - 4 admin-account routes
  - 6 wallet admin/review routes
  - 3 plan routes
  - 4 asset routes
  - 4 instrument routes
  - 2 admin trading routes
- **2 related non-admin routes** documented separately in the appendix, not counted in the 34: `GET /wallet/deposit/{id}`, `GET /wallet/withdrawal/{id}`.
- **6 public** admin-auth routes, **26 admin-only** routes, **2 shared any-auth** reads (`GET /plan`, `GET /assets`).

**Required sections**

- A. Overview: purpose, scope, routing, auth, conventions, status semantics, startup.
- B. Complete route inventory, counts, ordering, absent capabilities.
- C. Detailed endpoint specifications for all 34 routes plus the 2 related routes.
- D. Shared models, enums, serialization and validation rules.
- E. Database tables, cascades, financial operations, Redis/email side effects, audit/idempotency gaps, partial commits.
- F. Pagination, filtering, sorting, empty-result behavior.
- G. Security, financial, and contract risks with severity and prioritization.
- H. Source traceability by route, service, model, migration, and test.
- I. Frontend integration guidance, error matrix, data typing, screen mapping, dangerous-action UX, and production blockers.

**Critical findings documented**

- Public `POST /admin/register` creates a privileged admin with tokens.
- Any-auth, no-ownership `GET /wallet/deposit/{id}` and `GET /wallet/withdrawal/{id}`.
- No audit log, idempotency, rate limiting, MFA, or approval workflow.
- Hard-delete cascades for users and assets erase financial history.
- Missing wallet rowcount/non-negative guards on deposit credit and withdrawal lock/unlock.
- `POST /plan/create` duplicate title returns `401`.
- `GET /assets` empty table returns `404`.
- `PUT /assets/{id}` no-op returns `404`.
- `GET /wallet/deposit/{id}` missing record returns `500`.
- All success responses are `200`; no `201`/`204`.
- Raw 8-decimal list amounts vs 2-decimal detail amounts.
- Commit-before-Redis windows can leave durable changes after a `500`.

**Verification and limitations**

- Route inventory was generated by importing `app.main`; the source modules, services, models, queries, migrations, and admin integration tests were reviewed.
- Non-mutating probes confirmed the missing-auth response, validation format, and extra-field behavior.
- The integration tests were **not executed**: they require live MySQL/Redis and create/delete users, admins, deposits, withdrawals, plans, instruments, and trades.
- Concurrency, datetime timezone behavior, runtime cascades, and SMTP delivery are marked **Inferred** or **Unverified** in the document.
- **Probe incident:** one extra-field registration probe reached the service and created a synthetic admin row because the service commits before Redis token storage. The probe row (`id=1333`, synthetic `a@b.com`) was deleted immediately, and a follow-up query confirmed no matching row remains. No user, wallet, deposit, withdrawal, plan, instrument, trade, or other business data was modified. This is disclosed because it also confirms the partial-commit risk; it was not an intentional mutation test.

**Application changes**

- No application code, route, service, model, migration, configuration, dependency, or behavior was changed.
- The only repository change is `ADMIN_API_CONTRACT.md`, which was already untracked and is now replaced.
- `git status --short` should show only `?? ADMIN_API_CONTRACT.md`.

**Result:** the admin API contract is complete for the current `main` snapshot at commit `774539d`, with implementation-level detail, exact error strings, source references, and explicit frontend risks. It should not be treated as a production security sign-off: the public admin registration and the two IDOR detail routes are release blockers.

