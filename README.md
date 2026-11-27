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
- Phase 4: memory. Milo remembers useful things across sessions; About me shows and manages them. Done.
- Phase 5: live information. Weather, news (personal to your interests), recipes and web search. Done.
- Phase 6: planner and reminders. My day is real; Milo adds and changes plans in conversation; reminders pop up. Done.

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

## Milo's memory (Phase 4)

- `backend/app/memory_keeper.py`: after each message, decides what to remember, update or forget.
- `backend/app/memory_store.py`: the only code that reads or changes saved memories.
- `backend/app/models.py`: the database tables (profile and memories).
- `backend/app/db.py`: where memories are kept.

By default memories are saved in `backend/milo.db`, a file on this computer. It is personal data,
so git ignores it. Delete the file to start completely fresh.

### Optional: use Supabase instead

1. Create a free project at https://supabase.com
2. Click **Connect** at the top of the project and copy the **Session pooler** connection string.
3. Paste it into `backend/.env` as `DATABASE_URL`, changing the start from
   `postgresql://` to `postgresql+psycopg://`, and putting your database password in place of `[YOUR-PASSWORD]`.
4. Restart the backend. Milo creates its tables by itself. Memories in `milo.db` are not copied over.

## Live information (Phase 5)

- `backend/app/tools/`: one file per tool (weather, news, recipes, web search), plus `registry.py`,
  the list of tools Milo can choose from.
- `backend/app/thinking.py`: how Milo answers: decide whether to look something up, look it up (up to two
  rounds), then reply. A reply that only says "let me check" is sent back to be answered properly.
- `backend/app/holding.py`: what Milo says while a look-up takes a while ("Let me just check the weather for you").
  The delay is `HOLDING_AFTER_SECONDS` in `backend/.env` (default 3).
- The chat hides look-ups, links and memory notes. Switch them on under About me, "Show what Milo looked up and remembered".
- Weather: Open-Meteo, no key. Set your town on About me.
- News: BBC News feeds, no key. Milo adds topics that match your interests (football, technology, ...).
- Recipes: TheMealDB, no key.
- Web search: Tavily, needs a free key in `backend/.env` as `TAVILY_API_KEY` (from https://app.tavily.com).

## Planner and reminders (Phase 6)

- `backend/app/planner.py`: all the rules: dates like "Thursday", repeats, clashes, done per day, reminders.
- `backend/app/tools/diary.py`: Milo's diary tools (see, add, change, remove, tick off).
- `backend/app/routes/plans.py`: the addresses My day and the reminder pop-up use.
- `frontend/src/screens/MyDayScreen.tsx`, `components/PlanForm.tsx`, `components/ReminderBanner.tsx`.
- Plans with a time get a reminder before them: 15 minutes unless you choose another default on About me
  (or tell Milo "reminders should be 10 minutes before"). Each plan can also have its own.
- All plan times are local time. Milo converts times it finds on websites (often UK time) before adding them.
- Plans can have a place. For public events (a match, a concert) Milo looks up the date, time and place first.
  For personal plans it asks one short question about a missing time or place, or adds the plan without them.
- No duplicates: adding something that's already on that day (even spelled differently, like "Man Utd v Brentford")
  fills in the missing time or place of the existing plan instead of adding a second one.
- Plans with no time get a morning reminder (09:00 by default, changeable or off on About me) with a button,
  "Ask Milo for a good time", that opens the chat and asks Milo straight away.
- If Milo says it added or changed a plan but didn't, the backend catches it and makes it do it (or say so honestly). Reminders show on any screen while Milo
  is open. Spoken reminders come with voice (Phase 7); alerts with the app closed come with the phone app.

## Rules for this project

- Never commit `.env` files or `milo.db`. They hold secrets and personal data.
- Finish and test each phase before starting the next one.
