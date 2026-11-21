# Studify CA - project notes for any AI coding agent

Owner: CA Intermediate student in India, writes Hinglish. Wants SHORT answers, one step at a time, exact click locations. Uses GitHub web UI, Supabase dashboard, Windows laptop (Chrome), Android phone.

## What this is
- Single-file PWA: `index.html` (vanilla JS in one IIFE, no build step). Live: https://studifyca.github.io/Studify/ (repo StudifyCA/Studify, GitHub Pages).
- Backend: Supabase project `tcbjmzbrdgivdjvhrlas` (auth, RLS, RPC functions, edge functions `ai-tutor`, `hw-check`, `icai-check`, `icai-pdf`, `icai-docs`).
- `sw.js` = network-first service worker. Bump `CACHE='studyos-vNN'` every release (internal only).
- `manifest.webmanifest` has home-screen shortcuts (`?go=focus|today|hw|pt`).
- ICAI papers sync: `.github/workflows/icai-sync.yml` runs `icai_sync.py`, `mcq_extract.py`, `mcq_vision.py` (Gemini vision for scanned MCQ PDFs). PDFs live in GitHub Releases.
- Question banks for homework: `papers/qbank/qb-<KEY>.json` (FD1-4, IN1-6, FN1-6), shape `{q:[{c,t:'d'|'m',q,o?,a?,mk,s,r,i}],rep:[...]}`.
- SQL files `NN_*.sql` are run once in Supabase SQL Editor (latest: 18_leaderboard_referral.sql: leaderboard + referral).

## Code map (index.html)
- State: `S` (profiles), `ui` (screen state), `cloud` (Supabase state). `render()` / `renderKeep()`.
- Events: `data-act` -> `act(a,d)`, `data-chg` -> `chg(k,d,el)`, `data-ob` onboarding fields.
- Views: `viewToday`, `viewHW`, `viewPartner` (lbCard2 = global leaderboard), `viewSettings`, `viewOnboard`.
- RPC helper: `rpc(name,args)` throws on error.
- Homework: `hwGen`, `hwCands`, `hwItemHtml`, `hwQHtml`.
- Timer options in localStorage key `ca_studyos_tmopts` (strict, break reminder, Buddy Lock hash).

## Rules from the owner (do not break)
- Keep everything that works working. No duplicate features. Do not remove data to hide bugs - repair it.
- Visible version label is just "v1". Never show v1.xx.
- Multi-course expansion (CS/CMA/NEET etc.) is DEFERRED until the Play Store app exists.
- Never use or store the owner's ICAI ID/DOB credentials. The app must never ask for an ICAI password.
- Do not touch the AI memory feature ("memory ko mt chedna").
- AI tutor is locked unless `app_config.ai_open` is true or user is admin; daily limit 30 via `ai_use` RPC. Owner will turn on AI billing when users grow.
- Gemini model names change: edge functions discover models with ListModels (`pickModels`), do not hard-code old names.

## Testing
- Build a test copy that exposes internals as `window.__t`, serve it with `python3 -m http.server 8765`, drive with Playwright. Always check no `pageerror`.
- Check JS syntax before delivering: extract the <script> text and run `new Function(text)` in node.
- Postgres SQL can be tested locally with a stub `auth.uid()`.

## Delivery style
- The owner pastes files via GitHub web editor (pencil icon, select all, paste, Commit). For each release give: which files to replace, which SQL to run, which Supabase function to deploy. Send only files that changed.

## Open items
- Play Store: TWA via PWABuilder, package `com.studifyca.app`, assetlinks.json in repo `studifyca.github.io/.well-known/` (add BOTH upload-key and Play App Signing SHA-256).
- Native-only (later): widgets, notification Start button, real app blocking, mentor verification.
- Needs paid AI: answer explanations for MCQs without answers, notes -> MCQ.
- Real Gemini video-note clipping for 12-hour lectures is only tested with mocks.
