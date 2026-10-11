# Math practice

A phone-friendly practice sheet for one student, plus a Cloudflare Worker that stores the sheet, the answers, and a profile.

The site is static. Cloudflare Pages serves `web/`. The Worker is the only place that sees the answer key, the per-sheet token, submissions, photos, and the profile.

This repository does not contain the answer key, the student profile, submissions, or photos.

## Pages

The live site is Cloudflare Pages:

https://math-practice-9wc.pages.dev/

Deploy it from the admin machine. This repo has no workflow that needs a Cloudflare token.

```bash
npx wrangler pages deploy web --project-name math-practice --branch main
```

The student link looks like:

`https://math-practice-9wc.pages.dev/?sheet=2026-10-11-p1&t=<token>`

The token is printed by `scripts/create_sheet.py`. It is not stored in git. `PAGES_URL` overrides the link base.

`.github/workflows/pages.yml` can still publish `web/` to GitHub Pages. Once this repo is private, that job may fail because GitHub Pages is unavailable. It is marked so the failure does not block the repo. The live quiz does not use it.

`web/config.js` points at `https://math-practice.khkreddy.workers.dev`. For a local Worker, open the page with `&api=http://127.0.0.1:8787`.

## What the student sees

- Sections, instructions, and the printed wording. `$...$` is set with KaTeX.
- Multiple choice, short writing, and questions with parts.
- For a drawing (Q16, Q20, Q24a on sheet 1): **Take a picture** (`capture=environment`) and **Choose from gallery**. The photo is previewed, can be retaken, and is compressed to a JPEG of at most 400 KB.
- **Check and send** stores the first answers. The page then shows Correct, Not yet, Left blank, or that a drawing is waiting for the teacher. It does not show the key.
- Not-yet items can be answered once more. That try is stored separately and does not change the marks. The first send stays as it was.
- **Finish** is the first time the page shows the key, a worked solution when the key has one, and a specific next step for each miss. If the key has no verified note, the line is "No verified notes for this item."
- Each question has **I don't know**. That clears the answer and records the signal. It is not marked wrong.
- The page records when a question was first seen, how long it stayed on screen, and how many edits, and sends that with the answers.
- A draft stays in `localStorage` on that device, including an older draft that has only answers.
- Question 24b shows `figures/q24.svg`. A figure may instead carry its SVG in `data` (markup or a `data:image/svg+xml` URL). Scripts and external links are removed before it is shown.

## Worker

Free plan. Storage is Workers KV. Do not add R2; creating a bucket asks for a payment method.

| Method | Path | Who |
|---|---|---|
| GET | `/health` | anyone |
| GET | `/sheet/:id?t=<token>` | student link. Sheet only, no answer key. After a final send, also the check result. The key is included only after Finish |
| POST | `/submit/:id?t=<token>` | student. Stores the first answers, optional timing, and photos. Returns the check result without the key. A second final send is rejected unless `allow_resubmit` |
| POST | `/retry/:id?t=<token>` | student, after the check. Stores one re-answer for not-yet items at `retry:<id>`. Does not change the first send or the marks |
| POST | `/finish/:id?t=<token>` | student. Stores `finish:<id>`, then returns the key, any worked solution, and a next step for each miss |
| PUT | `/admin/sheet/:id` | `Authorization: Bearer $ADMIN_TOKEN`. Body `{ "sheet", "answer_key", "allow_resubmit"? }`. Returns a new token |
| PUT | `/admin/sheet/:id/content` | admin. Same body. Replaces the sheet, the key, or both, and keeps the student token |
| GET | `/admin/sheet/:id` | admin. Sheet, key, and token |
| GET | `/admin/submissions?since=<iso>&sheet=<id>` | admin. List without photo bytes. `sheet` keeps one sheet |
| GET | `/admin/submission/:id` | admin. One submission, including photos, plus `retry` and `finish` when they exist |
| GET, PUT | `/admin/profile` | admin. One JSON profile |

CORS allows every origin in `PAGES_ORIGIN` (comma-separated) and `http://localhost` / `http://127.0.0.1` with a port. The deployed list is `https://khkreddy.github.io` and `https://math-practice-9wc.pages.dev`. Each stored photo must be at most 1 MB.

An old submission that has only `answers` still loads. Retry and Finish use extra keys in the same SUBMISSIONS namespace. Nothing has to be copied into a new namespace, and deploying this Worker does not rotate a token that was already emailed.

### Deploy

From this directory, with the Cloudflare account that owns the project:

`wrangler.toml` has the SHEETS, SUBMISSIONS, and PROFILE namespace ids, and `web/config.js` points at the deployed Worker. To deploy again:

```bash
npx wrangler login
npx wrangler secret put ADMIN_TOKEN
npx wrangler deploy
```

Local run:

```bash
cp .dev.vars.example .dev.vars   # then edit ADMIN_TOKEN
npx wrangler dev
```

`.dev.vars` is gitignored.

## Admin scripts

They read `WORKER_URL` and `ADMIN_TOKEN` from the environment.

```bash
export WORKER_URL=https://math-practice.khkreddy.workers.dev
export ADMIN_TOKEN=...
python3 scripts/create_sheet.py \
  --sheet content/sheets/2026-10-11-p1.json \
  --key /path/to/2026-10-11-p1.key.json
python3 scripts/fetch_submissions.py --since 2026-10-11T00:00:00Z
python3 scripts/fetch_submissions.py --id 2026-10-11-p1
python3 scripts/profile.py get
python3 scripts/profile.py put --file /path/to/profile.json
python3 scripts/score_submission.py \
  --sheet content/sheets/2026-10-11-p1.json \
  --key /path/to/2026-10-11-p1.key.json \
  --submission /path/to/submission.json
```

`create_sheet.py` prints the student link. The key file is not in this repo. Its shape is `schema/answer-key.schema.json`.

Scoring marks multiple choice and short answers from the key. A photo is `needs_review` and gets no automatic marks. The daily steps are in `OPERATIONS.md`.

## Sheet 1

`content/sheets/2026-10-11-p1.json` is Practice Sheet 1 (24 questions, 50 marks). Hinge ids are not on this sheet. Put them on the private answer key when the map ids are known. The schema field is `hinges` (strings only).

## Figures

```bash
bash scripts/build_figures.sh
```

That runs `latex` and `dvisvgm` (`standalone` + TikZ). `vendor/mathfig` and `vendor/physfig` are the vendored libraries. See `vendor/NOTICE.md`. Question 24 uses mathfig's line and arrow styles. The parallel-lines macro draws a different picture (line names, arcs, tick marks), so it is not the exam figure.

## Tests

```bash
npm test
python3 -m unittest discover -s tests -v
```
