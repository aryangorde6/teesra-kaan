// The listener page. Plays a demo call from the server and shows what the Listener hears and decides.

const UI = {
  en: {
    tagline: "The third ear on a scam call",
    start: "Start listening",
    stop: "Stop listening",
    live_soon: "The live microphone connects with the speech API.",
    live_on: "Put the call on speaker, then tap Start.",
    demo: "Play a demo call",
    transcript: "What the caller is saying",
    signals: "Warning signs",
    report: "Report for 1930",
    copy: "Copy",
    copied: "Copied",
    download: "Download",
    call1930: "Call 1930",
    caller_said: "The caller said:",
    caller: "Caller",
    you: "You",
    listening: "Listening",
    ended: "Call ended",
    note: "Demo calls are acted from scripts; they are not real. Nothing is recorded or stored.",
    t0: "First scam move",
    warn: "Warning",
    red: "Danger",
    ask: "Caller asked",
    lead: (a, b) => `Warned ${a} s after the first scam move` + (b === null ? "." : `, ${b} s before the caller asked.`),
  },
  hi: {
    tagline: "स्कैम कॉल पर तीसरा कान",
    start: "सुनना शुरू करें",
    stop: "सुनना बंद करें",
    live_soon: "लाइव माइक स्पीच API जुड़ने पर चालू होगा।",
    live_on: "कॉल को स्पीकर पर रखें, फिर शुरू करें दबाएँ।",
    demo: "डेमो कॉल चलाएँ",
    transcript: "कॉल करने वाला क्या कह रहा है",
    signals: "चेतावनी के संकेत",
    report: "1930 के लिए रिपोर्ट",
    copy: "कॉपी करें",
    copied: "कॉपी हो गया",
    download: "डाउनलोड करें",
    call1930: "1930 पर कॉल करें",
    caller_said: "कॉल करने वाले ने कहा:",
    caller: "कॉल करने वाला",
    you: "आप",
    listening: "सुन रहा है",
    ended: "कॉल खत्म",
    note: "डेमो कॉल अभिनय करके बनाए गए हैं, असली नहीं। कुछ भी रिकॉर्ड या सेव नहीं होता।",
    t0: "पहली चाल",
    warn: "चेतावनी",
    red: "ख़तरा",
    ask: "माँग",
    lead: (a, b) => `पहली चाल के ${a} सेकंड बाद चेतावनी` + (b === null ? "।" : `, माँगने से ${b} सेकंड पहले।`),
  },
  mr: {
    tagline: "फसवणुकीच्या कॉलवर तिसरा कान",
    start: "ऐकायला सुरुवात करा",
    stop: "ऐकणे थांबवा",
    live_soon: "स्पीच API जोडल्यावर लाइव्ह माइक सुरू होईल.",
    live_on: "कॉल स्पीकरवर ठेवा, मग सुरू करा दाबा.",
    demo: "डेमो कॉल चालवा",
    transcript: "फोन करणारा काय बोलतोय",
    signals: "धोक्याची चिन्हे",
    report: "1930 साठी अहवाल",
    copy: "कॉपी करा",
    copied: "कॉपी झाले",
    download: "डाउनलोड करा",
    call1930: "1930 वर कॉल करा",
    caller_said: "फोन करणाऱ्याने सांगितले:",
    caller: "फोन करणारा",
    you: "तुम्ही",
    listening: "ऐकत आहे",
    ended: "कॉल संपला",
    note: "डेमो कॉल अभिनय करून बनवले आहेत, खरे नाहीत. काहीही रेकॉर्ड किंवा सेव्ह होत नाही.",
    t0: "पहिली चाल",
    warn: "इशारा",
    red: "धोका",
    ask: "मागणी",
    lead: (a, b) => `पहिल्या चालीनंतर ${a} सेकंदांत इशारा` + (b === null ? "." : `, मागणीच्या ${b} सेकंद आधी.`),
  },
};
const SPEECH_LANG = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };
const ASKS = new Set(["A5", "A6", "A7", "A11"]);
const $ = (sel) => document.querySelector(sel);

// Turns the microphone into 16 kHz 16-bit mono PCM, 100 ms per message.
const WORKLET = `
class Pcm16 extends AudioWorkletProcessor {
  constructor() { super(); this.ratio = sampleRate / 16000; this.pos = 0; this.buf = []; }
  process(inputs) {
    const ch = inputs[0][0];
    if (!ch) return true;
    for (; this.pos < ch.length; this.pos += this.ratio) {
      const i = Math.floor(this.pos), f = this.pos - i;
      const a = ch[i], b = i + 1 < ch.length ? ch[i + 1] : a;
      const v = Math.max(-1, Math.min(1, a + (b - a) * f));
      this.buf.push(v < 0 ? v * 0x8000 : v * 0x7fff);
    }
    this.pos -= ch.length;
    while (this.buf.length >= 1600) {
      const out = new Int16Array(this.buf.splice(0, 1600));
      this.port.postMessage(out.buffer, [out.buffer]);
    }
    return true;
  }
}
registerProcessor("pcm16", Pcm16);`;

let lang = "hi";
try { lang = localStorage.getItem("tk-lang") || lang; } catch (e) {}
let socket = null;
let state = null;
let mic = null;
let liveAvailable = false;

function t(key) { return UI[lang][key]; }

function setLang(next) {
  lang = next;
  try { localStorage.setItem("tk-lang", next); } catch (e) {}
  document.documentElement.lang = next;
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.lang === next)));
  document.querySelectorAll("[data-t]").forEach((el) => {
    const value = UI[next][el.dataset.t];
    if (typeof value === "string") el.textContent = value;
  });
}

function clock(s) {
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

function reset() {
  $("#transcript").innerHTML = "";
  $("#signals").innerHTML = "";
  $("#alert").hidden = true;
  $("#alert").className = "alert";
  $("#timeline-wrap").hidden = true;
  $("#report-wrap").hidden = true;
  $("#report").textContent = "";
  $("#partial").textContent = "";
  $("#partial").hidden = true;
  document.querySelectorAll(".timeline .mark").forEach((m) => m.remove());
  $("#legend").innerHTML = "";
  $("#lead").textContent = "";
  state = { call: null, line: null, speaker: null, started: 0, timer: null, report: "" };
}

function addWord(e) {
  if (state.speaker !== e.speaker) {
    const p = document.createElement("p");
    p.className = `line ${e.speaker}`;
    p.innerHTML = `<span class="who">${clock(e.t)} · ${e.speaker === "caller" ? t("caller") : t("you")}</span><span class="text"></span>`;
    $("#transcript").appendChild(p);
    state.line = p.querySelector(".text");
    state.speaker = e.speaker;
  }
  state.line.textContent += (state.line.textContent ? " " : "") + e.word;
  const box = $("#transcript");
  box.scrollTop = box.scrollHeight;
}

function addSignal(e) {
  const li = document.createElement("li");
  if (ASKS.has(e.id)) li.className = "ask";
  li.innerHTML = `<span class="name"></span><span class="when">${clock(e.said_at)}</span><span class="quote"></span>`;
  li.querySelector(".name").textContent = e.name;
  li.querySelector(".quote").textContent = `“${e.quote}”`;
  $("#signals").prepend(li);
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  // Placeholder until the recorded warning lines exist: the browser's own voice.
  const u = new SpeechSynthesisUtterance(text);
  u.lang = SPEECH_LANG[lang];
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function showAlarm(e) {
  const w = e.warning;
  const box = $("#alert");
  box.hidden = false;
  box.className = `alert ${w.level}`;
  box.querySelector(".alert-head").textContent = w.headline;
  box.querySelector(".alert-action").textContent = w.action;
  const quotes = box.querySelector(".alert-quotes ul");
  quotes.innerHTML = "";
  // One line per quote: drop a quote that's part of a longer one.
  const all = [...new Set(w.signals.map((s) => s.quote).filter(Boolean))];
  all.filter((q) => !all.some((other) => other !== q && other.includes(q))).forEach((q) => {
    const li = document.createElement("li");
    li.textContent = `“${q}”`;
    quotes.appendChild(li);
  });
  const facts = box.querySelector(".facts");
  facts.innerHTML = "";
  w.facts.forEach((f) => {
    const li = document.createElement("li");
    li.textContent = f;
    facts.appendChild(li);
  });
  box.scrollIntoView({ behavior: "smooth", block: "start" });
  if (navigator.vibrate) navigator.vibrate(w.level === "red" ? [300, 120, 300] : 200);
  speak(`${w.headline}. ${w.action}`);
}

function mark(at, color, label) {
  if (at === null || at === undefined || !state.call) return;
  const m = document.createElement("div");
  m.className = "mark";
  m.style.left = `${Math.min(100, (at / state.call.duration) * 100)}%`;
  m.style.background = color;
  m.title = `${label} ${clock(at)}`;
  $("#timeline").appendChild(m);
  const li = document.createElement("li");
  li.innerHTML = `<i style="background:${color}"></i>${label} ${clock(at)}`;
  $("#legend").appendChild(li);
}

function finish(e) {
  clearInterval(state.timer);
  $("#status").className = "status";
  $("#status").textContent = t("ended");
  $("#progress").style.width = "100%";
  const css = getComputedStyle(document.documentElement);
  const tm = e.timing;
  mark(tm.t0, css.getPropertyValue("--muted"), t("t0"));
  if (tm.t_warn !== null && tm.t_warn !== tm.t_red) mark(tm.t_warn, css.getPropertyValue("--amber"), t("warn"));
  mark(tm.t_red, css.getPropertyValue("--red"), t("red"));
  mark(tm.t_ask, css.getPropertyValue("--ink"), t("ask"));
  if (tm.t_warn !== null && tm.t0 !== null && tm.t0 !== undefined) {
    const a = Math.round(tm.t_warn - tm.t0);
    const b = tm.t_ask === null || tm.t_ask === undefined ? null : Math.round(tm.t_ask - tm.t_warn);
    $("#lead").textContent = t("lead")(a, b);
  }
  state.report = e.report_markdown;
  $("#report").textContent = e.report_markdown;
  $("#report-wrap").hidden = false;
}

function showPartial(e) {
  const p = $("#partial");
  p.textContent = e.text;
  p.hidden = !e.text;
}

const proto = location.protocol === "https:" ? "wss" : "ws";

function play() {
  stopMic();
  if (socket) socket.close();
  reset();
  const id = $("#call").value;
  const speed = new URLSearchParams(location.search).get("speed") || "1";
  socket = new WebSocket(`${proto}://${location.host}/ws/demo?call=${encodeURIComponent(id)}&lang=${lang}&speed=${speed}`);
  socket.onmessage = (msg) => handle(JSON.parse(msg.data), Number(speed));
}

async function listen() {
  if (mic) {
    if (socket && socket.readyState === 1) socket.send(JSON.stringify({ type: "stop" }));
    stopMic();
    return;
  }
  if (socket) socket.close();
  reset();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: true, autoGainControl: true },
    });
    const ctx = new AudioContext();
    await ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" })));
    const node = new AudioWorkletNode(ctx, "pcm16");
    const mute = ctx.createGain();
    mute.gain.value = 0;
    ctx.createMediaStreamSource(stream).connect(node).connect(mute).connect(ctx.destination);
    socket = new WebSocket(`${proto}://${location.host}/ws/live?lang=${lang}`);
    socket.binaryType = "arraybuffer";
    node.port.onmessage = (m) => { if (socket.readyState === 1) socket.send(m.data); };
    socket.onmessage = (msg) => handle(JSON.parse(msg.data), 1);
    socket.onclose = stopMic;
    mic = { stream, ctx };
    $("#live [data-t]").textContent = t("stop");
  } catch (err) {
    $("#status").textContent = String(err.message || err);
    stopMic();
  }
}

function stopMic() {
  if (!mic) return;
  mic.stream.getTracks().forEach((track) => track.stop());
  mic.ctx.close();
  mic = null;
  $("#live [data-t]").textContent = t("start");
}

function handle(e, speed) {
    if (e.type === "start") {
      state.call = e.call;
      state.started = performance.now();
      $("#status").className = "status on";
      $("#timeline-wrap").hidden = false;
      state.timer = setInterval(() => {
        const s = ((performance.now() - state.started) / 1000) * speed;
        $("#status").textContent = `${t("listening")} ${clock(s)}`;
        $("#progress").style.width = `${Math.min(100, (s / state.call.duration) * 100)}%`;
      }, 250);
    } else if (e.type === "word") addWord(e);
    else if (e.type === "partial") showPartial(e);
    else if (e.type === "signal") addSignal(e);
    else if (e.type === "alarm") showAlarm(e);
    else if (e.type === "end") finish(e);
    else if (e.type === "error") $("#status").textContent = e.message;
}

async function init() {
  setLang(lang);
  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
  const calls = await fetch("/api/calls").then((r) => r.json());
  const select = $("#call");
  calls.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.id;
    o.textContent = `${c.id.replace(/^demo-/, "")} · ${c.language} · ${clock(c.duration)}`;
    select.appendChild(o);
  });
  $("#play").addEventListener("click", play);
  $("#live").addEventListener("click", listen);
  try {
    liveAvailable = (await fetch("/api/status").then((r) => r.json())).live;
  } catch (e) {}
  $("#live").disabled = !liveAvailable;
  const hint = document.querySelector(".hint");
  hint.dataset.t = liveAvailable ? "live_on" : "live_soon";
  hint.textContent = t(hint.dataset.t);
  $("#copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(state.report);
      $("#copy").textContent = t("copied");
      setTimeout(() => ($("#copy").textContent = t("copy")), 1500);
    } catch (e) {}
  });
  $("#download").addEventListener("click", () => {
    const blob = new Blob([state.report], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `teesra-kaan-report-${state.call ? state.call.id : "call"}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
  reset();
}

init();
