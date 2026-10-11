# Math practice

A phone-friendly practice sheet for one student, plus a Cloudflare Worker that stores the sheet, the answers, and a profile.

The site is static. GitHub Pages serves `web/`. The Worker is the only place that sees the answer key, the per-sheet token, submissions, photos, and the profile.

This repository does not contain the answer key, the student profile, submissions, or photos.

## Pages

After this is on `main`, the site is:

https://khkreddy.github.io/Math-practice/

Hari needs to set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**. The workflow `.github/workflows/pages.yml` deploys the `web/` folder. If the first run says it cannot find a Pages site, set that source and run the workflow again.

The student link looks like:

`https://khkreddy.github.io/Math-practice/?sheet=2026-10-11-p1&t=<token>`

The token is printed by `scripts/create_sheet.py`. It is not stored in git.

`web/config.js` has an empty `workerUrl` until the Worker is deployed. Set it to the `workers.dev` origin (no trailing slash) and push to `main`. For a local Worker, open the page with `&api=http://127.0.0.1:8787`.

## What the student sees

- Sections, instructions, and the printed wording. `$...$` is set with KaTeX.
- Multiple choice, short writing, and questions with parts.
- For a drawing (Q16, Q20, Q24a on sheet 1): **Take a picture** (`capture=environment`) and **Choose from gallery**. The photo is previewed, can be retaken, and is compressed to a JPEG of at most 400 KB.
- One submit, a confirm screen, then a sent screen. A draft stays in `localStorage` on that device.
- Question 24b shows `figures/q24.svg`.

## Worker

Free plan. Storage is Workers KV. Do not add R2; creating a bucket asks for a payment method.

| Method | Path | Who |
|---|---|---|
| GET | `/health` | anyone |
| GET | `/sheet/:id?t=<token>` | student link. Sheet only, no answer key. `submitted` is true after a final send |
| POST | `/submit/:id?t=<token>` | student. Stores answers and photos. A second final send is rejected unless `allow_resubmit` |
| PUT | `/admin/sheet/:id` | `Authorization: Bearer $ADMIN_TOKEN`. Body `{ "sheet", "answer_key", "allow_resubmit"? }`. Returns a new token |
| GET | `/admin/sheet/:id` | admin. Sheet, key, and token |
| GET | `/admin/submissions?since=<iso>` | admin. List without photo bytes |
| GET | `/admin/submission/:id` | admin. One submission, including photos |
| GET, PUT | `/admin/profile` | admin. One JSON profile |

CORS allows `https://khkreddy.github.io` and `http://localhost` / `http://127.0.0.1` with a port. Each stored photo must be at most 1 MB.

### Deploy

From this directory, with the Cloudflare account that owns the project:

```bash
npx wrangler login
npx wrangler kv namespace create SHEETS
npx wrangler kv namespace create SUBMISSIONS
npx wrangler kv namespace create PROFILE
```

Replace the three placeholder ids in `wrangler.toml` with the ids that command prints. Then:

```bash
npx wrangler secret put ADMIN_TOKEN
npx wrangler deploy
```

`wrangler deploy` prints the Worker URL. Put that origin in `web/config.js` and push to `main`.

Local run:

```bash
cp .dev.vars.example .dev.vars   # then edit ADMIN_TOKEN
npx wrangler dev
```

`.dev.vars` is gitignored.

## Admin scripts

They read `WORKER_URL` and `ADMIN_TOKEN` from the environment.

```bash
export WORKER_URL=https://math-practice.<account>.workers.dev
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
