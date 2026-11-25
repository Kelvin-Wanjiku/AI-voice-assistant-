# Milo

An AI companion for older adults that remembers what matters to them.

## Project layout

```
milo/
├── backend/                 Python + FastAPI (AI logic, memory, tools, planner)
└── frontend/                React + TypeScript (what the user sees)
    └── src/
        ├── main.tsx         Starts the app
        ├── App.tsx          The frame: menu + which screen to show
        ├── types.ts         Shapes of Milo's data (plans, memories, messages)
        ├── api.ts           Talks to the backend
        ├── styles.css       All the styling
        ├── screens/         One file per screen: Home, Chat, My day, About me
        ├── components/      Pieces used on several screens (menu, icons, status)
        ├── data/            Shared data store + sample data
        └── utils/           Small helpers (dates and times)
```

## Progress

- Phase 1: foundation. Done.
- Phase 2: four screens with navigation, using sample data. Done.
- Phase 3: Milo's AI brain. The Chat screen gets real replies. Done.

## Milo's brain (Phase 3)

- `backend/app/personality.py`: who Milo is and how it talks. Edit this to change Milo's manner.
- `backend/app/llm.py`: the only file that talks to the AI provider.
- `backend/app/routes/chat.py`: the `/api/chat` address the Chat screen sends messages to.

Milo works with several free AI providers. Choose one in `backend/.env`:

```
LLM_PROVIDER=groq          # or gemini, mistral, openrouter
LLM_API_KEY=your-key-here
```

Restart the backend after changing `.env`.

## Connect the database (Supabase) - optional until Phase 4

1. Create a free project at https://supabase.com
2. Go to **Project Settings > Database > Connection string** and choose **Session pooler**.
3. Paste it into `backend/.env` as `DATABASE_URL`, changing the start from
   `postgresql://` to `postgresql+psycopg://`.
4. Restart the backend and press **Check again** in the app.

## Rules for this project

- Never commit `.env` files. They hold secrets.
- Finish and test each phase before starting the next one.
