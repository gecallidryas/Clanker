# Free API Key Safety & Setup Guide

## How Context Is Preserved

**Context is NOT tied to the API key.** The Gemini API is stateless - each request is independent.

The bot maintains conversation context by:
1. Storing message history in SQLite database
2. Constructing conversation history in the prompt sent to the AI
3. Including previous messages and context in each request

**Switching API keys does NOT affect conversation quality.** The bot will continue to understand context because it's embedded in the prompt, not stored by Google.

---

## Setting Up Free Gemini API Keys

### Step 1: Create Multiple Google Accounts
Create 3-5 Google accounts using different emails. Each account gets **15 requests/minute** for free.

### Step 2: Generate API Keys
For each account:
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with that account
3. Click "Create API Key"
4. Copy the key

### Step 3: Configure Your .env File
```env
# Set to "free" for proactive key rotation
GEMINI_KEY_TYPE=free

# Add all your free API keys
GEMINI_API_KEY=your_key_from_account_1
GEMINI_API_KEY_2=your_key_from_account_2
GEMINI_API_KEY_3=your_key_from_account_3
GEMINI_API_KEY_4=your_key_from_account_4
GEMINI_API_KEY_5=your_key_from_account_5
```

### Capacity Calculator
| Free Keys | Requests/Minute |
|-----------|-----------------|
| 1 key     | 15 RPM          |
| 3 keys    | 45 RPM          |
| 5 keys    | 75 RPM          |
| 10 keys   | 150 RPM         |

---

## How Rotation Works

### Free Mode (`GEMINI_KEY_TYPE=free`)
- Rotates to a **different key on every request**
- Distributes load evenly across all keys
- Minimizes chance of hitting any single key's rate limit

### Paid Mode (`GEMINI_KEY_TYPE=paid`)
- Only switches keys when hitting rate limits or errors
- Uses the same key until it fails
- Better for paid keys with higher limits

---

## Security Notes

- API keys are **encrypted at rest** using industry-standard encryption
- Only server administrators can view masked keys
- The bot creator does not access or use your keys
- Keys are never logged or transmitted externally

---

## OpenRouter Note

OpenRouter free keys are often rate-limited or unavailable unless you have high priority. For reliable uncensored mode:
1. Use Gemini free keys for general chat
2. Set an OpenRouter credit limit to $1 in your settings
3. ~$0.70 yields approximately 1500-2500 uncensored messages
