# femboibot-sanitized-with-holy-water

Clean project copy for running, testing, and deploying femboibot without the legacy reference subtree or local machine artifacts.

## Included

- `discord_bot/` runtime bot code, prompts, locales, modes, and bundled assets
- `tests/` automated tests
- `deploy/` deployment scripts and service files
- `.gitignore` minimal root ignore rules

## Excluded

- legacy reference code subtree
- `.venv/`
- `.pytest_cache/`
- `__pycache__/` and `.pyc` files
- local secret file `discord_bot/.env`
- runtime log files under `discord_bot/logs/`
- the copied local avatar artifact `discord_bot/data/avatars/34ea1d50-431b-4df0-b6e8-5e06e8d0bb26.jpg`
- unrelated repo docs and analysis files outside runtime, tests, and deploy

## Run

```powershell
cd discord_bot
python -m pip install -r requirements.txt
python main.py
```

Create `discord_bot/.env` from `discord_bot/.env.example` before starting the bot.

## Test

Run from the sanitized project root:

```powershell
python -m pytest tests -q
```

## Deploy

See `deploy/README.md` and the scripts in `deploy/`.
