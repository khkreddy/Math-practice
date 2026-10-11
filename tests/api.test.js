import { Miniflare } from "miniflare";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const ADMIN = "test-admin-token";
const ORIGIN = "https://khkreddy.github.io";

let mf;

beforeAll(async () => {
  mf = new Miniflare({
    modules: true,
    scriptPath: "worker/src/index.js",
    compatibilityDate: "2025-04-01",
    kvNamespaces: ["SHEETS", "SUBMISSIONS", "PROFILE"],
    bindings: {
      ADMIN_TOKEN: ADMIN,
      PAGES_ORIGIN: ORIGIN,
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
});
