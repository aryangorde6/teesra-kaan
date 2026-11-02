// The recording studio: one card at a time, recorded the way the live page hears a call, then labelled by listening.
// The warning lines the page speaks are cards too, under "Warnings": recorded, never labelled.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const store = {
  get(k) { try { return localStorage.getItem("studio." + k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem("studio." + k, v); } catch { /* private window */ } },
};

let cards = [];
let split = store.get("split") || "test";
let current = null;
let recorder = null;
let take = null;
let solo = null; // a solo take in progress: the line being said, when each line began, the listener's audio

const fmt = (s) => {
  if (s == null || s === "") return "–";
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(1).padStart(4, "0")}`;
};
const half = (s) => Math.max(0, Math.round(s * 2) / 2);

async function load() {
  cards = await (await fetch("/api/cards")).json();
  renderList();
  const want = location.hash.slice(1) || store.get("card");
  const first = cards.find((c) => c.id === want) || cards.find((c) => c.split === split && !c.recorded) || cards[0];
  if (first && first.split !== split) setSplit(first.split);
  show(first.id);
}

function progress() {
  const part = (s) => {
    const of = cards.filter((c) => c.split === s);
    return `${s}: ${of.filter((c) => c.recorded).length}/${of.length} recorded, ${of.filter((c) => c.label).length} labelled`;
  };
  const lines = cards.filter((c) => c.split === "voice");
  $("#progress").textContent = `${part("dev")} · ${part("test")} · ${part("paraphrase")} · warnings:${lines.filter((c) => c.recorded).length}/${lines.length} recorded`;
}

function renderList() {
  progress();
  document.querySelectorAll(".filters button").forEach((b) => b.setAttribute("aria-checked", b.dataset.split === split));
  const ol = $("#cards");
  ol.replaceChildren(...cards.filter((c) => c.split === split).map((c) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.dataset.id = c.id;
    b.setAttribute("aria-current", current && current.id === c.id);
    const name = document.createElement("span");
    name.textContent = `${c.n ? `${c.n}. ` : ""}${c.id} · ${c.language}`;
    const state = document.createElement("span");
    state.className = "state";
    if (c.kind === "warning") state.innerHTML = c.recorded ? '<span class="done">recorded</span>' : c.stale ? "words changed" : "to record";
    else state.innerHTML = c.label ? '<span class="done">labelled</span>' : c.recorded ? "recorded" : "to record";
    b.append(name, state);
    b.addEventListener("click", () => show(c.id));
    li.append(b);
    return li;
  }));
}

function setSplit(s) {
  split = s;
  store.set("split", s);
  renderList();
}

document.querySelectorAll(".filters button").forEach((b) => b.addEventListener("click", () => setSplit(b.dataset.split)));

const LANGUAGE = { en: "English", hi: "Hindi", mr: "Marathi" };
const again = (c) => c.recorded || c.stale; // a take is saved, so recording replaces it

function show(id) {
  if (recorder) return; // never leave a card mid-recording
  current = cards.find((c) => c.id === id);
  store.set("card", id);
  history.replaceState(null, "", "#" + id);
  take = null;
  const view = $("#card");
  const c = current;
  if (c.kind === "warning") { showLine(c, view); return; }
  view.replaceChildren($("#card-tpl").content.cloneNode(true));
  const what = c.is_scam ? `scam, pattern ${c.pattern}` : `genuine${c.kind ? ", " + c.kind : ""}`;
  $(".title", view).textContent = `${c.n ? `${c.n}. ` : ""}${c.id} · ${c.split} · ${c.language} · ${what}${c.from ? ` · rewritten from ${c.from}` : ""}`;
  $(".roles", view).textContent = c.roles ? `Caller: ${c.roles.caller}. Listener: ${c.roles.listener}.` : "";
  // The paraphrase test is only a test while the words the keyword lists look for stay out.
  if (c.split === "paraphrase") $(".say", view).textContent = "Read these lines as written. They leave out certain words on purpose (police, arrest, OTP, PIN, bank, video call, refund and the like), so don't put any back in. Keep the made-up names and numbers.";
  renderLines(c, view);
  // A paraphrase card can be recorded by one person: they read the caller, the laptop says the listener's lines.
  if (c.solo) {
    $(".solo", view).hidden = false;
    const box = $(".solo-box", view);
    box.checked = store.get("solo") === "1";
    const steps = () => { $(".steps", view).hidden = box.checked; $(".solo-steps", view).hidden = !box.checked; };
    box.addEventListener("change", () => { store.set("solo", box.checked ? "1" : "0"); steps(); });
    steps();
  }
  $(".voices", view).value = store.get("voices") || "";
  $(".labeller", view).value = store.get("labeller") || "";
  $(".rec-btn", view).addEventListener("click", toggleRecording);
  $(".save-take", view).addEventListener("click", saveTake);
  $(".discard", view).addEventListener("click", discardTake);
  $(".save-label", view).addEventListener("click", saveLabel);
  if (c.recorded) {
    $(".rec-btn", view).textContent = "Record again (replaces this take)";
    $(".rec-status", view).textContent = "Recorded. Record again only if this take is unusable; its label is cleared.";
    openLabelling();
  }
  renderList();
}

// A warning line: the words, the recorder, and the saved take as the page will play it.
function showLine(c, view) {
  view.replaceChildren($("#voice-tpl").content.cloneNode(true));
  const where = c.country === "US" ? " · for the US page" : "";
  $(".title", view).textContent = `${c.id} · ${LANGUAGE[c.language]} · ${c.level === "red" ? "red warning" : "amber warning"}${where}`;
  renderLines(c, view);
  $(".voices", view).value = store.get("line-voice") || "";
  $(".rec-btn", view).addEventListener("click", toggleRecording);
  $(".save-take", view).addEventListener("click", saveTake);
  $(".discard", view).addEventListener("click", discardTake);
  if (again(c)) {
    $(".rec-btn", view).textContent = "Record again (replaces this take)";
    $(".saved", view).hidden = false;
    $(".saved-audio", view).src = `/api/voice/${c.id}?t=${Date.now()}`;
    $(".rec-status", view).textContent = c.recorded
      ? "Recorded. The page plays this take."
      : "Recorded for words that have changed since, so the page doesn't play it. Record it again.";
  }
  renderList();
}

function renderLines(c, view) {
  // After a solo take, each line shows when it began; clicking it plays the take from there.
  let times = null;
  try { times = c.recorded && JSON.parse(store.get("times." + c.id) || "null"); } catch { times = null; }
  $(".lines", view).replaceChildren(...c.lines.map(([who, text, how], n) => {
    const li = document.createElement("li");
    li.className = who;
    li.innerHTML = `<span class="who"></span><span class="text deva"></span>`;
    $(".who", li).textContent = who + (how ? " · " : "");
    if (how) { const h = document.createElement("span"); h.className = "how"; h.textContent = how; $(".who", li).append(h); }
    if (times && times[n] != null) {
      const at = document.createElement("button");
      at.className = "at-line";
      at.textContent = fmt(times[n]);
      at.addEventListener("click", () => { const a = $(".label-audio", view); a.currentTime = times[n]; a.play(); });
      $(".who", li).append(" ", at);
    }
    $(".text", li).textContent = text;
    return li;
  }));
}

// --- Solo takes (test and paraphrase cards) -----------------------------------

function soloAt(n, view) {
  solo.line = n;
  solo.times[n] = (performance.now() - solo.started) / 1000;
  view.querySelectorAll(".lines li").forEach((li, i) => li.classList.toggle("now", i === n));
  view.querySelectorAll(".lines li")[n].scrollIntoView({ block: "nearest" });
  const [who] = current.lines[n];
  if (who !== "listener") {
    $(".rec-status", view).textContent = "Read the highlighted line, then press Space.";
    return;
  }
  // Played silently, only to time the line: the studio lays the line into the take when it's saved, so nothing
  // comes out of the laptop's speaker (evaluation rule v1.6.1).
  $(".rec-status", view).textContent = "The listener is answering (silently, it's added to the take). Wait…";
  solo.audio = new Audio(`/api/solo/${current.id}/${n}`);
  solo.audio.muted = true;
  solo.audio.onended = () => { solo.audio = null; soloNext(view); };
  solo.audio.play().catch(() => { solo.audio = null; $(".rec-status", view).textContent = "The listener's line didn't play. Press Space to go on."; });
}

function soloNext(view) {
  if (!solo || solo.audio) return; // the listener is still speaking
  if (solo.line + 1 < current.lines.length) { soloAt(solo.line + 1, view); return; }
  $(".rec-status", view).textContent = "That was the last line.";
  view.querySelectorAll(".lines li").forEach((li) => li.classList.remove("now"));
  setTimeout(() => recorder && recorder.stop(), 800); // a moment of the room after the last word
}

// --- Recording ---------------------------------------------------------------

async function toggleRecording() {
  const view = $("#card");
  const status = $(".rec-status", view);
  status.classList.remove("err");
  if (recorder) { recorder.stop(); return; }
  const line = current.kind === "warning";
  if (!$(".consent-box", view).checked || !$(".voices", view).value.trim() || (line && !$(".publish-box", view).checked)) {
    status.textContent = line ? "Add your initials and tick both boxes first." : "Add the voices' initials and tick the consent box first.";
    status.classList.add("err");
    return;
  }
  let stream;
  try {
    // The same microphone settings as the live page, so the test hears what Teesra Kaan hears.
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: true, autoGainControl: true },
    });
  } catch (e) {
    status.textContent = "The microphone is blocked. Allow it in the browser's address bar and try again.";
    status.classList.add("err");
    return;
  }
  const type = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
  const rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
  const chunks = [];
  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const buf = new Float32Array(analyser.fftSize);
  const started = performance.now();
  const btn = $(".rec-btn", view);
  const soloBox = $(".solo-box", view);
  solo = soloBox && !$(".solo", view).hidden && soloBox.checked ? { started, times: {}, line: -1, audio: null } : null;
  // A timer, not animation frames, so the clock keeps running if the page is in the background.
  const tick = setInterval(() => {
    analyser.getFloatTimeDomainData(buf);
    const rms = Math.sqrt(buf.reduce((a, v) => a + v * v, 0) / buf.length);
    $(".meter span", view).style.width = `${Math.min(100, rms * 400)}%`;
    const s = (performance.now() - started) / 1000;
    $(".timer", view).textContent = `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  }, 100);
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.onstop = () => {
    clearInterval(tick);
    stream.getTracks().forEach((t) => t.stop());
    ctx.close();
    recorder = null;
    btn.classList.remove("on");
    btn.textContent = again(current) ? "Record again (replaces this take)" : "Start recording";
    $(".meter span", view).style.width = "0";
    take = new Blob(chunks, { type: rec.mimeType });
    take.solo = solo ? solo.times : null;
    if (solo && solo.audio) solo.audio.pause();
    solo = null;
    view.querySelectorAll(".lines li").forEach((li) => li.classList.remove("now"));
    $(".take-audio", view).src = URL.createObjectURL(take);
    $(".take", view).hidden = false;
    status.textContent = "Listen back if you like, then save it, or discard it and record again.";
  };
  recorder = rec;
  rec.start(1000);
  btn.classList.add("on");
  btn.textContent = "Stop";
  $(".take", view).hidden = true;
  status.textContent = line ? "Recording. Say the line, then press Stop." : "Recording. Dial now.";
  if (solo) { btn.blur(); soloAt(0, view); } // Space now moves through the lines; it must not press Stop
}

async function saveTake() {
  const view = $("#card");
  const status = $(".rec-status", view);
  if (!take) return;
  const line = current.kind === "warning";
  const old = line ? "The old one is kept in recordings/replaced/." : "The old one is kept in recordings/replaced/, and its label is cleared.";
  if (again(current) && !confirm(`Replace the saved take of ${current.id}? ${old}`)) return;
  const voices = $(".voices", view).value.trim();
  store.set(line ? "line-voice" : "voices", voices); // a line has one voice, not a call's cast
  const q = new URLSearchParams({ voices, consent: $(".consent-box", view).checked ? "1" : "0",
    publish: $(".publish-box", view).checked ? "1" : "0", replace: again(current) ? "1" : "0", solo: take.solo ? "1" : "0" });
  const times = take.solo;
  if (times) q.set("times", JSON.stringify(times));
  $(".save-take", view).disabled = true;
  status.textContent = line ? "Trimming and levelling…" : "Saving…";
  try {
    const r = await fetch(`/api/${line ? "voice" : "recording"}/${current.id}?${q}`, { method: "POST", body: take });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || r.statusText);
    current.recorded = true;
    current.stale = false;
    current.label = null;
    store.set("times." + current.id, times ? JSON.stringify(times) : "null");
    take = null;
    show(current.id);
    $(".rec-status").textContent = line
      ? `Saved (${fmt(body.seconds)} once trimmed). The page plays it from now on; listen to it above.`
      : `Saved ${body.path} (${fmt(body.seconds)}). Now mark its times below.`;
  } catch (e) {
    status.textContent = e.message;
    status.classList.add("err");
    $(".save-take", view).disabled = false;
  }
}

function discardTake() {
  take = null;
  const view = $("#card");
  $(".take", view).hidden = true;
  $(".rec-status", view).textContent = "Discarded.";
}

// --- Labelling ---------------------------------------------------------------

let marks = { t0: null, t_ask: null };
let peaks = null;

async function openLabelling() {
  const view = $("#card");
  const c = current;
  const panel = $(".label", view);
  panel.hidden = false;
  marks = { t0: c.label ? num(c.label.t0) : null, t_ask: c.label ? num(c.label.t_ask) : null };
  $(".notes", view).value = c.label ? c.label.notes : "";
  if (c.label) $(".label-status", view).textContent = `Saved ${c.label.labelled_at} by ${c.label.labeller}.`;
  $(".hint", view).innerHTML = c.is_scam
    ? "<b>t0</b>: the first word of the caller's first scam move: the first false claim or pressure (authority, threat, urgency, secrecy, a parcel, a prize). Greetings and \"am I speaking to…\" don't count.<br><b>Ask</b>: the first word of the sentence where the caller first asks for an OTP or PIN, money, an app or link. Leave it empty if they never ask."
    : "A genuine call has no t0 and no ask. Listen through once, note anything unusual, and save.";
  const audio = $(".label-audio", view);
  audio.src = `/api/recording/${c.id}?v=${Date.now()}`;
  renderMarks();
  peaks = null;
  try {
    const data = await (await fetch(audio.src)).arrayBuffer();
    const ctx = new AudioContext();
    const decoded = await ctx.decodeAudioData(data);
    ctx.close();
    peaks = toPeaks(decoded.getChannelData(0), decoded.duration);
  } catch { peaks = null; }
  if (current !== c) return;
  drawWave();
  audio.addEventListener("timeupdate", drawWave);
  audio.addEventListener("seeked", drawWave);
  const canvas = $(".wave", view);
  canvas.addEventListener("pointerdown", (e) => {
    if (!peaks) return;
    const rect = canvas.getBoundingClientRect();
    audio.currentTime = ((e.clientX - rect.left) / rect.width) * peaks.duration;
    drawWave();
  });
  new ResizeObserver(drawWave).observe(canvas);
}

const num = (v) => (v === "" || v == null ? null : Number(v));

function toPeaks(samples, duration) {
  const n = 1200;
  const step = Math.max(1, Math.floor(samples.length / n));
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let m = 0;
    for (let j = i * step; j < Math.min(samples.length, (i + 1) * step); j++) m = Math.max(m, Math.abs(samples[j]));
    out[i] = m;
  }
  const top = Math.max(...out, 1e-6);
  return { values: out.map((v) => v / top), duration };
}

function drawWave() {
  const view = $("#card");
  const canvas = view && $(".wave", view);
  if (!canvas || !peaks) return;
  const css = getComputedStyle(document.documentElement);
  const w = (canvas.width = canvas.clientWidth * devicePixelRatio);
  const h = (canvas.height = canvas.clientHeight * devicePixelRatio);
  const g = canvas.getContext("2d");
  g.fillStyle = css.getPropertyValue("--wave");
  const vals = peaks.values;
  for (let i = 0; i < vals.length; i++) {
    const bar = Math.max(1, vals[i] * h * 0.9);
    g.fillRect((i / vals.length) * w, (h - bar) / 2, Math.max(1, w / vals.length - 0.5), bar);
  }
  const x = (t) => (t / peaks.duration) * w;
  g.fillStyle = css.getPropertyValue("--muted");
  for (let t = 0; t < peaks.duration; t += 10) g.fillRect(x(t), h - 6 * devicePixelRatio, devicePixelRatio, 6 * devicePixelRatio);
  for (const [k, color] of [["t0", "--amber"], ["t_ask", "--red"]]) {
    if (marks[k] == null) continue;
    g.fillStyle = css.getPropertyValue(color);
    g.fillRect(x(marks[k]) - devicePixelRatio, 0, 2 * devicePixelRatio, h);
  }
  const audio = $(".label-audio", view);
  g.fillStyle = css.getPropertyValue("--ink");
  g.fillRect(x(audio.currentTime) - devicePixelRatio / 2, 0, devicePixelRatio, h);
}

function renderMarks() {
  const view = $("#card");
  const box = $(".marks", view);
  if (!current.is_scam) { box.replaceChildren(); return; }
  box.replaceChildren(...[["t0", "t0", "first scam move"], ["t_ask", "ask", "first ask"]].map(([k, cls, what]) => {
    const row = document.createElement("div");
    row.className = `mark ${cls}`;
    row.innerHTML = `<b></b><span class="at"></span><button data-do="here">Mark here</button>
      <button data-do="-">−0.5 s</button><button data-do="+">+0.5 s</button><button data-do="go">Play from it</button>
      <button data-do="clear">Clear</button>`;
    $("b", row).textContent = cls === "t0" ? "t0" : "Ask";
    $(".at", row).textContent = marks[k] == null ? `– (${what})` : fmt(marks[k]);
    row.addEventListener("click", (e) => {
      const act = e.target.dataset.do;
      if (act) mark(k, act);
    });
    return row;
  }));
}

function mark(k, act) {
  const audio = $(".label-audio", $("#card"));
  if (act === "here") marks[k] = half(audio.currentTime);
  else if (act === "-" && marks[k] != null) marks[k] = half(marks[k] - 0.5);
  else if (act === "+" && marks[k] != null) marks[k] = half(marks[k] + 0.5);
  else if (act === "clear") marks[k] = null;
  else if (act === "go" && marks[k] != null) { audio.currentTime = marks[k]; audio.play(); }
  $(".label-status", $("#card")).textContent = "Not saved yet.";
  renderMarks();
  drawWave();
}

async function saveLabel() {
  const view = $("#card");
  const status = $(".label-status", view);
  status.classList.remove("err");
  const labeller = $(".labeller", view).value.trim();
  store.set("labeller", labeller);
  if (current.is_scam && marks.t0 == null) {
    status.textContent = "Mark t0 first: a scam call always has one.";
    status.classList.add("err");
    return;
  }
  try {
    const r = await fetch(`/api/label/${current.id}`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ t0: marks.t0, t_ask: marks.t_ask, labeller, notes: $(".notes", view).value }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || r.statusText);
    current.label = body;
    status.textContent = `Saved ${body.labelled_at}.`;
    renderList();
  } catch (e) {
    status.textContent = e.message;
    status.classList.add("err");
  }
}

document.addEventListener("keydown", (e) => {
  if (solo && recorder && e.key === " " && !e.target.closest("input, textarea")) {
    e.preventDefault();
    soloNext($("#card"));
    return;
  }
  if (e.target.closest("input, textarea") || !current || !current.recorded) return;
  const audio = $(".label-audio", $("#card"));
  if (!audio) return;
  if (e.key === " ") { e.preventDefault(); audio.paused ? audio.play() : audio.pause(); }
  else if (e.key === "ArrowLeft") { audio.currentTime = Math.max(0, audio.currentTime - 0.5); }
  else if (e.key === "ArrowRight") { audio.currentTime += 0.5; }
  else if (current.is_scam && (e.key === "t" || e.key === "T")) mark("t0", "here");
  else if (current.is_scam && (e.key === "a" || e.key === "A")) mark("t_ask", "here");
});

window.addEventListener("beforeunload", (e) => { if (recorder || take) e.preventDefault(); });

load();
