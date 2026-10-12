import { Miniflare } from "miniflare";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const ADMIN = "test-admin-token";
const ORIGIN = "https://khkreddy.github.io";

let mf;

beforeAll(async () => {
  mf = new Miniflare({
    modules: true,
    scriptPath: "worker/src/index.js",
    // Miniflare treats imported .js files as CommonJS unless a rule says otherwise.
    modulesRules: [{ type: "ESModule", include: ["worker/**/*.js"], fallthrough: true }],
    compatibilityDate: "2025-04-01",
    kvNamespaces: ["SHEETS", "SUBMISSIONS", "PROFILE"],
    bindings: {
      ADMIN_TOKEN: ADMIN,
      PAGES_ORIGIN: `${ORIGIN}, https://math-practice-9wc.pages.dev`,
    },
  });
  await mf.ready;
});

afterAll(async () => {
  await mf?.dispose();
});

function admin(method, path, body) {
  return mf.dispatchFetch(`https://math-practice.test${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${ADMIN}`,
      "Content-Type": "application/json",
    },
    body: body == null ? undefined : JSON.stringify(body),
  });
}

const sheet = {
  id: "sheet-1",
  title: "Practice Sheet 1",
  subject: "Mathematics",
  total_marks: 3,
  instructions: ["All questions are compulsory."],
  sections: [
    {
      id: "A",
      title: "Section A",
      marks_scheme: "2 x 1 = 2",
      questions: [
        {
          id: "q1",
          qno: 1,
          type: "mcq",
          marks: 1,
          text: "Which of the following is a factor of 44?",
          options: [{ id: "d", text: "11" }],
          answer: "d",
        },
        {
          id: "q16",
          qno: 16,
          type: "construction",
          marks: 2,
          text: "Represent a number.",
          response: "photo",
        },
      ],
    },
  ],
};

const key = {
  sheet_id: "sheet-1",
  questions: { q1: { accept: ["d"], match: "choice" } },
  secret_marker: "SENTINEL_DO_NOT_LEAK",
};

describe("math practice worker", () => {
  it("answers health", async () => {
    const res = await mf.dispatchFetch("https://math-practice.test/health");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true, service: "math-practice" });
  });

  it("rejects admin calls without the bearer token", async () => {
    const res = await mf.dispatchFetch("https://math-practice.test/admin/profile");
    expect(res.status).toBe(401);
  });

  it("creates a sheet, hides the key, stores a submission once, and keeps the profile", async () => {
    const created = await admin("PUT", "/admin/sheet/sheet-1", {
      sheet,
      answer_key: key,
    });
    expect(created.status).toBe(200);
    const createdBody = await created.json();
    expect(createdBody.token).toMatch(/^[0-9a-f]{64}$/);
    const token = createdBody.token;

    const hidden = await mf.dispatchFetch("https://math-practice.test/sheet/sheet-1");
    expect(hidden.status).toBe(401);

    const bad = await mf.dispatchFetch("https://math-practice.test/sheet/sheet-1?t=nope");
    expect(bad.status).toBe(401);

    const pub = await mf.dispatchFetch(`https://math-practice.test/sheet/sheet-1?t=${token}`, {
      headers: { Origin: ORIGIN },
    });
    expect(pub.status).toBe(200);
    expect(pub.headers.get("Access-Control-Allow-Origin")).toBe(ORIGIN);
    const pubBody = await pub.json();
    expect(pubBody.submitted).toBe(false);
    expect(JSON.stringify(pubBody)).not.toContain("SENTINEL_DO_NOT_LEAK");
    expect(JSON.stringify(pubBody)).not.toContain('"answer"');
    expect(pubBody.sheet.sections[0].questions[0].text).toContain("factor of 44");

    const evil = await mf.dispatchFetch(`https://math-practice.test/sheet/sheet-1?t=${token}`, {
      headers: { Origin: "https://evil.example" },
    });
    expect(evil.headers.get("Access-Control-Allow-Origin")).toBeNull();

    const preflight = await mf.dispatchFetch("https://math-practice.test/submit/sheet-1", {
      method: "OPTIONS",
      headers: { Origin: "http://127.0.0.1:8080", "Access-Control-Request-Method": "POST" },
    });
    expect(preflight.status).toBe(204);
    expect(preflight.headers.get("Access-Control-Allow-Origin")).toBe("http://127.0.0.1:8080");

    const photo = btoa("tiny-jpeg-bytes");
    const sent = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-1?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: ORIGIN },
      body: JSON.stringify({
        answers: {
          q1: { value: "d" },
          q16: { photo, content_type: "image/jpeg" },
        },
      }),
    });
    expect(sent.status).toBe(200);
    const sentBody = await sent.json();
    expect(sentBody.ok).toBe(true);
    expect(sentBody.feedback.items.find((item) => item.id === "q1").status).toBe("correct");
    expect(JSON.stringify(sentBody)).not.toContain("SENTINEL_DO_NOT_LEAK");
    expect(JSON.stringify(sentBody.feedback)).not.toContain('"key"');

    const again = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-1?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: { q1: { value: "a" } } }),
    });
    expect(again.status).toBe(409);

    const after = await mf.dispatchFetch(`https://math-practice.test/sheet/sheet-1?t=${token}`);
    expect((await after.json()).submitted).toBe(true);

    const list = await admin("GET", "/admin/submissions?since=2000-01-01T00:00:00Z");
    expect(list.status).toBe(200);
    const listed = await list.json();
    expect(listed.submissions).toHaveLength(1);
    expect(listed.submissions[0]).toMatchObject({ sheet_id: "sheet-1", has_photos: true });

    const future = await admin("GET", "/admin/submissions?since=2999-01-01T00:00:00Z");
    expect((await future.json()).submissions).toEqual([]);

    const full = await admin("GET", "/admin/submission/sheet-1");
    const fullBody = await full.json();
    expect(fullBody.answers.q16.photo).toBe(photo);
    expect(fullBody.answers.q1.value).toBe("d");

    const huge = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-1?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: { q16: { photo: "A".repeat(1_000_001) } } }),
    });
    expect([409, 413]).toContain(huge.status);

    const adminSheet = await admin("GET", "/admin/sheet/sheet-1");
    const adminSheetBody = await adminSheet.json();
    expect(adminSheetBody.token).toBe(token);
    expect(adminSheetBody.answer_key.secret_marker).toBe("SENTINEL_DO_NOT_LEAK");

    const putProfile = await admin("PUT", "/admin/profile", {
      profile: { updated_at: "2026-10-11T09:30:00.000Z", hinges: {} },
    });
    expect(putProfile.status).toBe(200);
    const gotProfile = await admin("GET", "/admin/profile");
    expect(await gotProfile.json()).toEqual({
      profile: { updated_at: "2026-10-11T09:30:00.000Z", hinges: {} },
    });
  });

  it("rejects a photo over 1 MB when resubmit is allowed", async () => {
    const created = await admin("PUT", "/admin/sheet/sheet-big", {
      sheet: { ...sheet, id: "sheet-big" },
      answer_key: { ...key, sheet_id: "sheet-big" },
      allow_resubmit: true,
    });
    const token = (await created.json()).token;
    const res = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-big?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: { q16: { photo: "A".repeat(1_000_001), content_type: "image/jpeg" } } }),
    });
    expect(res.status).toBe(413);
  });

  it("rejects a mismatched sheet id", async () => {
    const res = await admin("PUT", "/admin/sheet/other", { sheet, answer_key: key });
    expect(res.status).toBe(400);
  });

  it("allows each origin listed in PAGES_ORIGIN", async () => {
    for (const origin of [ORIGIN, "https://math-practice-9wc.pages.dev"]) {
      const res = await mf.dispatchFetch("https://math-practice.test/health", {
        headers: { Origin: origin },
      });
      expect(res.status).toBe(200);
      expect(res.headers.get("Access-Control-Allow-Origin")).toBe(origin);
      const preflight = await mf.dispatchFetch("https://math-practice.test/submit/sheet-1", {
        method: "OPTIONS",
        headers: { Origin: origin, "Access-Control-Request-Method": "POST" },
      });
      expect(preflight.status).toBe(204);
      expect(preflight.headers.get("Access-Control-Allow-Origin")).toBe(origin);
    }
    const evil = await mf.dispatchFetch("https://math-practice.test/health", {
      headers: { Origin: "https://evil.example" },
    });
    expect(evil.headers.get("Access-Control-Allow-Origin")).toBeNull();
  });

  it("hides the key until Finish, keeps the first send, and stores one no-credit retry", async () => {
    const practice = {
      ...sheet,
      id: "sheet-feedback",
      total_marks: 4,
      sections: [
        {
          id: "A",
          title: "Section A",
          marks_scheme: "2 x 1 + 2",
          questions: [
            {
              id: "q1",
              qno: 1,
              type: "mcq",
              marks: 1,
              text: "Which of the following is a factor of 44?",
              options: [
                { id: "a", text: "5" },
                { id: "d", text: "11" },
              ],
            },
            {
              id: "q2",
              qno: 2,
              type: "short",
              marks: 1,
              text: "Write a number.",
              response: "short",
            },
            {
              id: "q3",
              qno: 3,
              type: "construction",
              marks: 2,
              text: "Draw a number line.",
              response: "photo",
            },
          ],
        },
      ],
    };
    const practiceKey = {
      sheet_id: "sheet-feedback",
      secret_marker: "SENTINEL_DO_NOT_LEAK",
      questions: {
        q1: {
          accept: ["d"],
          match: "choice",
          action: "keep practicing",
          note: "H3#mx4 sign error",
          wrong: { a: "H3#mx4" },
          mx_id: "H3#mx4",
          worked_solution: { steps: ["LEAK_SOLUTION_STEP"] },
        },
        q2: {
          accept: ["12"],
          match: "number",
          note: "Count on from 10.",
          not_attempted_action: "Write the number question 2 asks for.",
          worked_solution: { steps: ["10 and 2 more is 12."] },
        },
      },
    };
    const created = await admin("PUT", "/admin/sheet/sheet-feedback", {
      sheet: practice,
      answer_key: practiceKey,
    });
    const token = (await created.json()).token;
    const sent = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-feedback?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answers: {
          q1: { value: "a" },
          q3: { photo: btoa("tiny-jpeg"), content_type: "image/jpeg" },
        },
      }),
    });
    expect(sent.status).toBe(200);
    const checked = await sent.json();
    const checkedText = JSON.stringify(checked);
    expect(checked.feedback.phase).toBe("checked");
    expect(checked.feedback.summary).toMatchObject({ typed_marks: 0, typed_max: 2, pending_marks: 2 });
    expect(checked.feedback.items.map((item) => item.status)).toEqual(["not_yet", "blank", "pending_review"]);
    for (const hidden of ["SENTINEL_DO_NOT_LEAK", "LEAK_SOLUTION_STEP", "keep practicing", "H3#mx4", "Count on from 10.", "d. 11"]) {
      expect(checkedText).not.toContain(hidden);
    }
    expect(checkedText).not.toContain('"key"');

    const early = await mf.dispatchFetch(`https://math-practice.test/finish/sheet-feedback?t=${token}`, { method: "POST" });
    expect(early.status).toBe(409);

    const retried = await mf.dispatchFetch(`https://math-practice.test/retry/sheet-feedback?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answers: {
          q1: { value: "d" },
          q2: { value: "should-not-be-stored" },
        },
      }),
    });
    expect(retried.status).toBe(200);
    const retryBody = await retried.json();
    expect(retryBody.feedback.phase).toBe("retried");
    expect(JSON.stringify(retryBody)).not.toContain("LEAK_SOLUTION_STEP");
    expect(retryBody.feedback.summary.typed_marks).toBe(0);

    const stored = await admin("GET", "/admin/submission/sheet-feedback");
    const storedBody = await stored.json();
    expect(storedBody.answers.q1.value).toBe("a");
    expect(storedBody.answers.q2).toBeUndefined();
    expect(storedBody.retry.no_credit).toBe(true);
    expect(storedBody.retry.answers.q1.value).toBe("d");
    expect(storedBody.retry.answers.q2).toBeUndefined();
    expect(storedBody.finish).toBeNull();

    const done = await mf.dispatchFetch(`https://math-practice.test/finish/sheet-feedback?t=${token}`, { method: "POST" });
    expect(done.status).toBe(200);
    const revealed = await done.json();
    expect(revealed.feedback.phase).toBe("finished");
    expect(revealed.feedback.summary.typed_marks).toBe(0);
    const q1 = revealed.feedback.items.find((item) => item.id === "q1");
    const q2 = revealed.feedback.items.find((item) => item.id === "q2");
    expect(q1.key).toBe("d. 11");
    expect(q1.worked_solution).toContain("LEAK_SOLUTION_STEP");
    expect(q1.action).toBe("Choose one of the options for question 1.");
    expect(q1.note).toBe("No verified notes for this item.");
    expect(q2.note).toBe("Count on from 10.");
    expect(q2.action).toBe("Write the number question 2 asks for.");
    expect(q2.worked_solution).toContain("10 and 2 more is 12.");
    const revealedText = JSON.stringify(revealed);
    for (const hidden of ["SENTINEL_DO_NOT_LEAK", "keep practicing", "H3#mx4", "mastered", "you learned from this mistake"]) {
      expect(revealedText).not.toContain(hidden);
    }

    const again = await mf.dispatchFetch(`https://math-practice.test/finish/sheet-feedback?t=${token}`, { method: "POST" });
    expect((await again.json()).finished_at).toBe(revealed.finished_at);
    const after = await admin("GET", "/admin/submission/sheet-feedback");
    expect((await after.json()).answers.q1.value).toBe("a");
  });

  it("stores timing and treats I don't know as blank", async () => {
    const created = await admin("PUT", "/admin/sheet/sheet-timing", {
      sheet: { ...sheet, id: "sheet-timing" },
      answer_key: { ...key, sheet_id: "sheet-timing" },
    });
    const token = (await created.json()).token;
    const bad = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-timing?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answers: { q1: { value: "d" } },
        timing: { q1: { edit_count: -1 } },
      }),
    });
    expect(bad.status).toBe(400);
    expect((await admin("GET", "/admin/submission/sheet-timing")).status).toBe(404);

    const sent = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-timing?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answers: { q1: { value: "d" } },
        timing: {
          q1: {
            first_seen_at: "2026-10-11T10:00:00.000Z",
            time_on_question_ms: 1500,
            edit_count: 2,
            idk: true,
          },
        },
      }),
    });
    expect(sent.status).toBe(200);
    const body = await sent.json();
    expect(body.feedback.items.find((item) => item.id === "q1").status).toBe("blank");
    const stored = await (await admin("GET", "/admin/submission/sheet-timing")).json();
    expect(stored.answers.q1).toEqual({ idk: true });
    expect(stored.timing.q1).toMatchObject({ edit_count: 2, idk: true, time_on_question_ms: 1500 });
  });

  it("filters the submission list by sheet", async () => {
    for (const id of ["sheet-list-a", "sheet-list-b"]) {
      const created = await admin("PUT", `/admin/sheet/${id}`, {
        sheet: { ...sheet, id },
        answer_key: { ...key, sheet_id: id },
      });
      const token = (await created.json()).token;
      const sent = await mf.dispatchFetch(`https://math-practice.test/submit/${id}?t=${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: { q1: { value: "d" } } }),
      });
      expect(sent.status).toBe(200);
    }
    const only = await admin("GET", "/admin/submissions?sheet=sheet-list-a");
    const listed = await only.json();
    expect(listed.submissions.map((item) => item.sheet_id)).toEqual(["sheet-list-a"]);
  });

  it("updates a sheet and key without rotating the student token", async () => {
    const created = await admin("PUT", "/admin/sheet/sheet-update", {
      sheet: { ...sheet, id: "sheet-update" },
      answer_key: { ...key, sheet_id: "sheet-update" },
    });
    const token = (await created.json()).token;
    const updated = await admin("PUT", "/admin/sheet/sheet-update/content", {
      sheet: { ...sheet, id: "sheet-update", title: "Revised title" },
      answer_key: {
        sheet_id: "sheet-update",
        questions: { q1: { accept: ["z"], match: "choice" } },
      },
    });
    expect(updated.status).toBe(200);
    expect((await updated.json()).token).toBe(token);
    const pub = await mf.dispatchFetch(`https://math-practice.test/sheet/sheet-update?t=${token}`);
    expect((await pub.json()).sheet.title).toBe("Revised title");
    const sent = await mf.dispatchFetch(`https://math-practice.test/submit/sheet-update?t=${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: { q1: { value: "d" } } }),
    });
    const body = await sent.json();
    expect(body.feedback.items.find((item) => item.id === "q1").status).toBe("not_yet");
    expect(JSON.stringify(body)).not.toContain('"key"');
  });

  it("strips scripts and external links from an inline figure", async () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(1)</script><a href="https://evil.example/x">x</a><a href="#arm">n</a><circle cx="1" cy="1" r="1"/></svg>';
    const created = await admin("PUT", "/admin/sheet/sheet-svg", {
      sheet: {
        ...sheet,
        id: "sheet-svg",
        sections: [
          {
            ...sheet.sections[0],
            questions: [
              {
                ...sheet.sections[0].questions[0],
                figure: {
                  id: "inline",
                  alt: "A small circle",
                  data: `data:image/svg+xml;base64,${btoa(svg)}`,
                },
              },
            ],
          },
        ],
      },
      answer_key: { ...key, sheet_id: "sheet-svg" },
    });
    const token = (await created.json()).token;
    const pub = await mf.dispatchFetch(`https://math-practice.test/sheet/sheet-svg?t=${token}`);
    const data = (await pub.json()).sheet.sections[0].questions[0].figure.data;
    expect(data).toContain("<circle");
    expect(data).toContain('href="#arm"');
    expect(data).not.toMatch(/script/i);
    expect(data).not.toMatch(/onload/i);
    expect(data).not.toContain("evil.example");
    expect(data.startsWith("data:")).toBe(false);
  });
});
