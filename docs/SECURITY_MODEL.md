# FormatAI Security & Client-Side User Settings Isolation Model

This document specifies the security architecture, threat model, and data isolation guarantees implemented across the FormatAI application.

---

## 1. Core Architectural Separation

FormatAI enforces a strict architectural boundary between **Client-Local Settings** and **Server-Side Application Configuration**:

| Characteristic | Client-Local Settings | Server-Side Application Configuration |
| :--- | :--- | :--- |
| **Scope** | Bound to the individual user's browser, profile, and device. | Bound to the container environment and server host. |
| **Stored Data** | • Personal AI provider API keys<br>• Per-provider enabled/disabled states<br>• Selected AI provider & model<br>• Document style presets & typography rules<br>• Output filenames & export preferences<br>• UI layout, font size, & preview modes<br>• Academic skill preferences | • System defaults & fallback limits<br>• Host-level environment keys (`.env`)<br>• Server port & CORS origins (`ALLOWED_ORIGINS`)<br>• Static template definitions |
| **Storage Medium** | Browser `localStorage` (`formatai_v2_user_settings`) or in-memory fallback. | Ephemeral container memory & `.env` configuration. |
| **Sharing Between Users** | **Strictly Impossible**: No shared server storage, no database, no cross-profile access. | Shared static read-only server parameters. |
| **Persistence on Server** | **Zero Persistence**: Transmitted only per-request; never saved to disk, database, or server logs. | Read-only during process lifetime. |

---

## 2. The Four Pillars of the Security Model

To prevent ambiguity, FormatAI clearly distinguishes between **isolation**, **confidentiality**, **encryption**, and **server-side exposure**:

### A. Isolation (Partitioning & Separation)
- **Same-Origin Policy (SOP)**: The web browser isolates `localStorage` by scheme, domain, and port (`origin`). No third-party domain or untrusted external origin can access FormatAI's storage keys.
- **Browser Profile Partitioning**: Different browser profiles (e.g. Chrome Profile 1 vs. Chrome Profile 2, or Firefox vs. Chrome) maintain physically separate SQLite/leveldb directories on disk. User A's browser profile cannot view or inherit User B's browser profile data.
- **Client Workspace Profiles**: Inside FormatAI, users can create multiple distinct workspace profiles (e.g., "Grant Proposals", "Personal Journal", "Classroom Workstation"). Each profile maintains an isolated namespace for keys, options, and preferences.
- **Stateless Backend Isolation**: The FormatAI backend is completely stateless with respect to users. There is no user table, session database, or cookie-based state. Requests from User A cannot influence or leak into requests from User B.

### B. Confidentiality (Protection Against Eavesdropping)
- **In Transit (Client ↔ Server)**: All communication between the client browser and the FormatAI backend is encrypted via Transport Layer Security (TLS 1.3 / HTTPS). Eavesdroppers on the local network or internet cannot intercept document text, prompts, or API keys.
- **In Transit (Server ↔ Upstream AI)**: The backend proxy forwards prompts and scoped credentials to upstream providers (Google, Groq, Mistral, OpenAI, Cohere, Hugging Face) exclusively over HTTPS.
- **Strict Per-Request Transmission**: Client API keys are only transmitted when an explicit AI generation or connection validation request is submitted. They are never sent during document formatting or static preview.

### C. Encryption (Client-Side Storage Reality)
> **CRITICAL SECURITY NOTICE**: FormatAI **does not claim that browser `localStorage` is cryptographically secure**.

- **Plaintext at Rest**: Standard browser `localStorage` is stored in **unencrypted plaintext** on the user's local disk filesystem within the browser application data folder.
- **Physical Access Threat**: Anyone with physical access to the machine, root/administrator file permissions, or an unauthenticated session on the operating system user account can inspect the local storage files.
- **Recommendation for Public/Shared Terminals**:
  - Do not leave master production API keys saved on shared computers (libraries, public labs).
  - Use the built-in **"Purge All Client Data & Reset"** button before ending a session on a shared terminal.
  - Alternatively, use ephemeral per-session keys or scoped restricted API keys.

### D. Server-Side Exposure (Zero Persistence Guarantee)
- **No Shared Server Store**: The server contains no database (PostgreSQL, MySQL, SQLite, Mongo, Redis) for user preferences or credentials.
- **Volatile Execution Only**: User-provided API keys and base URLs received in POST payloads are held in volatile RAM only for the duration of the upstream HTTP call and are dereferenced immediately afterward.
- **Automatic Credential Sanitization**: The server's error handler passes all exceptions through `sanitize_credentials()`. Any string matching `sk-...`, `gsk_...`, `Bearer ...`, or the caller's specific key is replaced with `[REDACTED]` in server logs and HTTP error responses.

---

## 3. Data Flow Diagram

```
+-------------------------------------------------------------------------+
|                              CLIENT BROWSER                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                  FormatAI React UI (Components)                   |  |
|  +---------------------------------+---------------------------------+  |
|                                    | (Read / Write)                     |
|                                    v                                    |
|  +-------------------------------------------------------------------+  |
|  |                 UserSettingsContext & Hook Layer                  |  |
|  |             (Profile Switcher, Redacted JSON Export)              |  |
|  +---------------------------------+---------------------------------+  |
|                                    | (Origin-Isolated IO)               |
|                                    v                                    |
|  +-------------------------------------------------------------------+  |
|  |             Browser localStorage: formatai_v2_user_settings       |  |
|  |             [Plaintext at Rest; Isolated by Origin & Profile]     |  |
|  +---------------------------------+---------------------------------+  |
+------------------------------------|------------------------------------+
                                     |
               HTTPS (TLS) POST /api/ai/generate
               Ephemeral payload: { prompt, api_key, model }
                                     |
                                     v
+------------------------------------+------------------------------------+
|                         FASTAPI BACKEND SERVER                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                      Stateless Route Handlers                     |  |
|  |         (No user DB, no session tables, zero user storage)        |  |
|  +---------------------------------+---------------------------------+  |
|                                    |                                    |
|  +---------------------------------v---------------------------------+  |
|  |                    Ephemeral Provider Adapters                    |  |
|  |          (Key held in RAM for request duration; Redacted logs)    |  |
|  +---------------------------------+---------------------------------+  |
+------------------------------------|------------------------------------+
                                     |
               HTTPS (TLS) to Upstream AI Provider (Google, Groq, etc.)
                                     v
                        [Upstream Model Response]
```

---

## 4. Automated Testing & Verification

FormatAI provides automated tests for settings isolation on both frontend and backend:

1. **Client-Side Test Suite (`scripts/test_settings_isolation.ts`)**:
   - `npm run test:settings`
   - Verifies profile creation, complete isolation of all 8 user-local data categories between User A and User B, absence of global window pollution, storage corruption self-healing, and full data purge.

2. **Backend Statelessness & Isolation Test Suite (`tests/test_settings_isolation.py`)**:
   - `python3 -m pytest tests/test_settings_isolation.py`
   - Verifies absence of shared user settings routes, guarantees User A's API key does not persist for User B, ensures custom base URLs are ephemeral, and validates credential redaction on errors.
