# Sheets

`sheets/2026-10-11-p1.json` is Practice Sheet 1, the student-facing paper (24 questions, 50 marks). Wording is the printed paper. `$...$` is KaTeX.

The answer key is not in this repository. `PUT /admin/sheet/:id` stores it in Workers KV, and `GET /sheet/:id` does not return it. See `schema/answer-key.schema.json`.

Hinge or unit ids are optional on each question (`hinges`, strings only). This sheet leaves them off. Attach ids in the private answer key when the map ids are known. Do not put map prose in the public sheet.

Question 24's figure is `web/figures/q24.svg`, built from `figures/sources/q24.tikz`.
