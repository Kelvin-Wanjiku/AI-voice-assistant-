# Milo

An AI companion for older adults that remembers what matters to them.

## Project layout

```
milo/
├── backend/    Python + FastAPI (AI logic, memory, tools, planner)
└── frontend/   React + TypeScript (what the user sees)
```

## Run it locally

You need **two terminals**, one for each half. Keep both open while you work.

### Terminal 1: backend

```bash
cd backend
python3 -m venv .venv              # Windows: python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Check it: open http://localhost:8000/api/health in your browser.

### Terminal 2: frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. You should see a greeting and three status rows.

## Connect the database (Supabase) - optional until Phase 4

1. Create a free project at https://supabase.com
2. Go to **Project Settings > Database > Connection string** and choose **Session pooler**.
3. Paste it into `backend/.env` as `DATABASE_URL`, changing the start from
   `postgresql://` to `postgresql+psycopg://`.
4. Restart the backend and press **Check again** in the app.

## Rules for this project

- Never commit `.env` files. They hold secrets.
- Finish and test each phase before starting the next one.
