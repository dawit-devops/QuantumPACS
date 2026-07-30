# Backend Requirements: Authentication & Authorization

## Context

Login and session management for all 7 QuantumPACS personas (Radiologist, Technologist, Clinician, PACS Admin, Modalities, RIS, EMR). Supports interactive user login (username/password + SSO), machine-to-machine API key auth, and ephemeral view-only share-key access for referring clinicians.

Success looks like: any user can authenticate via their role-appropriate method, access is transparently maintained across page loads, and unauthorized access is reliably rejected with clear feedback.

---

## Screens/Components

### Login Form

**Purpose**: Authenticate all interactive personas (Radiologist, Technologist, Clinician, PACS Admin). Entry point for the application.

**Data I need to display**:
- List of SSO/OAuth providers (each with a display name and icon URL) rendered as "Sign in with {Provider}" buttons
- Lockout countdown timer — remaining seconds before the user can attempt again
- Login error messages: invalid credentials, account locked, account expired, session expired
- Tenant identifier input (if multi-tenant and not derivable from username)

**Actions**:
- Submit username + password → establishes an authenticated session; returns user profile (id, username, role name, permissions list, tenant_id, admin flag), access token, refresh token, expiry timestamps
- Click SSO provider button → redirects browser to the identity provider's authorization URL; after callback, establishes session and redirects to home
- Dismiss error message → clears the displayed error

**States to handle**:
- **Initial**: Empty form ready for input; lockout timer at 0; all SSO buttons visible; submit enabled
- **Loading**: Spinner overlay on submit button; all form inputs disabled; SSO buttons disabled
- **Error — invalid credentials**: Inline error message above the form (not a toast); focus set on password field; form remains filled
- **Error — account locked/expired**: Distinct error message; no retry possible; may include contact-admin instruction
- **Lockout**: Countdown display showing "Retry in Xs"; submit button disabled; form inputs may remain editable but submission blocked; SSO buttons remain enabled (lockout is password-only)
- **SSO redirect**: Browser navigates away; no UI state to manage
- **Success**: Redirect to application home page; full user profile available to the app

**Business rules affecting UI**:
- Lockout uses exponential backoff: `2^(attempts-1)` seconds, capped at 30s max; persisted client-side in localStorage AND enforced server-side; SSO attempts bypass this counter
- Lockout countdown must remain accurate across page refreshes (persist attempt timestamp + count)
- Access tokens live ~1 hour; refresh tokens live ~14 days
- Concurrent session limit: not strictly enforced, but refresh tokens are individually invalidatable
- SSO redirect may be instant or show an interstitial — backend controls the redirect URL

---

### Share-Key Access

**Purpose**: Allow referring Clinicians and external physicians to view studies without any login or account. Accessed via a URL parameter, no JWT required.

**Data I need to display**:
- DICOM images for the shared study (viewer renders in cornerstone3D)
- Basic study/patient metadata (patient name, study date, modality, description)
- Explicitly **no** annotation tools, no data tab, no share tab, no download buttons, no report access

**Actions**:
- Navigate to URL with `?key=<share_key>` → viewer loads in restricted read-only mode
- Manipulate images: pan, zoom, window/level, scroll through series, play cine
- Cannot annotate, cannot save state, cannot download originals, cannot access any other study
- Cannot navigate to any other page in the application (no sidebar, no top nav except maybe a "Back to referring portal" link)

**States to handle**:
- **Valid key**: Viewer renders with limited toolbar; user is anonymous; banner or indicator showing "View-only access"
- **Expired key**: Redirect to login page with a message: "This shared link has expired. Please request a new link."
- **Invalid key (malformed or revoked)**: Show error page or toast: "Invalid or revoked share link"
- **Key present + user already logged in**: Ignore the share-key mode; render full normal application (logged-in user takes precedence)
- **Loading**: Spinner while the study metadata and images load via the key

**Business rules affecting UI**:
- No JWT required; no user identity is established
- Share key is a securely random string tied to a specific study/dataset
- Duration is configured at share-creation time (hours); enforced server-side on every image request
- UI must never expose the share key value to the user
- Restored from URL parameter on page load; no localStorage persistence

---

### Session Management

**Purpose**: Maintain authenticated state across page loads for all interactive personas. No dedicated UI screen — this is a cross-cutting behavior.

**Data I need**:
- Access token (short-lived JWT) for API authorization headers
- Refresh token (longer-lived, opaque or JWT) for silent token refresh
- User profile: id, username, role name, permissions list, tenant_id, admin boolean
- Token expiry timestamps (both access and refresh) for proactive refresh scheduling

**Actions**:
- **Page load**: Check for existing token in localStorage; validate locally (check expiry); if expired, attempt silent refresh via refresh token; if refresh also expired, clear and redirect to login
- **Silent refresh**: When access token is within a configurable threshold of expiry (e.g., 5 minutes), use refresh token to obtain a new access token + new refresh token; update localStorage; no user-visible interruption
- **Logout**: Clear tokens from localStorage; POST to server to invalidate refresh token server-side; redirect to login
- **Force logout on permission change**: If tokens are invalidated server-side (e.g., role change), next API call returns 401 → trigger silent refresh → if refresh also fails, clear session

**States to handle**:
- **Authenticated**: Normal full app rendering; tokens present and valid
- **Unauthenticated**: No tokens on page load; redirect immediately to `/login`
- **Token refreshing**: Brief in-flight state; no loading spinner or flash — the refresh happens before the API call that triggered it, or on a timer
- **Refresh failed (refresh token expired/invalidated)**: Clear tokens; redirect to login; no error toast (unexpected but handled gracefully)
- **Concurrent tab conflict**: If one tab refreshes tokens, other tabs either detect the new token via storage event or handle 401 gracefully

**Business rules affecting UI**:
- Token refresh must be transparent — no loading states, no page flicker
- Permission changes (role change, tenant change) invalidate existing tokens server-side
- Logout from one session should not affect other sessions unless the refresh token pool is shared (server decides strategy)
- Access token expiry is enforced server-side — UI never trusts local expiry alone
- On API 401, UI should attempt exactly one silent refresh before giving up (prevent infinite loops)

---

### API Key Authentication (Machine Clients)

**Purpose**: Allow automated clients (Modalities pushing studies, RIS/EMR integrations) to authenticate without a browser session.

**Data I need to display**: No UI — this is background behavior.

**Actions**: Client includes `X-API-Key` header on requests; server authenticates and authorizes; no frontend interaction.

**States to handle**: N/A for frontend.

**Business rules**:
- API keys are long-lived, revocable, and scoped to specific permissions
- API key usage is recorded in audit logs (may surface in Admin UI later)
- No token refresh needed; key is static

---

## Uncertainties

- [ ] Should share-key mode allow viewing a single series or the whole study? UI implications for series selector visibility.
- [ ] How granular is the password lockout? Per-IP, per-username, or both? Affects whether we display it as "your account" or "this network" message.
- [ ] Is there a maximum concurrent sessions limit per user? Affects whether we show a "sessions" list UI.
- [ ] Should API key usage be visible as per-request audit trail or summary stats? Affects future Admin screens.
- [ ] What happens to share-key access when the study is deleted? Presumably the key becomes invalid — but does the user get a 404 or a "Study no longer available" message?
- [ ] For SSO, does the backend handle the entire OAuth callback, or does the frontend receive an auth code and exchange it? This determines whether the login page navigates away and returns, or handles an intermediate step.

## Questions for Backend

- What's the token refresh flow — does the backend return a new refresh token each time (refresh rotation), or is the same refresh token reused?
- For SSO providers, does the backend handle the OAuth callback (redirect → backend → redirect to app with token) or does the frontend need to exchange the auth code?
- Should I display remaining time on share-key links in the UI (e.g., in a Share dialog when creating the link)? Or is that only shown in the backend email/notification?
- Is there (or will there be) a way to list active sessions for a user? Needed for a "Log out all devices" feature we may build later.
- For the tenant identifier on login — should we show a tenant input field, or is tenant derived from the username domain/email suffix?
- When a user's role or permissions change while they have an active session, should we expect them to be forcibly logged out, or should their existing tokens remain valid until they expire?

## Discussion Log

- *(To be filled after backend review)*