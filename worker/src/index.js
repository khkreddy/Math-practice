/**
 * Daily math-practice API.
 *
 * Storage is Workers KV only (free plan). Do not add R2: an R2 bucket
 * requires a payment method. Photos are base64 JPEG values inside the
 * submission record. Each photo value must be <= 1 MB.
 *
 * A final send is stored at sub:<id> and is not rewritten by a retry or by
 * Finish. The one re-answer is retry:<id> (no credit). Finish is finish:<id>.
 * None of those are new KV namespaces.
 *
 * Bindings: SHEETS, SUBMISSIONS, PROFILE, ADMIN_TOKEN, PAGES_ORIGIN.
 */

import { buildFeedback, sanitizeSheet } from "./score.js";

const PHOTO_MAX = 1_000_000;
const BODY_MAX = 6_000_000;
const TEXT_MAX = 20_000;
const STRIP_FROM_SHEET = new Set([
  "answer_key",
  "answer",
  "accept",
  "rubric",
  "solution",
  "expected",
  "worked_solution",
  "feedback",
  "action",
  "note",
  "mx_id",
  "misconception",
  "wrong",
  "not_attempted_action",
]);

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get("Origin"), env);
    if (request.method === "OPTIONS") {
      if (!cors["Access-Control-Allow-Origin"]) {
        return new Response(null, { status: 403 });
      }
      return new Response(null, { status: 204, headers: cors });
    }
    try {
      const response = await route(request, env, url);
      return withCors(response, cors);
    } catch (err) {
      const status = err instanceof HttpError ? err.status : 500;
      const message = err instanceof HttpError ? err.message : "internal error";
      return withCors(json({ error: message }, status), cors);
    }
  },
};

async function route(request, env, url) {
  const method = request.method;
  const parts = url.pathname.split("/").filter(Boolean);

  if (method === "GET" && parts.length === 1 && parts[0] === "health") {
    return json({ ok: true, service: "math-practice" });
  }

  if (parts[0] === "sheet" && parts.length === 2) {
    if (method !== "GET") throw new HttpError(405, "method not allowed");
    return getSheet(env, parts[1], presentedToken(request, url));
  }

  if (parts[0] === "submit" && parts.length === 2) {
    if (method !== "POST") throw new HttpError(405, "method not allowed");
    return submitSheet(request, env, parts[1], presentedToken(request, url));
  }

  if (parts[0] === "retry" && parts.length === 2) {
    if (method !== "POST") throw new HttpError(405, "method not allowed");
    return retrySheet(request, env, parts[1], presentedToken(request, url));
  }

  if (parts[0] === "finish" && parts.length === 2) {
    if (method !== "POST") throw new HttpError(405, "method not allowed");
    return finishSheet(request, env, parts[1], presentedToken(request, url));
  }

  if (parts[0] === "admin") {
    if (!adminOk(request, env)) throw new HttpError(401, "unauthorized");
    return adminRoute(request, env, url, parts.slice(1));
  }

  throw new HttpError(404, "not found");
}

async function adminRoute(request, env, url, parts) {
  const method = request.method;
  if (parts[0] === "sheet" && parts.length === 3 && parts[2] === "content" && method === "PUT") {
    return updateSheetContent(request, env, parts[1]);
  }
  if (parts[0] === "sheet" && parts.length === 2 && method === "PUT") {
    return putSheet(request, env, parts[1]);
  }
  if (parts[0] === "sheet" && parts.length === 2 && method === "GET") {
    return getAdminSheet(env, parts[1]);
  }
  if (parts[0] === "submissions" && parts.length === 1 && method === "GET") {
    return listSubmissions(env, url);
  }
  if (parts[0] === "submission" && parts.length === 2 && method === "GET") {
    return getSubmission(env, parts[1]);
  }
  if (parts[0] === "profile" && parts.length === 1 && method === "GET") {
    return getProfile(env);
  }
  if (parts[0] === "profile" && parts.length === 1 && method === "PUT") {
    return putProfile(request, env);
  }
  throw new HttpError(404, "not found");
}

async function putSheet(request, env, id) {
  assertId(id);
  const body = await readJson(request);
  const sheet = body && body.sheet;
  const answerKey = body && body.answer_key;
  if (!sheet || typeof sheet !== "object" || Array.isArray(sheet)) {
    throw new HttpError(400, "sheet object is required");
  }
  if (sheet.id !== id) throw new HttpError(400, "sheet.id must match the URL");
  if (!sheet.title || !Array.isArray(sheet.sections)) {
    throw new HttpError(400, "sheet needs a title and sections");
  }
  if (!answerKey || typeof answerKey !== "object" || Array.isArray(answerKey)) {
    throw new HttpError(400, "answer_key object is required");
  }
  if (answerKey.sheet_id && answerKey.sheet_id !== id) {
    throw new HttpError(400, "answer_key.sheet_id must match the URL");
  }
  const token = randomToken();
  const record = {
    sheet: presentSheet(sheet),
    answer_key: answerKey,
    token,
    allow_resubmit: Boolean(body.allow_resubmit),
    created_at: new Date().toISOString(),
  };
  await env.SHEETS.put(sheetKey(id), JSON.stringify(record));
  return json({
    id,
    token,
    allow_resubmit: record.allow_resubmit,
    created_at: record.created_at,
  });
}

async function getAdminSheet(env, id) {
  const record = await loadSheet(env, id);
  return json({
    id,
    token: record.token,
    allow_resubmit: record.allow_resubmit,
    created_at: record.created_at,
    sheet: record.sheet,
    answer_key: record.answer_key,
  });
}

async function updateSheetContent(request, env, id) {
  const record = await loadSheet(env, id);
  const body = await readJson(request);
  const sheet = body && body.sheet;
  const answerKey = body && body.answer_key;
  if (!sheet && !answerKey) throw new HttpError(400, "sheet or answer_key is required");
  if (sheet) {
    if (typeof sheet !== "object" || Array.isArray(sheet)) throw new HttpError(400, "sheet object is required");
    if (sheet.id !== id) throw new HttpError(400, "sheet.id must match the URL");
    if (!sheet.title || !Array.isArray(sheet.sections)) throw new HttpError(400, "sheet needs a title and sections");
    record.sheet = presentSheet(sheet);
  }
  if (answerKey) {
    if (typeof answerKey !== "object" || Array.isArray(answerKey)) {
      throw new HttpError(400, "answer_key object is required");
    }
    if (answerKey.sheet_id && answerKey.sheet_id !== id) {
      throw new HttpError(400, "answer_key.sheet_id must match the URL");
    }
    record.answer_key = answerKey;
  }
  if (body && Object.prototype.hasOwnProperty.call(body, "allow_resubmit")) {
    record.allow_resubmit = Boolean(body.allow_resubmit);
  }
  record.updated_at = new Date().toISOString();
  await env.SHEETS.put(sheetKey(id), JSON.stringify(record));
  return json({
    id,
    token: record.token,
    allow_resubmit: record.allow_resubmit,
    updated_at: record.updated_at,
  });
}

async function getSheet(env, id, token) {
  const record = await loadSheet(env, id);
  if (!token || !safeEqual(token, record.token)) {
    throw new HttpError(401, "unauthorized");
  }
  const submission = await readKvJson(env.SUBMISSIONS, subKey(id));
  const sheet = presentSheet(record.sheet);
  if (!submission) return studentJson({ sheet, submitted: false }, false);
  const retry = await readKvJson(env.SUBMISSIONS, retryKey(id));
  const finish = await readKvJson(env.SUBMISSIONS, finishKey(id));
  return studentJson({
    sheet,
    submitted: true,
    submitted_at: submission.submitted_at,
    feedback: feedbackFor(record, submission.answers, retry, finish),
  }, Boolean(finish));
}

async function submitSheet(request, env, id, token) {
  const record = await loadSheet(env, id);
  if (!token || !safeEqual(token, record.token)) {
    throw new HttpError(401, "unauthorized");
  }
  const existing = await env.SUBMISSIONS.get(subKey(id));
  if (existing && !record.allow_resubmit) {
    throw new HttpError(409, "already submitted");
  }
  const body = await readJson(request);
  const timing = cleanTiming(body && body.timing);
  const answers = applyIdk(normalizeAnswers(body && body.answers), timing);
  const submission = {
    sheet_id: id,
    submitted_at: new Date().toISOString(),
    answers,
  };
  if (timing) submission.timing = timing;
  await env.SUBMISSIONS.put(subKey(id), JSON.stringify(submission));
  await env.SUBMISSIONS.delete(retryKey(id));
  await env.SUBMISSIONS.delete(finishKey(id));
  return studentJson({
    ok: true,
    sheet_id: id,
    submitted_at: submission.submitted_at,
    feedback: feedbackFor(record, answers, null, null),
  }, false);
}

async function retrySheet(request, env, id, token) {
  const record = await loadSheet(env, id);
  if (!token || !safeEqual(token, record.token)) throw new HttpError(401, "unauthorized");
  const submission = await readKvJson(env.SUBMISSIONS, subKey(id));
  if (!submission) throw new HttpError(409, "not submitted");
  if (await readKvJson(env.SUBMISSIONS, finishKey(id))) throw new HttpError(409, "already finished");
  const body = await readJson(request);
  const answers = normalizeAnswers(body && body.answers);
  const open = feedbackFor(record, submission.answers, null, null);
  const paths = open.items.filter((item) => item.status === "not_yet").map((item) => item.path);
  if (!paths.length) throw new HttpError(409, "nothing to try again");
  const retry = {
    sheet_id: id,
    retried_at: new Date().toISOString(),
    answers: pickPaths(answers, paths),
    no_credit: true,
  };
  await env.SUBMISSIONS.put(retryKey(id), JSON.stringify(retry));
  return studentJson({
    ok: true,
    feedback: feedbackFor(record, submission.answers, retry, null),
  }, false);
}

async function finishSheet(request, env, id, token) {
  const record = await loadSheet(env, id);
  if (!token || !safeEqual(token, record.token)) throw new HttpError(401, "unauthorized");
  const submission = await readKvJson(env.SUBMISSIONS, subKey(id));
  if (!submission) throw new HttpError(409, "not submitted");
  let finish = await readKvJson(env.SUBMISSIONS, finishKey(id));
  const retry = await readKvJson(env.SUBMISSIONS, retryKey(id));
  if (!finish) {
    const open = feedbackFor(record, submission.answers, retry, null);
    if (open.items.some((item) => item.status === "not_yet") && !retry) {
      throw new HttpError(409, "try the not-yet answers first");
    }
    finish = { finished_at: new Date().toISOString() };
    await env.SUBMISSIONS.put(finishKey(id), JSON.stringify(finish));
  }
  return studentJson({
    ok: true,
    finished_at: finish.finished_at,
    feedback: feedbackFor(record, submission.answers, retry, finish),
  }, true);
}

async function listSubmissions(env, url) {
  const since = url.searchParams.get("since");
  const sheetFilter = url.searchParams.get("sheet");
  let sinceMs = null;
  if (since) {
    sinceMs = Date.parse(since);
    if (Number.isNaN(sinceMs)) throw new HttpError(400, "since must be a date");
  }
  const submissions = [];
  let cursor;
  do {
    const page = await env.SUBMISSIONS.list({ prefix: "sub:", cursor });
    for (const key of page.keys) {
      const raw = await env.SUBMISSIONS.get(key.name);
      if (!raw) continue;
      const submission = JSON.parse(raw);
      if (sinceMs !== null && Date.parse(submission.submitted_at) < sinceMs) continue;
      if (sheetFilter && submission.sheet_id !== sheetFilter) continue;
      submissions.push({
        sheet_id: submission.sheet_id,
        submitted_at: submission.submitted_at,
        has_photos: hasPhotos(submission.answers),
      });
    }
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  submissions.sort((a, b) => a.submitted_at.localeCompare(b.submitted_at));
  return json({ submissions });
}

async function getSubmission(env, id) {
  assertId(id);
  const submission = await readKvJson(env.SUBMISSIONS, subKey(id));
  if (!submission) throw new HttpError(404, "not found");
  const retry = await readKvJson(env.SUBMISSIONS, retryKey(id));
  const finish = await readKvJson(env.SUBMISSIONS, finishKey(id));
  return json({ ...submission, retry, finish });
}

async function getProfile(env) {
  const raw = await env.PROFILE.get("profile");
  return json({ profile: raw ? JSON.parse(raw) : null });
}

async function putProfile(request, env) {
  const body = await readJson(request);
  const profile = body && Object.prototype.hasOwnProperty.call(body, "profile")
    ? body.profile
    : body;
  if (!profile || typeof profile !== "object" || Array.isArray(profile)) {
    throw new HttpError(400, "profile object is required");
  }
  const raw = JSON.stringify(profile);
  if (raw.length > PHOTO_MAX) throw new HttpError(413, "profile exceeds 1 MB");
  await env.PROFILE.put("profile", raw);
  return json({ ok: true });
}

async function loadSheet(env, id) {
  assertId(id);
  const raw = await env.SHEETS.get(sheetKey(id));
  if (!raw) throw new HttpError(404, "not found");
  return JSON.parse(raw);
}

function assertId(id) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$/.test(id)) {
    throw new HttpError(400, "bad id");
  }
}

function sheetKey(id) {
  return `sheet:${id}`;
}

function subKey(id) {
  return `sub:${id}`;
}

function retryKey(id) {
  return `retry:${id}`;
}

function finishKey(id) {
  return `finish:${id}`;
}

function presentSheet(sheet) {
  return sanitizeSheet(stripSecrets(sheet));
}

function feedbackFor(record, answers, retry, finish) {
  return buildFeedback({
    sheet: record.sheet,
    answerKey: record.answer_key,
    answers,
    retry: Boolean(retry),
    finished: Boolean(finish),
  });
}

function studentJson(data, reveal) {
  const body = { ...data };
  if (body.sheet) body.sheet = scrubStudent(body.sheet, false);
  if (body.feedback) body.feedback = scrubStudent(body.feedback, reveal);
  return json(body);
}

function scrubStudent(value, reveal) {
  if (Array.isArray(value)) return value.map((item) => scrubStudent(item, reveal));
  if (!value || typeof value !== "object") return value;
  const drop = new Set([
    "accept",
    "rubric",
    "answer",
    "answer_key",
    "token",
    "secret_marker",
    "mx_id",
    "misconception",
    "wrong",
    "expected",
    "not_attempted_action",
    "solution",
  ]);
  if (!reveal) {
    drop.add("worked_solution");
    drop.add("key");
    drop.add("action");
    drop.add("note");
  }
  const out = {};
  for (const [key, child] of Object.entries(value)) {
    if (drop.has(key)) continue;
    out[key] = scrubStudent(child, reveal);
  }
  return out;
}

async function readKvJson(namespace, key) {
  const raw = await namespace.get(key);
  if (!raw) return null;
  return JSON.parse(raw);
}

function cleanTiming(timing) {
  if (timing == null) return null;
  if (typeof timing !== "object" || Array.isArray(timing)) throw new HttpError(400, "timing must be an object");
  const out = {};
  for (const [qid, row] of Object.entries(timing)) {
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(qid)) throw new HttpError(400, "bad timing id");
    if (!row || typeof row !== "object" || Array.isArray(row)) throw new HttpError(400, "bad timing");
    const item = {};
    if (row.first_seen_at != null) {
      if (typeof row.first_seen_at !== "string" || row.first_seen_at.length > 40) {
        throw new HttpError(400, "bad first_seen_at");
      }
      item.first_seen_at = row.first_seen_at;
    }
    if (row.time_on_question_ms != null) {
      const n = row.time_on_question_ms;
      if (typeof n !== "number" || !Number.isFinite(n) || n < 0 || n > 86_400_000) {
        throw new HttpError(400, "bad time_on_question_ms");
      }
      item.time_on_question_ms = Math.round(n);
    }
    if (row.edit_count != null) {
      if (!Number.isInteger(row.edit_count) || row.edit_count < 0 || row.edit_count > 100_000) {
        throw new HttpError(400, "bad edit_count");
      }
      item.edit_count = row.edit_count;
    }
    if (row.idk != null) {
      if (typeof row.idk !== "boolean") throw new HttpError(400, "bad idk");
      item.idk = row.idk;
    }
    out[qid] = item;
  }
  return out;
}

function applyIdk(answers, timing) {
  if (!timing) return answers;
  for (const [qid, row] of Object.entries(timing)) {
    if (row.idk === true) answers[qid] = { idk: true };
  }
  return answers;
}

function pickPaths(answers, paths) {
  const out = {};
  for (const path of paths) {
    const value = valueAt(answers, path);
    if (value == null) continue;
    setPath(out, path, value);
  }
  return out;
}

function valueAt(root, path) {
  let node = root && root[path[0]];
  for (let i = 1; i < path.length; i++) node = node && node.parts && node.parts[path[i]];
  return node;
}

function setPath(root, path, value) {
  if (path.length === 1) {
    root[path[0]] = value;
    return;
  }
  if (!root[path[0]] || root[path[0]].idk) root[path[0]] = { parts: {} };
  let cursor = root[path[0]];
  for (let i = 1; i < path.length - 1; i++) {
    cursor.parts = cursor.parts || {};
    if (!cursor.parts[path[i]]) cursor.parts[path[i]] = { parts: {} };
    cursor = cursor.parts[path[i]];
  }
  cursor.parts = cursor.parts || {};
  cursor.parts[path[path.length - 1]] = value;
}

function presentedToken(request, url) {
  const query = url.searchParams.get("t");
  const header = request.headers.get("X-Sheet-Token");
  if (query && header && query !== header) return "";
  return query || header || "";
}

function adminOk(request, env) {
  const header = request.headers.get("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!env.ADMIN_TOKEN || !token) return false;
  return safeEqual(token, env.ADMIN_TOKEN);
}

function safeEqual(a, b) {
  const enc = new TextEncoder();
  const left = enc.encode(String(a));
  const right = enc.encode(String(b));
  const length = Math.max(left.length, right.length);
  let diff = left.length ^ right.length;
  for (let i = 0; i < length; i++) {
    diff |= (left[i] || 0) ^ (right[i] || 0);
  }
  return diff === 0;
}

function randomToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function stripSecrets(value) {
  if (Array.isArray(value)) return value.map(stripSecrets);
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      if (STRIP_FROM_SHEET.has(key)) continue;
      out[key] = stripSecrets(child);
    }
    return out;
  }
  return value;
}

function normalizeAnswers(answers) {
  if (!answers || typeof answers !== "object" || Array.isArray(answers)) {
    throw new HttpError(400, "answers must be an object");
  }
  return walkAnswer(answers);
}

function walkAnswer(node) {
  if (Array.isArray(node)) return node.map(walkAnswer);
  if (node && typeof node === "object") {
    if (node.idk === true) return { idk: true };
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      if (key === "photo") {
        if (value) out.photo = normalizePhoto(value);
      } else if (key === "content_type") {
        if (value) out.content_type = normalizePhotoType(value);
      }
      else out[key] = walkAnswer(value);
    }
    if (out.photo && !out.content_type) out.content_type = "image/jpeg";
    if (out.content_type && !out.photo) {
      throw new HttpError(400, "content_type requires a photo");
    }
    return out;
  }
  if (typeof node === "string") {
    if (node.length > TEXT_MAX) throw new HttpError(400, "answer too long");
    return node;
  }
  if (typeof node === "number" || typeof node === "boolean" || node == null) return node;
  throw new HttpError(400, "bad answer");
}

function normalizePhotoType(value) {
  if (value !== "image/jpeg") throw new HttpError(400, "photos must be image/jpeg");
  return value;
}

function normalizePhoto(photo) {
  if (typeof photo !== "string") throw new HttpError(400, "photo must be a string");
  const match = photo.match(/^data:image\/jpeg;base64,([A-Za-z0-9+/=\s]+)$/);
  const b64 = (match ? match[1] : photo).replace(/\s/g, "");
  if (!b64 || !/^[A-Za-z0-9+/=]+$/.test(b64)) {
    throw new HttpError(400, "photo must be base64 jpeg");
  }
  if (b64.length > PHOTO_MAX) throw new HttpError(413, "photo exceeds 1 MB");
  const padding = b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0;
  const bytes = Math.floor((b64.length * 3) / 4) - padding;
  if (bytes > PHOTO_MAX) throw new HttpError(413, "photo exceeds 1 MB");
  return b64;
}

function hasPhotos(node) {
  if (!node || typeof node !== "object") return false;
  if (typeof node.photo === "string") return true;
  return Object.values(node).some((value) => hasPhotos(value));
}

async function readJson(request) {
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > BODY_MAX) throw new HttpError(413, "body too large");
  const text = await request.text();
  if (text.length > BODY_MAX) throw new HttpError(413, "body too large");
  if (!text) throw new HttpError(400, "body must be JSON");
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, "body must be JSON");
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function corsHeaders(origin, env) {
  const allowed = (env.PAGES_ORIGIN || "https://khkreddy.github.io").split(",").map((s) => s.trim()).filter(Boolean);
  const local = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;
  if (!origin || (!allowed.includes(origin) && !local.test(origin))) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Sheet-Token",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function withCors(response, cors) {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(cors)) headers.set(key, value);
  return new Response(response.body, { status: response.status, headers });
}
