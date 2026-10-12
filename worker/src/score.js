/**
 * Score a stored submission for the student page.
 *
 * The public result uses correct / not_yet / blank / pending_review.
 * Worked solutions, the key, and the next-step line are added only when
 * the caller passes finished. Mix-up ids are never copied onto that result.
 */

const BANNED = /keep\s+practis|\bpracticing\b|\bpractising\b|\bmastery\b|\bmastered\b|\bemerging\b|\bslipping\b|you learned from (this|your) mistake|\bmx[_-]?\d|\bmisconception\b|\bmix-?up\b|\bH\d+#/i;

export function sanitizeSvg(input) {
  if (typeof input !== "string") return "";
  let svg = input.trim();
  const base64 = svg.match(/^data:image\/svg\+xml;base64,([A-Za-z0-9+/=\s]+)$/i);
  if (base64) {
    try {
      svg = atob(base64[1].replace(/\s/g, ""));
    } catch {
      return "";
    }
  } else if (/^data:image\/svg\+xml(?:;charset=[^,;]*)?,/i.test(svg)) {
    const comma = svg.indexOf(",");
    try {
      svg = decodeURIComponent(svg.slice(comma + 1));
    } catch {
      return "";
    }
  }
  svg = svg.trim().replace(/^\uFEFF/, "");
  if (!/<svg\b/i.test(svg)) return "";
  svg = svg.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
  svg = svg.replace(/<script\b[^>]*>/gi, "");
  svg = svg.replace(/<\/script>/gi, "");
  svg = svg.replace(/<foreignObject\b[^>]*>[\s\S]*?<\/foreignObject>/gi, "");
  svg = svg.replace(/<\/?(?:iframe|object|embed|link|meta)\b[^>]*>/gi, "");
  svg = svg.replace(/\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "");
  svg = svg.replace(/\s+style\s*=\s*("[^"]*"|'[^']*')/gi, (full, quoted) => {
    if (/url\s*\(|javascript|expression\s*\(/i.test(quoted)) return "";
    return full;
  });
  svg = svg.replace(/\s+(?:xlink:href|href)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/gi, (full, _quoted, dq, sq, uq) => {
    const val = String(dq ?? sq ?? uq ?? "").trim();
    if (val.startsWith("#") && !/javascript/i.test(val)) return full;
    return "";
  });
  svg = svg.replace(/javascript\s*:/gi, "");
  return svg;
}

export function sanitizeSheet(value) {
  if (Array.isArray(value)) return value.map(sanitizeSheet);
  if (!value || typeof value !== "object") return value;
  const out = {};
  for (const [key, child] of Object.entries(value)) {
    if (key === "figure" && child && typeof child === "object" && !Array.isArray(child)) {
      out.figure = sanitizeFigure(child);
    } else {
      out[key] = sanitizeSheet(child);
    }
  }
  return out;
}

function sanitizeFigure(figure) {
  const out = { ...figure };
  if (typeof out.data === "string") {
    const clean = sanitizeSvg(out.data);
    if (clean) out.data = clean;
    else delete out.data;
  }
  return out;
}

function hasNested(node) {
  return Array.isArray(node.parts) && node.parts.length > 0 && !node.response && node.type !== "mcq";
}

function normalize(text) {
  let value = String(text).trim().toLowerCase();
  value = value.replaceAll("₹", " ");
  value = value.replaceAll("–", "-").replaceAll("—", "-");
  value = value.replace(/\b(rupees|rs\.?|answer|ans)\b/g, " ");
  value = value.replace(/\s+/g, " ");
  value = value.replace(/^[ .:-]+|[ .:-]+$/g, "");
  return value;
}

function tokenSet(text) {
  return new Set(normalize(text).split(/[,;\s]+/).filter(Boolean));
}

function numbers(text) {
  return normalize(text).match(/-?\d+(?:\.\d+)?/g) || [];
}

function sameSet(left, right) {
  if (left.size !== right.size) return false;
  for (const item of left) if (!right.has(item)) return false;
  return true;
}

function sameList(left, right) {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function acceptList(spec) {
  const accept = spec && spec.accept;
  if (accept == null || accept === "") return [];
  if (Array.isArray(accept)) return accept.map((item) => String(item));
  return [String(accept)];
}

function matches(value, spec) {
  const accept = acceptList(spec);
  if (!accept.length) return false;
  const mode = (spec && spec.match) || "text";
  const got = String(value);
  if (mode === "choice") {
    const allowed = new Set(accept.map((item) => item.trim().toLowerCase()));
    return allowed.has(got.trim().toLowerCase());
  }
  if (mode === "set") {
    const gotSet = tokenSet(got);
    return accept.some((item) => sameSet(gotSet, tokenSet(item)));
  }
  if (mode === "number") {
    const gotNumbers = numbers(got);
    return gotNumbers.length > 0 && accept.some((item) => sameList(numbers(item), gotNumbers));
  }
  if (mode === "token") {
    const gotTokens = tokenSet(got);
    return accept.some((item) => [...tokenSet(item)].every((tok) => gotTokens.has(tok)));
  }
  return accept.some((item) => normalize(got) === normalize(item));
}

function leafKind(node, spec) {
  if (node.type === "mcq") return "mcq";
  if (node.type === "construction" || node.response === "photo" || (spec && spec.kind === "photo")) return "photo";
  return "text";
}

function scoreLeaf(node, spec, response) {
  const maxMarks = node.marks == null ? null : node.marks;
  const kind = leafKind(node, spec);
  const idk = Boolean(response && response.idk === true);
  if (kind === "photo") {
    if (idk || !response || !response.photo) {
      return { status: "not_attempted", marks_awarded: 0, max_marks: maxMarks, kind };
    }
    return { status: "needs_review", marks_awarded: null, max_marks: maxMarks, kind };
  }
  if (idk) return { status: "not_attempted", marks_awarded: 0, max_marks: maxMarks, kind };
  const value = response && response.value ? String(response.value) : "";
  if (!value.trim()) return { status: "not_attempted", marks_awarded: 0, max_marks: maxMarks, kind };
  const ok = matches(value, spec || {});
  return {
    status: ok ? "correct" : "incorrect",
    marks_awarded: ok ? maxMarks || 0 : 0,
    max_marks: maxMarks,
    kind,
  };
}

function collectLeaves(node, path, spec, response, qno, leaves) {
  if (hasNested(node)) {
    for (const part of node.parts) {
      collectLeaves(
        part,
        path.concat(part.id),
        (spec && spec.parts && spec.parts[part.id]) || {},
        (response && response.parts && response.parts[part.id]) || {},
        qno,
        leaves,
      );
    }
    return;
  }
  const scored = scoreLeaf(node, spec || {}, response || {});
  const label = path.length === 1
    ? String(qno)
    : `${qno} ${path.slice(1).map((id) => `(${id})`).join(" ")}`;
  leaves.push({
    path,
    qno,
    label,
    prompt: typeof node.text === "string" ? node.text : "",
    spec: spec || {},
    node,
    status: scored.status,
    marks_awarded: scored.marks_awarded,
    max_marks: scored.max_marks,
    kind: scored.kind,
    value: response && response.value ? String(response.value) : "",
    has_photo: Boolean(response && response.photo),
    idk: Boolean(response && response.idk === true),
  });
}

function publicStatus(status) {
  if (status === "correct") return "correct";
  if (status === "needs_review") return "pending_review";
  if (status === "not_attempted") return "blank";
  return "not_yet";
}

function accountLeaves(leaves, questionMarks) {
  if (leaves.length && leaves.every((leaf) => leaf.max_marks != null)) {
    let typedMarks = 0;
    let typedMax = 0;
    let pendingMarks = 0;
    for (const leaf of leaves) {
      if (leaf.status === "needs_review") pendingMarks += leaf.max_marks;
      else {
        typedMarks += leaf.marks_awarded || 0;
        typedMax += leaf.max_marks;
      }
    }
    return { typed_marks: typedMarks, typed_max: typedMax, pending_marks: pendingMarks };
  }
  const max = questionMarks || 0;
  if (leaves.some((leaf) => leaf.status === "needs_review")) {
    return { typed_marks: 0, typed_max: 0, pending_marks: max };
  }
  const allCorrect = leaves.length > 0 && leaves.every((leaf) => leaf.status === "correct");
  return { typed_marks: allCorrect ? max : 0, typed_max: max, pending_marks: 0 };
}

function textField(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function solutionText(spec) {
  const worked = spec.worked_solution || (spec.feedback && spec.feedback.worked_solution);
  if (typeof worked === "string") return worked.trim();
  if (worked && Array.isArray(worked.steps)) {
    return worked.steps.map((step) => String(step)).filter((step) => step.trim()).join("\n").trim();
  }
  return "";
}

function rawAction(leaf) {
  const spec = leaf.spec || {};
  const feedback = spec.feedback || {};
  if (leaf.status === "not_attempted") {
    return textField(spec.not_attempted_action, feedback.not_attempted_action, spec.action, feedback.action);
  }
  return textField(spec.action, feedback.action);
}

function fallbackAction(leaf) {
  if (leaf.kind === "photo") return `Take a picture of your drawing for question ${leaf.label}.`;
  if (leaf.kind === "mcq") return `Choose one of the options for question ${leaf.label}.`;
  if (leaf.status === "not_attempted") return `Write an answer for question ${leaf.label}.`;
  return `Work question ${leaf.label} again and write the value it asks for.`;
}

function safeLine(text, fallback) {
  if (!text || BANNED.test(text)) return fallback;
  return text;
}

function noteFor(spec) {
  const feedback = spec.feedback || {};
  const note = textField(spec.note, feedback.note);
  if (!note || BANNED.test(note)) return "No verified notes for this item.";
  return note;
}

function yourAnswer(leaf) {
  if (leaf.idk) return "I don't know";
  if (leaf.kind === "photo") return leaf.has_photo ? "Picture sent" : "No picture";
  if (!leaf.value.trim()) return "No answer";
  if (leaf.kind === "mcq" && leaf.node && Array.isArray(leaf.node.options)) {
    const option = leaf.node.options.find((item) => item.id === leaf.value);
    if (option) return `${option.id}. ${option.text}`;
  }
  return leaf.value;
}

function keyText(leaf) {
  const accept = acceptList(leaf.spec);
  if (!accept.length || leaf.kind === "photo") return "";
  if (leaf.kind === "mcq" && leaf.node && Array.isArray(leaf.node.options)) {
    return accept.map((id) => {
      const option = leaf.node.options.find((item) => String(item.id).toLowerCase() === id.toLowerCase());
      return option ? `${option.id}. ${option.text}` : id;
    }).join(" or ");
  }
  return accept.join(" or ");
}

function toPublic(leaf, finished) {
  const status = publicStatus(leaf.status);
  const item = {
    id: leaf.path[0],
    path: leaf.path,
    qno: leaf.qno,
    label: leaf.label,
    prompt: leaf.prompt,
    status,
    max_marks: leaf.max_marks,
    marks_awarded: leaf.status === "needs_review" ? null : (leaf.marks_awarded ?? 0),
    your_answer: yourAnswer(leaf),
  };
  if (!finished) return item;
  const revealed = keyText(leaf);
  if (revealed) item.key = revealed;
  const solution = solutionText(leaf.spec);
  if (solution && status !== "pending_review") item.worked_solution = solution;
  if (status === "not_yet" || status === "blank") {
    item.action = safeLine(rawAction(leaf), fallbackAction(leaf));
    item.note = noteFor(leaf.spec);
  } else if (status === "pending_review") {
    item.action = "Your teacher will check this drawing.";
  }
  return item;
}

export function buildFeedback({ sheet, answerKey, answers, retry, finished }) {
  const items = [];
  const summary = { typed_marks: 0, typed_max: 0, pending_marks: 0 };
  const questions = (answerKey && answerKey.questions) || {};
  const given = answers || {};
  for (const section of (sheet && sheet.sections) || []) {
    for (const question of section.questions || []) {
      const leaves = [];
      collectLeaves(question, [question.id], questions[question.id] || {}, given[question.id] || {}, question.qno, leaves);
      const account = accountLeaves(leaves, question.marks || 0);
      summary.typed_marks += account.typed_marks;
      summary.typed_max += account.typed_max;
      summary.pending_marks += account.pending_marks;
      for (const leaf of leaves) items.push(toPublic(leaf, Boolean(finished)));
    }
  }
  let phase = "checked";
  if (finished) phase = "finished";
  else if (retry) phase = "retried";
  return { phase, summary, items };
}
