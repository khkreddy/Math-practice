# Daily practice

Clock time is **15:00 IST** (09:30 UTC).

No tokens, answer keys, or student details belong in this file. Those stay on the admin machine and in Workers KV.

## 1. Make the day's sheet

Write the student-facing JSON (see `schema/sheet.schema.json` and `content/sheets/2026-10-11-p1.json`). Write the answer key beside it, outside this repo (`schema/answer-key.schema.json`).

```bash
export WORKER_URL=https://math-practice.khkreddy.workers.dev
export ADMIN_TOKEN=...
python3 scripts/create_sheet.py --sheet content/sheets/<id>.json --key /path/to/<id>.key.json
```

The script prints a token and a link:

`https://math-practice-9wc.pages.dev/?sheet=<id>&t=<token>`

`PAGES_URL` overrides that base. Email the link to the student.

A plain `PUT` (the script without `--update`) rotates the token, so send the new link if you replace the sheet that way. To fix a live sheet or key and keep the link that was already emailed:

```bash
python3 scripts/create_sheet.py --update --sheet content/sheets/<id>.json --key /path/to/<id>.key.json
```

That calls `PUT /admin/sheet/<id>/content` and does not change the token. A final submission already stored is kept. Pass `--allow-resubmit` only when a second send should replace it.

Deploy the page from this machine, not from GitHub Actions:

```bash
npx wrangler pages deploy web --project-name math-practice --branch main
```

`web/config.js` must already contain the Worker origin. See `README.md`.

## What the student sees after sending

The first send is checked on the Worker. The page shows Correct, Not yet, Left blank, or that a drawing waits for you. It does not show the key. Not-yet items can be tried once more. That try is stored apart from the first send and does not change the marks. **Finish** then shows the key, a worked solution when the key has `worked_solution.steps` (or `feedback.worked_solution`), and a next step from `action` or `feedback.action`. A blank uses `not_attempted_action` when that is set. If there is no recorded note, the page says "No verified notes for this item."

Do not put a mix-up id, or the words "keep practicing", in those fields. The page will not show them. The private profile states below are never shown to the student.

## 2. Fetch what was sent

```bash
python3 scripts/fetch_submissions.py --since 2026-10-11T09:30:00Z
python3 scripts/fetch_submissions.py --sheet <sheet-id>
python3 scripts/fetch_submissions.py --id <sheet-id> > /path/to/submission.json
```

The list has no photo bytes. `--sheet` limits it to one sheet. The single-sheet call includes photos. `retry` on that record is the second try, with no credit. `answers` is still the first send.

## 3. Score

```bash
python3 scripts/score_submission.py \
  --sheet content/sheets/<id>.json \
  --key /path/to/<id>.key.json \
  --submission /path/to/submission.json
```

- Multiple choice: `match` `choice`, against the option id.
- Short text: `text` (normalized, case-insensitive), `number` (the numbers in the answer), `set` (same numbers or words, any order), or `token` (every word of an accept value appears, so `CQF` matches `angle CQF`).
- A photo (`kind: photo`, or a construction response) is `needs_review`. Marks stay empty until a person looks at the picture. The key's `rubric` is what they check. Do not treat a blurry or missing photo as wrong; leave it for review.
- Empty is `not_attempted`, which is not the same as incorrect.
- If the key maps a wrong response to a short misconception id (`wrong`), that id is copied onto the result.

## 4. Update the profile

`GET /admin/profile`, change the JSON, `python3 scripts/profile.py put --file ...`.

Shape: `schema/profile.schema.json`. One profile. Each hinge id maps to a state and a list of evidence.

For every scored leaf that has hinge ids on the answer key, append:

```json
{
  "sheet_id": "<id>",
  "question_id": "q7",
  "part": "a",
  "result": "correct",
  "misconception": "",
  "at": "<submitted_at>"
}
```

`result` is `correct`, `incorrect`, `partial`, `needs_review`, or `not_attempted`. Copy `misconception` only when the scorer reported one.

State, from the evidence for that hinge, newest last. Ignore `needs_review` and `not_attempted` when deciding the state (they do not move it). These state names stay in this private profile. Do not copy them onto the student page.

| Situation | State |
|---|---|
| No marked evidence yet | `unseen` |
| One `correct`, or a `correct` after an `incorrect` | `emerging` |
| Two `correct` in a row | `practicing` |
| Three `correct` in a row | `mastered` |
| Was `mastered` or `practicing`, and the newest marked result is `incorrect` or `partial` | `slipping` |

`partial` counts as not-yet-correct: it can move a strong hinge to `slipping`, and it does not advance `unseen` to `emerging`.

Set `updated_at` to the time of this update.

## 5. Choose the next sheet

Build the next sheet around the profile, still at a grade 6 level unless the profile says otherwise.

- Most of the marks: hinges in `slipping`, `emerging`, or `unseen`.
- One short question from a `mastered` hinge, so a success is not dropped.
- Anything still `needs_review` stays out of the automatic marks. After the photo is marked by hand, add a normal evidence row and run the state rules again.
- Do not repeat a question the student has just submitted correctly. A hinge can return with a new question.

Sheet 1 has no hinge ids in the public JSON. Put ids only on the private key until they are safe to show (ids, no map text). The public sheet may then copy those ids into `hinges` and nothing else.

## Photos

The page compresses each picture to a JPEG of at most 400 KB before upload. The Worker rejects a stored photo value over 1 MB. Review the picture against the rubric. A net, a number line, or a constructed angle is not scored by the text scorer.
