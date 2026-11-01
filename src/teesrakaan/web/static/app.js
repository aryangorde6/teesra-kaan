// The listener page. Plays a demo call from the server and shows what the Listener hears and decides.

const UI = {
  en: {
    tagline: "The third ear on a scam call",
    start: "Start listening",
    stop: "Stop listening",
    hero: "Teesra Kaan listens to a call on speaker. It warns you in the caller's own words, and shows his next line before he says it.",
    watch: "Watch a scam call",
    watch_hint: "A \"digital arrest\" call, acted from a script. Watch for the caller's next line.",
    live_off: "Live listening is off on this public page: it uses paid speech and model APIs. The demo calls replay Muse Spark's real answers.",
    back: "← Back",
    typed: "Checked what you typed",
    waiting: "Listening for warning signs. Nothing suspicious yet.",
    calm_end: "Call ended. No warning: this call didn't look like a scam.",
    calm_signs: (n) => `It heard ${n} warning sign${n === 1 ? "" : "s"}, but the call as a whole didn't look like a scam, so it stayed quiet.`,
    live_on: "Open this page on a second phone or laptop: the phone on the call keeps its own microphone. Put the call on speaker next to it, then tap Start.",
    standin: "Checked by keywords only: this public page doesn't call the paid model API, so Muse Spark doesn't read what you type. Keywords miss calls worded without them. \"Try an example\" shows Muse Spark's real answer.",
    silent: "Hearing nothing. If the call is on this phone, open this page on another phone or laptop.",
    demo: "Play a demo call",
    upload: "Check a call you recorded",
    checking: "Checking the recording…",
    check_head: "Got a call like this? Check before you pay",
    check_hint: "Type what the caller said, or tap your keyboard's microphone and say it. Works on this phone, after the call.",
    check_ph: "e.g. He said he's from the CBI, there's an FIR on my Aadhaar, and I mustn't tell anyone…",
    check: "Check",
    checking_text: "Checking…",
    example: "Try an example",
    example_text: "He said he is calling from Mumbai Police. My Aadhaar was found in a money laundering case. He put me on a video call and said do not tell anyone.",
    family: "Tell family now",
    transcript: "What the caller is saying",
    signals: "Warning signs",
    report: "Report for 1930",
    report_us: "Report for ReportFraud.ftc.gov",
    copy: "Copy",
    copied: "Copied",
    download: "Download",
    call1930: "Call 1930",
    call_us: "Report at ReportFraud.ftc.gov",
    where: "Where you are",
    country_in: "India · 1930",
    country_us: "USA · ReportFraud.ftc.gov",
    caller_said: "The caller said:",
    caller: "Caller",
    you: "You",
    listening: "Listening",
    ended: "Call ended",
    note: "Demo calls are acted from scripts; they are not real. Nothing is recorded or stored.",
    synthetic: "You're hearing synthetic voices, not real people.",
    how: "How it decides",
    how_1: "Muse Voice Transcribe writes down the call as it happens and keeps the two voices apart. After each thing the caller says, Muse Spark answers these questions about the caller, and must quote the caller's exact words for every \"yes\". A quote the caller never said is thrown away.",
    how_2: "Fixed rules raise the alarm, never the model on its own: Muse Spark must judge the call a scam, and at least one warning sign must be shown in the caller's own words. If one of them is a request for money, an OTP or PIN, an app or a link, it turns red.",
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
    hero: "तीसरा कान स्पीकर पर चल रहा कॉल सुनता है। यह कॉल करने वाले के अपने शब्दों में चेतावनी देता है, और उसकी अगली बात उसके बोलने से पहले दिखाता है।",
    watch: "एक स्कैम कॉल देखें",
    watch_hint: "स्क्रिप्ट से अभिनय किया गया \"डिजिटल अरेस्ट\" कॉल। कॉल करने वाले की अगली बात पर नज़र रखें।",
    live_off: "इस सार्वजनिक पेज पर लाइव सुनना बंद है: इसमें पेड स्पीच और मॉडल API लगते हैं। डेमो कॉल Muse Spark के असली जवाब दोबारा चलाते हैं।",
    back: "← वापस",
    typed: "आपने जो लिखा, उसकी जाँच",
    waiting: "चेतावनी के संकेत सुन रहा है। अभी तक कुछ संदिग्ध नहीं।",
    calm_end: "कॉल खत्म। कोई चेतावनी नहीं: यह कॉल स्कैम नहीं लगा।",
    calm_signs: (n) => `${n} चेतावनी के संकेत सुने, पर पूरा कॉल स्कैम नहीं लगा, इसलिए चुप रहा।`,
    live_on: "यह पेज किसी दूसरे फ़ोन या लैपटॉप पर खोलें: जिस फ़ोन पर कॉल चल रहा है, वह अपना माइक नहीं देता। कॉल को स्पीकर पर इसके पास रखें, फिर शुरू करें दबाएँ।",
    standin: "सिर्फ़ कीवर्ड से जाँचा गया: यह सार्वजनिक पेज पेड मॉडल API नहीं चलाता, इसलिए आपका लिखा Muse Spark नहीं पढ़ता। जिन कॉल में ये शब्द नहीं होते, वे कीवर्ड से छूट जाती हैं। \"उदाहरण देखें\" Muse Spark का असली जवाब दिखाता है।",
    silent: "कुछ सुनाई नहीं दे रहा। अगर कॉल इसी फ़ोन पर है, तो यह पेज किसी दूसरे फ़ोन या लैपटॉप पर खोलें।",
    demo: "डेमो कॉल चलाएँ",
    upload: "रिकॉर्ड किया हुआ कॉल जाँचें",
    checking: "रिकॉर्डिंग जाँची जा रही है…",
    check_head: "ऐसा कॉल आया? पैसे देने से पहले जाँचें",
    check_hint: "कॉल करने वाले ने जो कहा, वह लिखें, या कीबोर्ड का माइक दबाकर बोलें। कॉल के बाद इसी फ़ोन पर चलता है।",
    check_ph: "जैसे: उसने कहा वह CBI से है, मेरे आधार पर FIR है, और किसी को नहीं बताना है…",
    check: "जाँचें",
    checking_text: "जाँच हो रही है…",
    example: "उदाहरण देखें",
    example_text: "उसने कहा वह मुंबई पुलिस से बोल रहा है। मेरा आधार मनी लॉन्ड्रिंग केस में मिला है। उसने वीडियो कॉल पर आने को कहा और बोला किसी को मत बताना।",
    family: "परिवार को अभी बताएँ",
    transcript: "कॉल करने वाला क्या कह रहा है",
    signals: "चेतावनी के संकेत",
    report: "1930 के लिए रिपोर्ट",
    report_us: "ReportFraud.ftc.gov के लिए रिपोर्ट",
    copy: "कॉपी करें",
    copied: "कॉपी हो गया",
    download: "डाउनलोड करें",
    call1930: "1930 पर कॉल करें",
    call_us: "ReportFraud.ftc.gov पर शिकायत करें",
    where: "आप कहाँ हैं",
    country_in: "भारत · 1930",
    country_us: "अमेरिका · ReportFraud.ftc.gov",
    caller_said: "कॉल करने वाले ने कहा:",
    caller: "कॉल करने वाला",
    you: "आप",
    listening: "सुन रहा है",
    ended: "कॉल खत्म",
    note: "डेमो कॉल अभिनय करके बनाए गए हैं, असली नहीं। कुछ भी रिकॉर्ड या सेव नहीं होता।",
    synthetic: "आप सिंथेटिक आवाज़ें सुन रहे हैं, असली लोग नहीं।",
    how: "यह कैसे तय करता है",
    how_1: "Muse Voice Transcribe कॉल को साथ-साथ लिखता है और दोनों आवाज़ें अलग रखता है। कॉल करने वाले की हर बात के बाद Muse Spark उसके बारे में ये सवाल हाँ/ना में बताता है, और हर \"हाँ\" के लिए उसके असली शब्द दिखाने होते हैं। जो शब्द कॉल करने वाले ने कहे ही नहीं, वे हटा दिए जाते हैं।",
    how_2: "चेतावनी तय नियम देते हैं, मॉडल अकेले कभी नहीं: Muse Spark को कॉल स्कैम लगना चाहिए, और कम से कम एक संकेत कॉल करने वाले के अपने शब्दों में दिखना चाहिए। अगर उनमें से एक पैसे, OTP या PIN, ऐप या लिंक की माँग हो तो लाल।",
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
    hero: "तिसरा कान स्पीकरवरचा कॉल ऐकतो. तो फोन करणाऱ्याच्या स्वतःच्या शब्दांत इशारा देतो, आणि त्याचं पुढचं वाक्य तो बोलण्याआधीच दाखवतो.",
    watch: "एक फसवणुकीचा कॉल पाहा",
    watch_hint: "स्क्रिप्टवरून अभिनय केलेला \"डिजिटल अरेस्ट\" कॉल. फोन करणाऱ्याच्या पुढच्या वाक्याकडे लक्ष ठेवा.",
    live_off: "या सार्वजनिक पेजवर लाइव्ह ऐकणे बंद आहे: त्यासाठी सशुल्क स्पीच आणि मॉडेल API लागतात. डेमो कॉल Muse Spark ची खरी उत्तरे पुन्हा चालवतात.",
    back: "← मागे",
    typed: "तुम्ही लिहिलेल्याची तपासणी",
    waiting: "धोक्याची चिन्हे ऐकत आहे. अजून काही संशयास्पद नाही.",
    calm_end: "कॉल संपला. इशारा नाही: हा कॉल फसवणुकीचा वाटला नाही.",
    calm_signs: (n) => `${n} धोक्याची चिन्हे ऐकली, पण पूर्ण कॉल फसवणुकीचा वाटला नाही, म्हणून तो शांत राहिला.`,
    live_on: "हे पेज दुसऱ्या फोनवर किंवा लॅपटॉपवर उघडा: ज्या फोनवर कॉल चालू आहे तो आपला माइक देत नाही. कॉल स्पीकरवर याच्या जवळ ठेवा, मग सुरू करा दाबा.",
    standin: "फक्त कीवर्डने तपासले: हे सार्वजनिक पेज सशुल्क मॉडेल API चालवत नाही, त्यामुळे तुम्ही लिहिलेले Muse Spark वाचत नाही. ज्या कॉलमध्ये हे शब्द नसतात, त्या कीवर्डमधून सुटतात. \"उदाहरण पाहा\" Muse Spark चे खरे उत्तर दाखवते.",
    silent: "काहीच ऐकू येत नाही. कॉल याच फोनवर असेल, तर हे पेज दुसऱ्या फोनवर किंवा लॅपटॉपवर उघडा.",
    demo: "डेमो कॉल चालवा",
    upload: "रेकॉर्ड केलेला कॉल तपासा",
    checking: "रेकॉर्डिंग तपासत आहे…",
    check_head: "असा कॉल आला? पैसे देण्याआधी तपासा",
    check_hint: "फोन करणाऱ्याने जे सांगितले ते लिहा, किंवा कीबोर्डचा माइक दाबून बोला. कॉलनंतर याच फोनवर चालते.",
    check_ph: "उदा. तो म्हणाला तो CBI मधून आहे, माझ्या आधारवर FIR आहे, आणि कोणालाही सांगायचं नाही…",
    check: "तपासा",
    checking_text: "तपासत आहे…",
    example: "उदाहरण पाहा",
    example_text: "तो म्हणाला तो मुंबई पोलिसांकडून बोलतोय. माझं आधार मनी लाँडरिंग केसमध्ये सापडलं आहे. त्याने व्हिडिओ कॉलवर यायला सांगितलं आणि म्हणाला कोणालाही सांगू नका.",
    family: "घरच्यांना आत्ता सांगा",
    transcript: "फोन करणारा काय बोलतोय",
    signals: "धोक्याची चिन्हे",
    report: "1930 साठी अहवाल",
    report_us: "ReportFraud.ftc.gov साठी अहवाल",
    copy: "कॉपी करा",
    copied: "कॉपी झाले",
    download: "डाउनलोड करा",
    call1930: "1930 वर कॉल करा",
    call_us: "ReportFraud.ftc.gov वर तक्रार करा",
    where: "तुम्ही कुठे आहात",
    country_in: "भारत · 1930",
    country_us: "अमेरिका · ReportFraud.ftc.gov",
    caller_said: "फोन करणाऱ्याने सांगितले:",
    caller: "फोन करणारा",
    you: "तुम्ही",
    listening: "ऐकत आहे",
    ended: "कॉल संपला",
    note: "डेमो कॉल अभिनय करून बनवले आहेत, खरे नाहीत. काहीही रेकॉर्ड किंवा सेव्ह होत नाही.",
    synthetic: "तुम्ही सिंथेटिक आवाज ऐकत आहात, खरी माणसे नाहीत.",
    how: "हे कसे ठरवते",
    how_1: "Muse Voice Transcribe कॉल चालू असतानाच लिहून काढतो आणि दोन्ही आवाज वेगळे ठेवतो. फोन करणाऱ्याच्या प्रत्येक बोलण्यानंतर Muse Spark त्याच्याबद्दल हे प्रश्न हो/नाही मध्ये सांगतो, आणि प्रत्येक \"हो\" साठी त्याचे नेमके शब्द दाखवावे लागतात. फोन करणाऱ्याने न बोललेले शब्द काढून टाकले जातात.",
    how_2: "इशारा ठरलेले नियम देतात, मॉडेल एकटे कधीच नाही: Muse Spark ला कॉल फसवणुकीचा वाटला पाहिजे, आणि किमान एक चिन्ह फोन करणाऱ्याच्या स्वतःच्या शब्दांत दिसले पाहिजे. त्यातले एक पैसे, OTP किंवा PIN, अ‍ॅप किंवा लिंकची मागणी असेल तर लाल.",
    t0: "पहिली चाल",
    warn: "इशारा",
    red: "धोका",
    ask: "मागणी",
    lead: (a, b) => `पहिल्या चालीनंतर ${a} सेकंदांत इशारा` + (b === null ? "." : `, मागणीच्या ${b} सेकंद आधी.`),
  },
};
const SPEECH_LANG = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };
// The demo calls' names in the menu, and what they're spoken in. A call not listed (a recorded re-enactment) shows its id.
const CALL_NAME = {
  "demo-digital-arrest": { en: "Digital arrest", hi: "डिजिटल अरेस्ट", mr: "डिजिटल अरेस्ट" },
  "demo-trai-marathi": { en: "Your number will be cut off (TRAI)", hi: "आपका नंबर बंद होगा (TRAI)", mr: "तुमचा नंबर बंद होईल (TRAI)" },
  "demo-bank-alert-genuine": { en: "A genuine bank alert", hi: "असली बैंक अलर्ट", mr: "खरा बँक अलर्ट" },
  "demo-wrong-credit": { en: "Sent too much by mistake", hi: "गलती से ज़्यादा पैसे भेजे", mr: "चुकून जास्त पैसे पाठवले" },
  // The English calls are voiced (synthetic voices, said on screen while they play), for viewers who don't speak Hindi.
  "demo-digital-arrest-en": { en: "Digital arrest, voiced", hi: "डिजिटल अरेस्ट, आवाज़ के साथ", mr: "डिजिटल अरेस्ट, आवाजासह" },
  "demo-wrong-credit-en": { en: "Sent too much by mistake, voiced", hi: "गलती से ज़्यादा पैसे भेजे, आवाज़ के साथ", mr: "चुकून जास्त पैसे पाठवले, आवाजासह" },
};
const CALL_LANG = {
  "hi+en": { en: "Hindi and English", hi: "हिंदी और अंग्रेज़ी", mr: "हिंदी आणि इंग्रजी" },
  hi: { en: "Hindi", hi: "हिंदी", mr: "हिंदी" },
  mr: { en: "Marathi", hi: "मराठी", mr: "मराठी" },
  en: { en: "English", hi: "अंग्रेज़ी", mr: "इंग्रजी" },
};
let demoCalls = [];
// The hero plays the digital-arrest call, the one where the next line comes true: voiced in English when the page is.
function hero() {
  const find = (id) => demoCalls.find((c) => c.id === id);
  return (lang === "en" && find("demo-digital-arrest-en")) || find("demo-digital-arrest") || demoCalls[0];
}
function labelCalls() {
  document.querySelectorAll("#call option").forEach((o) => {
    const c = demoCalls.find((x) => x.id === o.value);
    const name = (CALL_NAME[c.id] || {})[lang] || c.id.replace(/^demo-/, "");
    const spoken = (CALL_LANG[c.language] || {})[lang] || c.language;
    o.textContent = `${name} · ${spoken} · ${clock(c.duration)}`;
  });
  const h = hero();
  if (h) $("#watch-len").textContent = clock(h.duration);
}
// Where the warning and the report send you. It starts on India everywhere: the demo calls are Indian calls, and a judge
// abroad should see what the person on them would (1930, not the FTC). "Where you are" switches it, and is remembered.
const HELPLINE = {
  IN: { href: "tel:1930", text: "call1930", report: "report" },
  US: { href: "https://reportfraud.ftc.gov/", text: "call_us", report: "report_us" },
};
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

let zone = "";
try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
// Hindi in India, who the page is for; elsewhere (a judge abroad, say) English, unless the browser asks for Hindi or Marathi.
let lang = /^Asia\/(Kolkata|Calcutta)$/.test(zone) ? "hi" : "en";
try { lang = navigator.languages.map((l) => l.slice(0, 2).toLowerCase()).find((l) => l === "hi" || l === "mr") || lang; } catch (e) {}
try { lang = localStorage.getItem("tk-lang") || lang; } catch (e) {}
let country = "IN";
try { country = localStorage.getItem("tk-country") || country; } catch (e) {}
if (!HELPLINE[country]) country = "IN";
let socket = null;
let state = null;
let mic = null;
let player = null;
let liveAvailable = false;
let voiceLines = {}; // recorded warning line → its version (/api/voice)
const voice = new Audio();

function t(key) { return UI[lang][key]; }

let questions = [];

function renderQuestions() {
  const ol = $("#questions");
  ol.innerHTML = "";
  questions.forEach((q) => {
    const li = document.createElement("li");
    if (q.kind === "ask") li.className = "ask";
    li.innerHTML = `<span class="n"></span><span class="q"></span>`;
    li.querySelector(".n").textContent = q.name[lang];
    li.querySelector(".q").textContent = q.question;
    ol.appendChild(li);
  });
}

function setLang(next) {
  lang = next;
  try { localStorage.setItem("tk-lang", next); } catch (e) {}
  document.documentElement.lang = next;
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.lang === next)));
  document.querySelectorAll("[data-t]").forEach((el) => {
    const value = UI[next][el.dataset.t];
    if (typeof value === "string") el.textContent = value;
  });
  document.querySelectorAll("[data-tp]").forEach((el) => { el.placeholder = UI[next][el.dataset.tp]; });
  renderQuestions();
  labelCalls();
}

function setCountry(next) {
  country = next;
  try { localStorage.setItem("tk-country", next); } catch (e) {}
  $("#country").value = next;
  const h = HELPLINE[next];
  const link = $("#helpline");
  link.href = h.href;
  link.dataset.t = h.text;
  if (next === "US") { link.target = "_blank"; link.rel = "noopener"; } else { link.removeAttribute("target"); }
  $("#report-head").dataset.t = h.report;
  setLang(lang);
}

function clock(s) {
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

function reset() {
  if (state) { clearInterval(state.timer); state.pending.forEach(clearTimeout); }
  voice.pause();
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  $("#transcript").innerHTML = "";
  $("#voiced").hidden = true;
  $("#signals").innerHTML = "";
  $("#alert").hidden = true;
  $("#alert").className = "alert";
  $("#next").hidden = true;
  $("#next-now").hidden = true;
  $("#next .came-true").innerHTML = "";
  $("#ahead").hidden = true;
  $("#family").hidden = true;
  $("#timeline-wrap").hidden = true;
  $("#report-wrap").hidden = true;
  $("#standin").hidden = true;
  $("#report").textContent = "";
  $("#partial").textContent = "";
  $("#partial").hidden = true;
  document.querySelectorAll(".timeline .mark").forEach((m) => m.remove());
  $("#legend").innerHTML = "";
  $("#lead").textContent = "";
  $("#engine").textContent = "";
  $("#status").className = "status";
  $("#status").textContent = "";
  $("#waiting").className = "waiting";
  $("#waiting .waiting-text").dataset.t = "waiting";
  $("#waiting .waiting-text").textContent = t("waiting");
  $("#waiting .waiting-why").textContent = "";
  state = { call: null, line: null, speaker: null, started: 0, timer: null, pending: [], report: "" };
  updateWaiting();
}

// The call screen: everything else steps aside, so the warning and the next line are what's on screen.
function enterCall(kind) {
  document.body.classList.add("in-call");
  document.body.classList.toggle("typed", kind === "typed");
  setBack(kind === "live" ? "stop" : "back");
  window.scrollTo(0, 0);
}

function goHome() {
  if (mic && socket && socket.readyState === 1) socket.send(JSON.stringify({ type: "stop" }));
  stopMic();
  if (player) { player.pause(); player = null; }
  if (socket) { socket.close(); socket = null; }
  reset();
  document.body.classList.remove("in-call", "typed");
  window.scrollTo(0, 0);
}

function setBack(key) {
  const b = $("#back");
  b.dataset.t = key;
  b.textContent = (key === "stop" ? "■ " : "") + t(key);
}

// "Listening, nothing yet" until there's a warning or a next line; a call that ends without one says so.
function updateWaiting() {
  $("#waiting").hidden = !($("#alert").hidden && $("#next").hidden && $("#ahead").hidden);
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
  const when = e.said_at === null || e.said_at === undefined ? "" : `<span class="when">${clock(e.said_at)}</span>`;
  li.innerHTML = `<span class="name"></span>${when}<span class="quote"></span>`;
  li.querySelector(".name").textContent = e.name;
  li.querySelector(".quote").textContent = `“${e.quote}”`;
  $("#signals").prepend(li);
}

function showNext(e) {
  // The caller's next line from the scam's script, shown before it's said; hidden while the scripts disagree.
  $("#next-now").hidden = !e.id;
  // With no line to show and none ticked yet, hide the whole card rather than leave it empty.
  $("#next").hidden = !e.id && !$("#next .came-true").children.length;
  if (!e.id) return;
  $("#next .next-label").textContent = e.label;
  $("#next .next-line").textContent = e.line;
}

function cameTrue(e) {
  const li = document.createElement("li");
  li.textContent = e.text;
  const when = document.createElement("span");
  when.className = "when";
  when.textContent = clock(e.said_at);
  li.appendChild(when);
  $("#next").hidden = false;
  $("#next .came-true").prepend(li);
  if (navigator.vibrate) navigator.vibrate(150);
}

// The warning, said aloud: the line recorded in the studio, or the browser's own voice until it's recorded.
function speak(w) {
  const id = w.level === "red" ? `W-red-${country}-${lang}` : `W-amber-${lang}`; // messages.voice_id
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (!voiceLines[id]) { sayInBrowser(w); return; }
  voice.src = `/voice/${id}.m4a?v=${voiceLines[id]}`;
  voice.muted = false;
  if (player) player.volume = 0.3; // the call steps back while the third ear speaks
  voice.play().catch(() => { unduck(); sayInBrowser(w); });
}

function sayInBrowser(w) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(`${w.headline}. ${w.action}`);
  u.lang = lang === "en" && country === "US" ? "en-US" : SPEECH_LANG[lang];
  speechSynthesis.speak(u);
}

function unduck() { if (player) player.volume = 1; }
voice.addEventListener("ended", unduck);
voice.addEventListener("error", unduck);

// Phones let a page play a sound later only from an element first played on a tap: this one, muted, on the first tap.
function primeVoice() {
  const id = Object.keys(voiceLines)[0];
  if (!id || voice.dataset.primed) return;
  voice.dataset.primed = "1";
  voice.muted = true;
  voice.src = `/voice/${id}.m4a?v=${voiceLines[id]}`;
  voice.play().then(() => voice.pause(), () => {}).finally(() => { if (voice.paused) voice.muted = false; });
}
document.addEventListener("click", primeVoice, true);

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
  // One tap to tell family, with the caller's words: WhatsApp in India, a text message in the US.
  const family = $("#family");
  family.hidden = !w.family;
  family.href = country === "US" ? `sms:?&body=${encodeURIComponent(w.family)}` : `https://wa.me/?text=${encodeURIComponent(w.family)}`;
  updateWaiting(); // first, or the "listening" card vanishing above it shifts the warning under the bar mid-scroll
  box.scrollIntoView({ behavior: "smooth", block: "start" });
  if (navigator.vibrate) navigator.vibrate(w.level === "red" ? [300, 120, 300] : 200);
  speak(w);
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
  if (tm.t_warn !== null && tm.t_warn !== tm.t_red) mark(tm.t_warn, css.getPropertyValue("--sun"), t("warn"));
  mark(tm.t_red, css.getPropertyValue("--red"), t("red"));
  mark(tm.t_ask, css.getPropertyValue("--ink"), t("ask"));
  if (tm.t_warn !== null && tm.t0 !== null && tm.t0 !== undefined) {
    const a = Math.round(tm.t_warn - tm.t0);
    const b = tm.t_ask === null || tm.t_ask === undefined ? null : Math.round(tm.t_ask - tm.t_warn);
    $("#lead").textContent = t("lead")(a, b);
  }
  state.report = e.report_text || e.report_markdown;
  $("#report").textContent = state.report;
  $("#report-wrap").hidden = false;
  if ($("#alert").hidden) {
    $("#waiting").className = "waiting calm";
    $("#waiting .waiting-text").dataset.t = "calm_end";
    $("#waiting .waiting-text").textContent = t("calm_end");
    const n = $("#signals").children.length;
    $("#waiting .waiting-why").textContent = n ? t("calm_signs")(n) : "";
  }
}

function showPartial(e) {
  const p = $("#partial");
  p.textContent = e.text;
  p.hidden = !e.text;
}

const proto = location.protocol === "https:" ? "wss" : "ws";

function play() {
  stopMic();
  if (player) { player.pause(); player = null; }
  if (socket) socket.close();
  reset();
  enterCall("call");
  const id = $("#call").value;
  const speed = new URLSearchParams(location.search).get("speed") || "1";
  socket = new WebSocket(`${proto}://${location.host}/ws/demo?call=${encodeURIComponent(id)}&lang=${lang}&country=${country}&speed=${speed}`);
  socket.onmessage = (msg) => handle(JSON.parse(msg.data), Number(speed));
}

async function checkFile(file) {
  stopMic();
  if (socket) socket.close();
  reset();
  enterCall("call");
  $("#status").textContent = t("checking");
  try {
    const r = await fetch(`/api/check?lang=${lang}&country=${country}`, { method: "POST", body: file });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || r.statusText);
    // Replay the result at 4x, so the warning still arrives at the moment it would have.
    data.events.forEach((e) => state.pending.push(setTimeout(() => handle(e, 4), (e.t * 1000) / 4)));
  } catch (err) {
    $("#status").textContent = String(err.message || err);
  }
}

function showAhead(a) {
  // The scam a typed call matches, and the rest of its script, in the caller's words.
  const box = $("#ahead");
  box.hidden = false;
  box.querySelector(".ahead-match").textContent = a.matches;
  box.querySelector(".next-label").textContent = a.label;
  const ol = box.querySelector(".ahead-steps");
  ol.innerHTML = "";
  a.steps.forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s.line;
    ol.appendChild(li);
  });
  box.querySelector(".ahead-note").textContent = a.note;
}

async function checkSaid() {
  const text = $("#said").value.trim();
  if (!text) { $("#said").focus(); return; }
  stopMic();
  if (player) { player.pause(); player = null; }
  if (socket) socket.close();
  reset();
  enterCall("typed");
  $("#status").textContent = t("checking_text");
  try {
    const r = await fetch(`/api/said?lang=${lang}&country=${country}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || r.statusText);
    $("#status").textContent = t("typed");
    $("#engine").textContent = `Judge: ${data.judge}`;
    $("#standin").hidden = data.judge.startsWith("Muse Spark");  // the transcript panel, with the judge line, is hidden here
    state.call = { id: "typed" };
    data.signals.forEach(addSignal);
    if (data.warning) showAlarm({ warning: data.warning });
    showAhead(data.ahead);
    updateWaiting();
    state.report = data.report_text || data.report_markdown;
    $("#report").textContent = state.report;
    $("#report-wrap").hidden = false;
  } catch (err) {
    $("#status").textContent = String(err.message || err);
  }
}

async function listen() {
  if (mic) {
    if (socket && socket.readyState === 1) socket.send(JSON.stringify({ type: "stop" }));
    stopMic();
    return;
  }
  if (socket) socket.close();
  reset();
  enterCall("live");
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
    socket = new WebSocket(`${proto}://${location.host}/ws/live?lang=${lang}&country=${country}`);
    socket.binaryType = "arraybuffer";
    node.port.onmessage = (m) => {
      // A phone on a call gives the page silence (the call keeps the microphone), so notice it.
      const pcm = new Int16Array(m.data);
      for (let i = 0; i < pcm.length; i += 4) if (Math.abs(pcm[i]) > 32) { if (mic) mic.heardAt = performance.now(); break; }
      if (socket.readyState === 1) socket.send(m.data);
    };
    socket.onmessage = (msg) => handle(JSON.parse(msg.data), 1);
    socket.onclose = stopMic;
    mic = { stream, ctx, heardAt: performance.now() };
    mic.quiet = setInterval(() => { $("#silent").hidden = performance.now() - mic.heardAt < 8000; }, 1000);
  } catch (err) {
    $("#status").textContent = String(err.message || err);
    stopMic();
  }
}

function stopMic() {
  if (!mic) return;
  mic.stream.getTracks().forEach((track) => track.stop());
  mic.ctx.close();
  clearInterval(mic.quiet);
  $("#silent").hidden = true;
  mic = null;
  setBack("back");
}

function handle(e, speed) {
    if (e.type === "start") {
      state.call = e.call;
      // A recorded re-enactment plays its own audio, in step with its saved transcript (speed 1 only).
      if (e.call.audio && speed === 1) { player = new Audio(e.call.audio); player.play().catch(() => {}); }
      $("#voiced").hidden = !(e.call.audio && speed === 1);
      $("#engine").textContent = e.call.judge ? `Judge: ${e.call.judge}` : "";
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
    else if (e.type === "next") showNext(e);
    else if (e.type === "came_true") cameTrue(e);
    else if (e.type === "end") finish(e);
    else if (e.type === "error") $("#status").textContent = e.message;
    updateWaiting();
}

async function init() {
  setCountry(country);
  $("#country").addEventListener("change", (e) => setCountry(e.target.value));
  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
  const setBig = (on) => {
    document.documentElement.classList.toggle("big", on);
    $("#big").setAttribute("aria-pressed", String(on));
    try { localStorage.setItem("tk-big", on ? "1" : ""); } catch (e) {}
  };
  let big = false;
  try { big = localStorage.getItem("tk-big") === "1"; } catch (e) {}
  setBig(big);
  $("#big").addEventListener("click", () => setBig(!document.documentElement.classList.contains("big")));
  questions = (await fetch("/api/signals").then((r) => r.json())).signals;
  renderQuestions();
  const calls = await fetch("/api/calls").then((r) => r.json());
  const select = $("#call");
  demoCalls = calls;
  calls.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.id;
    select.appendChild(o);
  });
  labelCalls();
  $("#play").addEventListener("click", play);
  $("#watch").addEventListener("click", () => { const h = hero(); if (h) select.value = h.id; play(); });
  $("#back").addEventListener("click", () => {
    if (mic) { if (socket && socket.readyState === 1) socket.send(JSON.stringify({ type: "stop" })); stopMic(); }
    else goHome();
  });
  $("#live").addEventListener("click", listen);
  $("#check").addEventListener("click", checkSaid);
  $("#example").addEventListener("click", () => { $("#said").value = t("example_text"); checkSaid(); });
  try {
    liveAvailable = (await fetch("/api/status").then((r) => r.json())).live;
  } catch (e) {}
  try {
    voiceLines = await fetch("/api/voice").then((r) => r.json());
  } catch (e) {}
  // With live listening on, it leads and the demo steps back; on the public page, the demo leads.
  $("#live").hidden = !liveAvailable;
  $("#watch").classList.toggle("quiet", liveAvailable);
  $("#upload").hidden = !liveAvailable;
  $("#file").addEventListener("change", (e) => { if (e.target.files[0]) checkFile(e.target.files[0]); e.target.value = ""; });
  const hint = $("#live-hint");
  hint.dataset.t = liveAvailable ? "live_on" : "live_off";
  hint.textContent = t(hint.dataset.t);
  $("#copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(state.report);
      $("#copy").textContent = t("copied");
      setTimeout(() => ($("#copy").textContent = t("copy")), 1500);
    } catch (e) {}
  });
  $("#download").addEventListener("click", () => {
    const blob = new Blob([state.report], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `teesra-kaan-report-${state.call ? state.call.id : "call"}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
  reset();
}

init();
