# vuneliq
A transparent digital giving platform that empowers individuals to donate to meaningful causes, track contributions, and see the real-world impact of their generosity.

## Backend: local setup

Requires Python 3.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set SECRET_KEY to a long random value
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- With `AI_API_KEY` empty, AI endpoints use a clearly labelled mock provider.

### Run the tests

```bash
cd backend
python -m pytest -q
```

Tests use an in-memory SQLite database and the mock AI provider; no network or real keys are needed.
CI runs the same command on every pull request (`.github/workflows/backend-tests.yml`).

### Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.
The team engineering workflow (Research → Plan → Implement) is installed as a Claude Code skill in
`.claude/skills/rpi-production-engineering` (pinned in `skills-lock.json`).
