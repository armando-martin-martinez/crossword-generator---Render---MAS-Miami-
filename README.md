# Crossword Generator — Backend Deployment (Render)

## Files in this folder
- `app.py` — Flask API (`/api/generate`, `/api/available`)
- `generator.py` — CSP backtracking crossword solver
- `requirements.txt` — Python dependencies (includes `gunicorn` for production)

## 1. Supabase — run once, before deploying
```sql
-- Lock down direct public access to content tables (deny-all by design)
alter table public.words enable row level security;
alter table public.clues enable row level security;
alter table public.definitions enable row level security;
alter table public.categories enable row level security;
alter table public.word_categories enable row level security;
alter table public.puzzles enable row level security;
alter table public.puzzle_words enable row level security;

-- Lock down the signup trigger function to defense-in-depth levels
revoke execute on function public.handle_new_user() from public;
revoke execute on function public.handle_new_user() from anon;
revoke execute on function public.handle_new_user() from authenticated;
```
Status: ✅ done as of this write-up.

## 2. Render — Web Service (backend)
- **Root directory**: this `backend/` folder (or wherever these files live in the repo)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Environment Variables**:
  | Key | Value | Notes |
  |---|---|---|
  | `DATABASE_URL` | your Supabase Postgres connection string | Never commit this — Render env var only |
  | `ALLOWED_ORIGINS` | `https://mas-miami.com,https://www.mas-miami.com` | Comma-separated, no spaces |
  | `FLASK_DEBUG` | *(leave unset)* | Defaults to `false`. Only set to `true` for temporary local debugging on Render, never leave on. |
- **Custom domain**: `api.mas-miami.com` (Render shows the exact CNAME to add in Squarespace DNS once you add the domain)

## 3. Render — Static Site (frontend)
- Publish `Index.html` (rename to `index.html` if Render's static site expects that exact filename — check on upload)
- **Custom domain**: `mas-miami.com` + `www.mas-miami.com`
- No build command needed — it's a single static file with CDN-loaded dependencies (Tailwind, Supabase-js)

## 4. Known free-tier behaviors (not bugs)
- **Backend cold start**: Render's free Web Service sleeps after 15 min idle; first request after that takes ~30–60s to wake up. `Index.html` already shows a friendly status message for this case instead of a silent failure.
- **Supabase auto-pause**: the free Supabase project pauses after 7 days with zero activity. Resume manually from the Supabase dashboard if this happens.

## 5. Post-deploy smoke test
1. Load `https://mas-miami.com` — topics should populate (confirms `/api/available` reachable + RLS didn't break Flask's direct `psycopg2` access).
2. Generate a crossword on each difficulty.
3. Register a new account, confirm profile + stats flow.
4. Pause/resume a game.
5. Give up on a puzzle, then check the Stats modal reflects it (played count, not counted as completed).
