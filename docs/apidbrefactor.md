# Guild-Specific API Configuration System

## Implementation Plan v4

A system that allows Discord server administrators to configure their own API keys and models on a per-guild basis with password protection and env file upload support. Global keys and global .env are disabled -- each guild provides its own .env.

---

## Security Architecture (Summary)

- Discord Administrator permission gate + optional allowlist
- Per-guild password (bcrypt/argon2) + per-user auth sessions
- API keys encrypted at rest (Fernet), ENCRYPTION_KEY required
- Masked key display only (last 4 chars)
- Rate limiting on auth + password operations
- Audit log for all sensitive changes

---

## Stage 0 -- Requirements and Threat Model

### Supported Providers and Keys

| Provider | Allowed Keys | Recommended Models (full names) |
|----------|--------------|----------------------------------|
| Gemini | GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 | gemini-2.5-flash-lite, gemini-2.5-flash |
| OpenRouter | OPENROUTER_API_KEY | cognitivecomputations/dolphin-mistral-24b-venice-edition:free, nousresearch/hermes-3-llama-3.1-405b:free, nousresearch/deephermes-3-mistral-24b-preview, mistralai/mistral-small-3.1-24b-instruct:free, deepseek/deepseek-chat |

### Allowed Keys Whitelist (env upload)

```python
ALLOWED_ENV_KEYS = {
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "OPENROUTER_API_KEY",
    "GEMINI_MODEL",
    "OPENROUTER_MODEL",
    "OPENROUTER_FALLBACK_MODELS",
}
```

### Global Keys Disabled

- No global .env or shared API keys.
- Each guild must upload its own .env.
- Provider usage should fail fast when required keys are missing.

### .env.example Distribution

- Use the existing template at discord_bot/.env.example.
- Add /config env example to send the template as an attachment (ephemeral).

### Env to DB Mapping (Explicit)

| Env Key | DB Field | Encrypted |
|---------|----------|-----------|
| GEMINI_API_KEY | guild_config.gemini_api_key | Yes |
| GEMINI_API_KEY_2 | guild_config.gemini_api_key_2 | Yes |
| GEMINI_API_KEY_3 | guild_config.gemini_api_key_3 | Yes |
| OPENROUTER_API_KEY | guild_config.openrouter_api_key | Yes |
| GEMINI_MODEL | guild_config.gemini_model | No |
| OPENROUTER_MODEL | guild_config.openrouter_model | No |
| OPENROUTER_FALLBACK_MODELS | guild_config.openrouter_fallback_models | No |

### Permission Model

- Discord Admin = Discord Administrator permission flag + optional allowlist.
- Sensitive operations: view keys, upload env, change model, toggle evil mode.

### Command Auth Requirements

| Command | Admin Required | Auth Session Required |
|---------|----------------|-----------------------|
| /config auth | Yes | No |
| /config password set | Yes | No |
| /config password change | Yes | Yes |
| /config password reset | Yes (bot owner) | No |
| /config keys view | Yes | Yes |
| /config keys clear | Yes | Yes |
| /config model view | Yes | No |
| /config model set | Yes | Yes |
| /config env upload | Yes | Yes |
| /config env example | Yes | No |
| /config toggle evil | Yes | Yes |

### Password Recovery

If a guild admin loses the config password, the server owner must contact the bot owner for a manual reset.

### Data Storage Rules

- Store only encrypted key values (never plaintext).
- Audit entries store masked values only.
- ENCRYPTION_KEY is required; bot must hard-fail if missing.
- updated_at must be updated on every write to guild_config.

### Env Upload Merge Policy

- Upload merges values: only keys present in the uploaded file are updated.
- Missing keys are left unchanged.
- Empty value clears the stored key for that field.

### Model Validation Default

- Default behavior: warn if model is not in the recommended list, but allow it.
- Optional strict mode: reject non-recommended models (config flag).

### Deliverables

- Final list of supported keys/models
- Permissions matrix
- Security behaviors document
- .env.example template + /config env example

---

## Stage 1 -- Data Model and Migrations

### Tables

```sql
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,

    -- Encrypted API keys
    gemini_api_key TEXT,
    gemini_api_key_2 TEXT,
    gemini_api_key_3 TEXT,
    openrouter_api_key TEXT,

    -- Model preferences
    gemini_model TEXT DEFAULT 'gemini-2.5-flash-lite',
    openrouter_model TEXT DEFAULT 'cognitivecomputations/dolphin-mistral-24b-venice-edition:free',
    openrouter_fallback_models TEXT,

    -- Toggles
    evil_mode_enabled INTEGER DEFAULT 0,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS guild_admin_auth (
    guild_id INTEGER PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    password_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS guild_auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    password_version INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS guild_config_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    field TEXT,
    old_value TEXT,
    new_value TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Notes:
- Update updated_at on any write to guild_config (application-side or trigger).

### Deliverables

- DB migration in utils/db_handler.py

---

## Stage 2 -- Crypto and Password System

### Encryption Key Handling (Hard Fail)

```python
import os
from cryptography.fernet import Fernet
from utils.logger import get_logger

logger = get_logger(__name__)

class KeyEncryption:
    def __init__(self):
        master_key = os.getenv("ENCRYPTION_KEY")
        if not master_key:
            raise RuntimeError(
                "ENCRYPTION_KEY not set! Required for guild API key storage. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self.fernet = Fernet(master_key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()

    def mask_key(self, key: str) -> str:
        if len(key) <= 8:
            return "****"
        return f"****...****{key[-4:]}"
```

### Password and Session System

- Use bcrypt or argon2.
- Password change increments password_version to invalidate sessions.
- Per-user sessions expire after 15 minutes.
- Cleanup job deletes expired sessions on a schedule.

### Rate Limiting (Per-User)

- 5/min per user per guild for /config auth and password operations.

### Deliverables

- utils/encryption.py with hard-fail on missing key
- utils/auth.py with per-user sessions + cleanup
- Rate-limit helper (per-user)

---

## Stage 3 -- Command Surface

### Command Structure

```
/config
├── password
│   ├── set <password>              -- Set initial password
│   ├── change <old> <new>          -- Change password (invalidates all sessions)
│   └── reset                       -- Force reset (bot owner only)
├── auth <password>                 -- Open 15-min per-user session
├── keys
│   ├── view                         -- View masked keys
│   └── clear                        -- Remove all stored keys
├── model
│   ├── view                         -- View current models
│   └── set <provider> <model>       -- Set model (convenience)
├── env
│   ├── upload                       -- Upload .env file
│   └── example                      -- Send .env.example template
└── toggle
    └── evil                         -- Enable/disable evil mode
```

Notes:
- Key changes are done via env upload. No direct /config keys set.
- /config model set is a convenience alternative to env upload.

### Deliverables

- cogs/config.py with all commands
- Model validation warnings

---

## Stage 4 -- Env File Upload and Parsing

### Command

/config env upload -- accepts .env attachment

### Validation Rules

| Rule | Value |
|------|-------|
| Max file size | 16 KB |
| Allowed keys | Whitelist only (Stage 0) |
| Duplicates | Reject |
| Unknown keys | Reject with list |
| Mapping | Enforced (env key -> DB field) |
| Model values | Warn if not recommended (optional strict mode) |

### Parsing Rules

- Accept UTF-8 with optional BOM.
- Accept optional leading export (export KEY=...)
- Support quoted values and inline comments (use python-dotenv or equivalent parser).
- Ignore blank lines and comment lines.

### Implementation Sketch

```python
ENV_TO_DB = {
    "GEMINI_API_KEY": "gemini_api_key",
    "GEMINI_API_KEY_2": "gemini_api_key_2",
    "GEMINI_API_KEY_3": "gemini_api_key_3",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "GEMINI_MODEL": "gemini_model",
    "OPENROUTER_MODEL": "openrouter_model",
    "OPENROUTER_FALLBACK_MODELS": "openrouter_fallback_models",
}

@app_commands.command(name="upload")
async def env_upload(self, interaction: discord.Interaction, file: discord.Attachment):
    # 1) Check permissions + auth session
    # 2) Validate file size + extension
    # 3) Parse lines; reject duplicates + unknowns
    # 4) Normalize OpenRouter aliases to full IDs (if provided)
    # 5) Warn if model not in recommended list (or reject in strict mode)
    # 6) Encrypt API keys and store using ENV_TO_DB mapping
    # 7) If value is empty, clear that field
    # 8) Respond with masked summary (ephemeral)
    # 9) Audit log event (field="count", new_value=str(len(parsed)))
```

### Deliverables

- Env parser with whitelist + duplicate detection
- File size + format checks
- Encrypted storage
- Masked summary response

---

## Stage 5 -- API Manager Integration

### Multi-Key Rotation Strategy (Gemini)

- Use gemini_api_key, then gemini_api_key_2, then gemini_api_key_3.
- If all keys are missing or exhausted, return a clear error for the guild.

### OpenRouter Fallback Models

- Parse openrouter_fallback_models as comma-separated list.
- Accept full IDs and aliases, normalize to full IDs on storage.

### Key Requirements

- No global fallback keys.
- If a guild has no key configured for a provider, provider usage fails fast with an actionable error.

### Deliverables

- Gemini multi-key rotation
- OpenRouter fallback parsing
- Model preference integration
- Zero plaintext logging

---

## Stage 6 -- Security Hardening and Auditing

### Audit Events

- key_clear, model_change, env_upload, auth_success, auth_failure, password_set, password_change
- Store masked values only (last 4 chars)

### Rate Limiting Coverage

- /config auth, /config password set, /config password change

### Additional Hardening

- Expired session cleanup job
- Audit retention policy (e.g., keep 90 days, prune daily)
- All sensitive responses are ephemeral

### Deliverables

- Audit writes on all changes
- Rate limiting on auth operations
- Session cleanup + audit retention
- Optional: /config audit

---

## Stage 7 -- Test Plan and Rollout

### Unit Tests

- Encryption/decryption roundtrip
- Hard-fail on missing ENCRYPTION_KEY
- Password hash + verify
- Key masking
- Model validation warnings
- OpenRouter alias normalization

### Integration Tests

- Per-user auth session isolation
- Session invalidation on password change
- Env upload validation (size, keys, duplicates)
- Env upload merge behavior (partial update, empty value clears)
- Multi-key rotation
- No global fallback behavior
- Fallback models parsing

### Manual Smoke Checklist

- Set password for first time
- Authenticate with correct/wrong password
- Rate limit kicks in after 5 wrong attempts (per-user)
- Password change invalidates sessions
- Upload .env with valid keys
- Upload .env with unknown keys (rejected)
- Upload .env with duplicate keys (rejected)
- Upload .env with empty value (clears key)
- Bot uses guild keys and fails fast without them
- Model warnings appear for non-recommended models

### Deliverables

- Test suite
- Smoke checklist
- Deploy instructions