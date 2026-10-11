(() => {
  const app = document.getElementById("app");
  const params = new URLSearchParams(location.search);
  const sheetId = params.get("sheet") || "";
  const token = params.get("t") || "";
  const apiOverride = params.get("api") || "";
  const configured = (window.MATH_PRACTICE && window.MATH_PRACTICE.workerUrl) || "";
  const workerUrl = (apiOverride || configured).replace(/\/$/, "");

  const state = {
    sheet: null,
    answers: {},
    screen: "loading",
    message: "",
    submittedAt: "",
  };

  const draftKey = () => `math-practice-draft:${sheetId}`;

  function renderMath(el, text) {
    el.replaceChildren();
    const src = text || "";
    const re = /\$([^$]+)\$/g;
    let last = 0;
    let match;
    while ((match = re.exec(src))) {
      if (match.index > last) el.append(src.slice(last, match.index));
      const span = document.createElement("span");
      span.className = "math";
      if (window.katex) {
        window.katex.render(match[1], span, { throwOnError: false, displayMode: false });
      } else {
        span.textContent = match[1];
      }
      el.append(span);
      last = match.index + match[0].length;
    }
    if (last < src.length) el.append(src.slice(last));
  }

  function nestedParts(node) {
    return Array.isArray(node.parts) && node.parts.length && !node.response && node.type !== "mcq";
  }

  function leavesOf(node, path) {
    if (nestedParts(node)) {
      return node.parts.flatMap((part) => leavesOf(part, path.concat(part.id)));
    }
    if (node.type === "mcq") return [{ path, kind: "mcq", node }];
    if (node.type === "construction" || node.response === "photo") {
      return [{ path, kind: "photo", node }];
    }
    const long = node.type === "word_problem" || (node.marks || 0) >= 3;
    return [{ path, kind: "text", node, long }];
  }

  function allLeaves() {
    const leaves = [];
    for (const section of state.sheet.sections) {
      for (const question of section.questions) {
        for (const leaf of leavesOf(question, [question.id])) {
          leaf.qno = question.qno;
          leaves.push(leaf);
        }
      }
    }
    return leaves;
  }

  function getAt(path) {
    let node = state.answers[path[0]];
    for (let i = 1; i < path.length; i++) {
      node = node && node.parts && node.parts[path[i]];
    }
    return node || {};
  }

  function setAt(path, patch) {
    if (!state.answers[path[0]]) state.answers[path[0]] = {};
    let cursor = state.answers[path[0]];
    for (let i = 1; i < path.length; i++) {
      cursor.parts = cursor.parts || {};
      if (!cursor.parts[path[i]]) cursor.parts[path[i]] = {};
      cursor = cursor.parts[path[i]];
    }
    Object.assign(cursor, patch);
    autosave();
  }

  function leafFilled(leaf) {
    const value = getAt(leaf.path);
    if (leaf.kind === "photo") return Boolean(value.photo);
    return Boolean(value.value && String(value.value).trim());
  }

  function prune(node) {
    if (!node || typeof node !== "object") return node;
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      if ((key === "photo" || key === "content_type" || key === "value") && !value) continue;
      if (value && typeof value === "object") {
        const child = prune(value);
        if (child && Object.keys(child).length) out[key] = child;
      } else if (value !== "" && value != null) {
        out[key] = value;
      }
    }
    return out;
  }

  function leafLabel(leaf) {
    if (leaf.path.length === 1) return String(leaf.qno);
    return `${leaf.qno} ${leaf.path.slice(1).map((id) => `(${id})`).join(" ")}`;
  }

  function autosave() {
    const note = document.querySelector("[data-save-note]");
    try {
      localStorage.setItem(draftKey(), JSON.stringify(state.answers));
      if (note) note.textContent = "Saved on this phone.";
    } catch {
      try {
        const slim = JSON.parse(JSON.stringify(state.answers));
        stripPhotos(slim);
        localStorage.setItem(draftKey(), JSON.stringify(slim));
        if (note) note.textContent = "Written answers are saved on this phone. Pictures stay until you send or leave.";
      } catch {
        if (note) note.textContent = "Could not save a copy on this phone. Stay on this page until you send.";
      }
    }
  }

  function stripPhotos(node) {
    if (!node || typeof node !== "object") return;
    delete node.photo;
    delete node.content_type;
    Object.values(node).forEach(stripPhotos);
  }

  function loadDraft() {
    try {
      const raw = localStorage.getItem(draftKey());
      if (raw) state.answers = JSON.parse(raw) || {};
    } catch {
      state.answers = {};
    }
  }

  function clearDraft() {
    try { localStorage.removeItem(draftKey()); } catch { /* ignore */ }
  }

  function h(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
  }

  function renderFigure(figure) {
    const wrap = h("div", "figure");
    if (!figure || !/^figures\/[A-Za-z0-9._-]+\.svg$/.test(figure.src || "")) {
      wrap.append(h("p", "error", "Figure missing."));
      return wrap;
    }
    const img = document.createElement("img");
    img.src = figure.src;
    img.alt = figure.alt || "Figure";
    wrap.append(img);
    return wrap;
  }

  function renderMcq(node, path) {
    const box = document.createElement("div");
    const current = getAt(path).value || "";
    for (const option of node.options || []) {
      const label = h("label", "choice");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = path.join("-");
      input.value = option.id;
      input.checked = current === option.id;
      input.addEventListener("change", () => setAt(path, { value: option.id }));
      const text = h("span");
      const letter = h("strong", null, `(${option.id}) `);
      text.append(letter);
      const rest = h("span");
      renderMath(rest, option.text);
      text.append(rest);
      label.append(input, text);
      box.append(label);
    }
    return box;
  }

  function renderText(leaf, path) {
    const input = document.createElement("textarea");
    input.rows = leaf.long ? 5 : 2;
    input.value = getAt(path).value || "";
    input.placeholder = "Type your answer";
    input.addEventListener("input", () => setAt(path, { value: input.value }));
    return input;
  }

  async function compressToJpeg(file) {
    const bitmap = await createImageBitmap(file);
    try {
      let maxEdge = Math.min(1600, Math.max(bitmap.width, bitmap.height));
      for (let attempt = 0; attempt < 6; attempt++) {
        const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
        const width = Math.max(1, Math.round(bitmap.width * scale));
        const height = Math.max(1, Math.round(bitmap.height * scale));
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(bitmap, 0, 0, width, height);
        let quality = 0.82;
        let blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
        while (blob && blob.size > 400 * 1024 && quality > 0.45) {
          quality = Math.round((quality - 0.08) * 100) / 100;
          blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
        }
        if (blob && blob.size <= 400 * 1024) return blob;
        maxEdge = Math.round(maxEdge * 0.75);
      }
      throw new Error("too big");
    } finally {
      if (bitmap.close) bitmap.close();
    }
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const raw = String(reader.result || "");
        const comma = raw.indexOf(",");
        resolve(comma >= 0 ? raw.slice(comma + 1) : raw);
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
  }

  function renderPhoto(path) {
    const box = h("div", "photo-box");
    const stored = getAt(path);
    if (stored.photo) {
      const img = document.createElement("img");
      img.className = "photo-preview";
      img.alt = "Your picture";
      img.src = `data:image/jpeg;base64,${stored.photo}`;
      const retake = h("button", "secondary", "Retake");
      retake.type = "button";
      retake.addEventListener("click", () => {
        const fresh = getAt(path);
        delete fresh.photo;
        delete fresh.content_type;
        autosave();
        fillPhoto(box, path);
      });
      box.append(img, h("p", "save-note", "Picture ready."), retake);
      return box;
    }
    fillPhoto(box, path);
    return box;
  }

  function fillPhoto(box, path) {
    box.replaceChildren();
    const actions = h("div", "photo-actions");
    const note = h("p", "save-note", "Take a picture of your drawing, or choose one you already have.");
    const cameraBtn = h("button", "primary", "Take a picture");
    cameraBtn.type = "button";
    const camera = document.createElement("input");
    camera.type = "file";
    camera.accept = "image/*";
    camera.setAttribute("capture", "environment");
    camera.hidden = true;
    const galleryBtn = h("button", "secondary", "Choose from gallery");
    galleryBtn.type = "button";
    const gallery = document.createElement("input");
    gallery.type = "file";
    gallery.accept = "image/*";
    gallery.hidden = true;
    cameraBtn.addEventListener("click", () => camera.click());
    galleryBtn.addEventListener("click", () => gallery.click());
    const take = async (input) => {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      note.textContent = "Making the picture smaller…";
      cameraBtn.disabled = true;
      galleryBtn.disabled = true;
      try {
        const blob = await compressToJpeg(file);
        const photo = await blobToBase64(blob);
        if (photo.length > 1000000) throw new Error("too big");
        setAt(path, { photo, content_type: "image/jpeg" });
        const preview = renderPhoto(path);
        box.replaceWith(preview);
      } catch {
        note.textContent = "That picture could not be used. Try another one.";
        cameraBtn.disabled = false;
        galleryBtn.disabled = false;
      }
    };
    camera.addEventListener("change", () => take(camera));
    gallery.addEventListener("change", () => take(gallery));
    actions.append(cameraBtn, galleryBtn);
    box.append(note, actions, camera, gallery);
  }

  function renderNode(node, path) {
    const block = document.createElement("div");
    if (node.text) {
      const p = document.createElement("p");
      renderMath(p, node.text);
      block.append(p);
    }
    if (node.figure) block.append(renderFigure(node.figure));
    if (node.type === "mcq") {
      block.append(renderMcq(node, path));
      return block;
    }
    if (nestedParts(node)) {
      for (const part of node.parts) {
        const wrap = h("div", "part");
        const head = h("div", "part-head");
        head.append(h("span", null, `(${part.id})`));
        if (part.marks) head.append(h("span", "marks", part.marks === 1 ? "1 mark" : `${part.marks} marks`));
        wrap.append(head, renderNode(part, path.concat(part.id)));
        block.append(wrap);
      }
      return block;
    }
    const leaf = leavesOf(node, path)[0];
    if (leaf.kind === "photo") block.append(renderPhoto(path));
    else block.append(renderText(leaf, path));
    return block;
  }

  function renderQuiz() {
    const sheet = state.sheet;
    app.replaceChildren();
    const top = document.createElement("header");
    top.className = "top";
    top.append(h("h1", null, sheet.title));
    top.append(h("p", "meta", `${sheet.subject} · ${sheet.total_marks} marks`));
    top.append(h("p", "save-note", null));
    top.querySelector(".save-note").dataset.saveNote = "1";
    top.querySelector(".save-note").textContent = "Your answers stay on this phone until you send them.";
    app.append(top);
    if (sheet.instructions && sheet.instructions.length) {
      const list = h("ul", "instructions");
      for (const line of sheet.instructions) list.append(h("li", null, line));
      app.append(list);
    }
    for (const section of sheet.sections) {
      const sec = h("section", "sheet-section");
      const title = document.createElement("h2");
      title.append(document.createTextNode(section.title));
      title.append(h("span", null, section.marks_scheme));
      sec.append(title);
      if (section.instruction) sec.append(h("p", "instruction", section.instruction));
      for (const question of section.questions) {
        const article = h("article", "question");
        article.id = `q-${question.id}`;
        const head = h("div", "qhead");
        head.append(h("span", null, String(question.qno)));
        head.append(h("span", "marks", question.marks === 1 ? "1 mark" : `${question.marks} marks`));
        article.append(head, renderNode(question, [question.id]));
        sec.append(article);
      }
      app.append(sec);
    }
    const bar = h("div", "submit-bar");
    const button = h("button", "primary", "Check and send");
    button.type = "button";
    button.addEventListener("click", () => {
      state.screen = "confirm";
      render();
    });
    bar.append(button);
    app.append(bar);
  }

  function renderConfirm() {
    const leaves = allLeaves();
    const missing = leaves.filter((leaf) => !leafFilled(leaf));
    app.replaceChildren();
    const card = h("div", "card");
    card.append(h("h1", null, "Send this sheet?"));
    card.append(h("p", null, `You answered ${leaves.length - missing.length} of ${leaves.length} parts.`));
    const back = h("button", "secondary", "Go back");
    back.type = "button";
    back.addEventListener("click", () => {
      state.screen = "quiz";
      render();
    });
    const send = h("button", "primary", "Send my answers");
    send.type = "button";
    send.addEventListener("click", () => sendAnswers(send));
    const bar = h("div", "bar");
    bar.append(back, send);
    card.append(bar);
    if (missing.length) {
      card.append(h("p", "save-note", "You can go back and fill these, or send the sheet as it is."));
      card.append(h("p", null, "Still empty:"));
      const list = h("ul", "plain");
      for (const leaf of missing) list.append(h("li", "missing", leafLabel(leaf)));
      card.append(list);
    } else {
      card.append(h("p", null, "Every part has an answer."));
    }
    app.append(card);
  }

  function renderSubmitted() {
    app.replaceChildren();
    const card = h("div", "card");
    card.append(h("h1", "ok-title", "Sent"));
    card.append(h("p", null, "Your answers are with your teacher. You can close this page."));
    if (state.submittedAt) {
      const when = new Date(state.submittedAt);
      const label = Number.isNaN(when.getTime()) ? state.submittedAt : when.toLocaleString();
      card.append(h("p", "save-note", `Sent at ${label}.`));
    }
    app.append(card);
  }

  function renderMessage(title, text) {
    app.replaceChildren();
    const card = h("div", "card");
    card.append(h("h1", null, title));
    card.append(h("p", null, text));
    app.append(card);
  }

  async function sendAnswers(button) {
    button.disabled = true;
    button.textContent = "Sending…";
    try {
      const res = await fetch(`${workerUrl}/submit/${encodeURIComponent(sheetId)}?t=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: prune(state.answers) }),
      });
      const payload = await res.json().catch(() => ({}));
      if (res.status === 409) {
        clearDraft();
        state.submittedAt = "";
        state.screen = "submitted";
        render();
        return;
      }
      if (!res.ok) throw new Error(payload.error || "Could not send");
      clearDraft();
      state.submittedAt = payload.submitted_at || "";
      state.screen = "submitted";
      render();
    } catch {
      button.disabled = false;
      button.textContent = "Send my answers";
      const note = h("p", "error", "Could not send. Check the connection and try again. Your answers are still on this phone.");
      button.parentElement.append(note);
    }
  }

  function render() {
    if (state.screen === "quiz") renderQuiz();
    else if (state.screen === "confirm") renderConfirm();
    else if (state.screen === "submitted") renderSubmitted();
    else renderMessage("Something went wrong", state.message || "Try the link again.");
  }

  async function start() {
    if (!sheetId || !token) {
      renderMessage("Open your link", "Use the link you were sent. It includes the sheet and a code.");
      return;
    }
    if (!workerUrl) {
      renderMessage("Sheet not ready", "This practice link is not connected yet. Ask the person who sent it to finish setting it up.");
      return;
    }
    try {
      const res = await fetch(`${workerUrl}/sheet/${encodeURIComponent(sheetId)}?t=${encodeURIComponent(token)}`);
      const payload = await res.json().catch(() => ({}));
      if (res.status === 401) {
        renderMessage("Link not valid", "This link does not open the sheet. Ask for a new one.");
        return;
      }
      if (!res.ok) throw new Error(payload.error || "load failed");
      state.sheet = payload.sheet;
      document.title = payload.sheet.title || "Practice sheet";
      if (payload.submitted) {
        clearDraft();
        state.screen = "submitted";
        state.message = "";
        render();
        return;
      }
      loadDraft();
      state.screen = "quiz";
      render();
    } catch {
      renderMessage("Could not load the sheet", "Check the connection and open the link again.");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
