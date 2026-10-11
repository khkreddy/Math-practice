/**
 * Daily math-practice API.
 *
 * Storage is Workers KV only (free plan). Do not add R2: an R2 bucket
 * requires a payment method. Photos are base64 JPEG values inside the
 * submission record. Each photo value must be <= 1 MB.
 *
 * Bindings: SHEETS, SUBMISSIONS, PROFILE, ADMIN_TOKEN, PAGES_ORIGIN.
 */

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

  if (parts[0] === "admin") {
    if (!adminOk(request, env)) throw new HttpError(401, "unauthorized");
    return adminRoute(request, env, url, parts.slice(1));
  }

  throw new HttpError(404, "not found");
}

async function adminRoute(request, env, url, parts) {
  const method = request.method;
  if (parts[0] === "sheet" && parts.length === 2 && method === "PUT") {
    return putSheet(request, env, parts[1]);
  }
  if (parts[0] === "sheet" && parts.length === 2 && method === "GET") {
    return getAdminSheet(env, parts[1]);
  }
  if (parts[0] === "submissions" && parts.length === 1 && method === "GET") {
    return listSubmissions(env, url.searchParams.get("since"));
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
    sheet: stripSecrets(sheet),
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

async function getSheet(env, id, token) {
  const record = await loadSheet(env, id);
  if (!token || !safeEqual(token, record.token)) {
    throw new HttpError(401, "unauthorized");
  }
  const existing = await env.SUBMISSIONS.get(subKey(id));
  return json({
    sheet: record.sheet,
    submitted: Boolean(existing),
  });
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
  const answers = normalizeAnswers(body && body.answers);
  const submission = {
    sheet_id: id,
    submitted_at: new Date().toISOString(),
    answers,
  };
  await env.SUBMISSIONS.put(subKey(id), JSON.stringify(submission));
  return json({
    ok: true,
    sheet_id: id,
    submitted_at: submission.submitted_at,
  });
}

async function listSubmissions(env, since) {
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
  const raw = await env.SUBMISSIONS.get(subKey(id));
  if (!raw) throw new HttpError(404, "not found");
  return json(JSON.parse(raw));
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
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function corsHeaders(origin, env) {
  const allowed = env.PAGES_ORIGIN || "https://khkreddy.github.io";
  const local = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;
  if (!origin || (origin !== allowed && !local.test(origin))) return {};
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
