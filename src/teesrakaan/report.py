"""The report pack at hang-up: what a victim needs for 1930 or cybercrime.gov.in (or, in the US, ReportFraud.ftc.gov), already written down.

Everything in it comes from the call: the caller's claims with their quotes and
times, and the amounts, numbers, UPI IDs, links and apps the caller mentioned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .listener import Listener
from .messages import SIGNAL_NAME, facts_for
from .signals import Level
from .transcript import CALLER, LISTENER, Call, normalize

_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_AMOUNT = re.compile(
    r"(?:₹|\brs\.?|\binr)\s?\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:rupaye|rupay|rupees?|रुपये|रुपए|रुपया|lakh|लाख|hazaar|hajar|हज़ार|हजार|crore|करोड़)",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_UPI = re.compile(r"(?<![\w.])[\w.-]{2,}@[a-z]{2,}(?![\w.@])", re.IGNORECASE)
_ACCOUNT = re.compile(r"(?<!\d)\d{9,18}(?!\d)")
_LINK = re.compile(r"https?://\S+|www\.\S+|\b[\w-]+\.(?:com|in|net|org|apk|xyz|info|co)\b", re.IGNORECASE)
_APPS = re.compile(
    r"anydesk|any desk|teamviewer|team viewer|quicksupport|quick support|skype|whatsapp|telegram|zoom|"
    r"एनीडेस्क|स्काइप|व्हाट्सएप|व्हॉट्सअ‍ॅप",
    re.IGNORECASE,
)

# Per country (messages.COUNTRIES), then language. The US steps follow the FTC's consumer advice.
WHAT_TO_DO = {"IN": {
    "en": [
        "If you sent money or shared an OTP or PIN: call 1930 (the National Cyber Crime Helpline) now, and report at cybercrime.gov.in. Then call your bank to block the card or account.",
        "If you didn't: don't call the number back. Report it on Chakshu at sancharsaathi.gov.in.",
        "Keep this report, the call recording, SMS messages and screenshots. Don't delete them.",
    ],
    "hi": [
        "अगर आपने पैसे भेजे हैं या OTP/PIN बताया है: अभी 1930 (राष्ट्रीय साइबर अपराध हेल्पलाइन) पर कॉल करें और cybercrime.gov.in पर शिकायत दर्ज करें। फिर अपने बैंक को कॉल करके कार्ड या खाता ब्लॉक करवाएँ।",
        "अगर नहीं भेजे हैं: उस नंबर पर वापस कॉल न करें। sancharsaathi.gov.in पर चक्षु में नंबर की शिकायत करें।",
        "यह रिपोर्ट, कॉल रिकॉर्डिंग, SMS और स्क्रीनशॉट संभालकर रखें। इन्हें डिलीट न करें।",
    ],
    "mr": [
        "तुम्ही पैसे पाठवले असतील किंवा OTP/PIN सांगितला असेल तर: आत्ताच 1930 (राष्ट्रीय सायबर गुन्हे हेल्पलाइन) वर कॉल करा आणि cybercrime.gov.in वर तक्रार नोंदवा. नंतर तुमच्या बँकेला कॉल करून कार्ड किंवा खाते ब्लॉक करा.",
        "पाठवले नसतील तर: त्या नंबरवर परत कॉल करू नका. sancharsaathi.gov.in वर चक्षूमध्ये नंबरची तक्रार करा.",
        "हा अहवाल, कॉल रेकॉर्डिंग, SMS आणि स्क्रीनशॉट जपून ठेवा. ते डिलीट करू नका.",
    ],
}, "US": {
    "en": [
        "If you sent money, gift cards or crypto, or shared a code or PIN: call your bank, or the company you paid through, now. Then report it at ReportFraud.ftc.gov.",
        "If you gave personal information, such as your Social Security number: follow the steps at IdentityTheft.gov.",
        "If you didn't: don't call the number back. Report the call at ReportFraud.ftc.gov.",
        "Keep this report, the call recording, text messages and screenshots. Don't delete them.",
    ],
    "hi": [
        "अगर आपने पैसे, गिफ़्ट कार्ड या क्रिप्टो भेजे हैं, या कोई कोड या PIN बताया है: अभी अपने बैंक को, या जिस कंपनी से पैसे भेजे उसे, कॉल करें। फिर ReportFraud.ftc.gov पर शिकायत करें।",
        "अगर आपने निजी जानकारी दी है, जैसे Social Security नंबर: IdentityTheft.gov पर दिए कदम उठाएँ।",
        "अगर नहीं: उस नंबर पर वापस कॉल न करें। ReportFraud.ftc.gov पर कॉल की शिकायत करें।",
        "यह रिपोर्ट, कॉल रिकॉर्डिंग, मैसेज और स्क्रीनशॉट संभालकर रखें। इन्हें डिलीट न करें।",
    ],
    "mr": [
        "तुम्ही पैसे, गिफ्ट कार्ड किंवा क्रिप्टो पाठवले असतील, किंवा कोड किंवा PIN सांगितला असेल तर: आत्ताच तुमच्या बँकेला, किंवा ज्या कंपनीमार्फत पैसे पाठवले तिला, कॉल करा. मग ReportFraud.ftc.gov वर तक्रार करा.",
        "तुम्ही वैयक्तिक माहिती दिली असेल, जसे Social Security नंबर: IdentityTheft.gov वरील पावले उचला.",
        "नसेल तर: त्या नंबरवर परत कॉल करू नका. ReportFraud.ftc.gov वर कॉलची तक्रार करा.",
        "हा अहवाल, कॉल रेकॉर्डिंग, मेसेज आणि स्क्रीनशॉट जपून ठेवा. ते डिलीट करू नका.",
    ],
}}


# Report headings. DRAFT, Oct 28: the Hindi and Marathi need a native speaker's check.
TEXT = {
    "en": {
        "title": "Scam call report", "length": "Call length", "number": "Caller's number",
        "verdict": "Teesra Kaan's warning", "red": "danger (red)", "amber": "caution (amber)", "none": "none",
        "warned": "First warning, minutes into the call", "todo": "What to do now",
        "claims": "What the caller claimed and asked for", "no_claims": "Nothing matched the warning signs.",
        "mentioned": "Mentioned by the caller (for the complaint form)", "nothing": "Nothing.",
        "amounts": "Amounts", "phone_numbers": "Phone numbers", "upi_ids": "UPI IDs", "emails": "Emails",
        "account_numbers": "Account numbers", "links": "Links", "apps": "Apps",
        "transcript": "Transcript", "caller": "Caller", "you": "You",
        "footer": "Prepared automatically by Teesra Kaan from the call audio. Check it before you submit it.",
    },
    "hi": {
        "title": "स्कैम कॉल रिपोर्ट", "length": "कॉल की अवधि", "number": "कॉल करने वाले का नंबर",
        "verdict": "तीसरा कान की चेतावनी", "red": "ख़तरा (लाल)", "amber": "सावधान (पीला)", "none": "कोई नहीं",
        "warned": "पहली चेतावनी, कॉल के इतने मिनट बाद", "todo": "अब क्या करें",
        "claims": "कॉल करने वाले ने क्या दावा किया और क्या माँगा", "no_claims": "कोई चेतावनी का संकेत नहीं मिला।",
        "mentioned": "कॉल करने वाले ने बताया (शिकायत फ़ॉर्म के लिए)", "nothing": "कुछ नहीं।",
        "amounts": "रकम", "phone_numbers": "फ़ोन नंबर", "upi_ids": "UPI ID", "emails": "ईमेल",
        "account_numbers": "खाता नंबर", "links": "लिंक", "apps": "ऐप",
        "transcript": "बातचीत", "caller": "कॉल करने वाला", "you": "आप",
        "footer": "यह रिपोर्ट तीसरा कान ने कॉल की आवाज़ से अपने आप बनाई है। जमा करने से पहले जाँच लें।",
    },
    "mr": {
        "title": "फसवणुकीच्या कॉलचा अहवाल", "length": "कॉलचा कालावधी", "number": "फोन करणाऱ्याचा नंबर",
        "verdict": "तिसरा कानचा इशारा", "red": "धोका (लाल)", "amber": "सावधान (पिवळा)", "none": "काही नाही",
        "warned": "पहिला इशारा, कॉलच्या इतक्या मिनिटांनंतर", "todo": "आता काय करायचे",
        "claims": "फोन करणाऱ्याने काय दावा केला आणि काय मागितले", "no_claims": "धोक्याचे कोणतेही चिन्ह आढळले नाही.",
        "mentioned": "फोन करणाऱ्याने सांगितलेले (तक्रार फॉर्मसाठी)", "nothing": "काही नाही.",
        "amounts": "रक्कम", "phone_numbers": "फोन नंबर", "upi_ids": "UPI ID", "emails": "ईमेल",
        "account_numbers": "खाते नंबर", "links": "लिंक", "apps": "अ‍ॅप",
        "transcript": "संभाषण", "caller": "फोन करणारा", "you": "तुम्ही",
        "footer": "हा अहवाल तिसरा कानने कॉलच्या आवाजावरून आपोआप तयार केला आहे. सादर करण्यापूर्वी तपासा.",
    },
}


def _unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        key = normalize(item)
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def extract(text: str) -> dict[str, list[str]]:
    """Amounts, phone numbers, UPI IDs, emails, account numbers, links and apps mentioned in `text`."""
    text = text.translate(_DIGITS)
    phones = _unique(_PHONE.findall(text))
    phone_digits = {re.sub(r"\D", "", p)[-10:] for p in phones}
    emails = _unique(_EMAIL.findall(text))
    return {
        "amounts": _unique(_AMOUNT.findall(text)),
        "phone_numbers": phones,
        "upi_ids": _unique([u for u in _UPI.findall(text) if not any(u in e for e in emails)]),
        "emails": emails,
        "account_numbers": _unique([a for a in _ACCOUNT.findall(text) if a[-10:] not in phone_digits]),
        "links": _unique(_LINK.findall(text)),
        "apps": _unique([a.lower() for a in _APPS.findall(text)]),
    }


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


@dataclass
class ReportPack:
    call_id: str
    duration: float
    level: str
    rule: str
    claims: list[dict]  # {id, name, quote, said_at}, in the order they were said
    warned_at: float | None
    mentioned: dict[str, list[str]]
    transcript: list[dict]  # {speaker, start, text}
    facts: list[str] = field(default_factory=list)
    lang: str = "en"
    caller_number: str = ""  # typed in by the user afterwards, if they have it
    country: str = "IN"  # where to report (messages.COUNTRIES)

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    def to_markdown(self) -> str:
        t = TEXT[self.lang]
        level = {"red": t["red"], "amber": t["amber"], "none": t["none"]}[self.level]
        out = [f"# {t['title']}: {self.call_id}", ""]
        out.append(f"- **{t['length']}:** {_clock(self.duration)}")
        if self.caller_number:
            out.append(f"- **{t['number']}:** {self.caller_number}")
        out.append(f"- **{t['verdict']}:** {level}")
        if self.warned_at is not None:
            out.append(f"- **{t['warned']}:** {_clock(self.warned_at)}")
        out += ["", f"## {t['todo']}", *[f"{i}. {s}" for i, s in enumerate(WHAT_TO_DO[self.country][self.lang], 1)]]
        if self.facts:
            out += ["", *[f"> {fact}" for fact in self.facts]]
        out += ["", f"## {t['claims']}"]
        for c in self.claims:
            out.append(f"- **{_clock(c['said_at'])} · {c['name']}:** \"{c['quote']}\"")
        if not self.claims:
            out.append(f"- {t['no_claims']}")
        found = [(t[k], v) for k, v in self.mentioned.items() if v]
        out += ["", f"## {t['mentioned']}"]
        out += [f"- **{name}:** {', '.join(values)}" for name, values in found] or [f"- {t['nothing']}"]
        out += ["", f"## {t['transcript']}", ""]
        who = {CALLER: t["caller"], LISTENER: t["you"]}
        out += [f"- `{_clock(line['start'])}` **{who[line['speaker']]}:** {line['text']}" for line in self.transcript]
        out += ["", f"_{t['footer']}_", ""]
        return "\n".join(out)


def build_report(call: Call, listener: Listener, lang: str = "en", caller_number: str = "", country: str = "IN") -> ReportPack:
    claims = sorted(
        (
            {"id": f.id, "name": SIGNAL_NAME[f.id][lang], "quote": f.quote, "said_at": f.said_at}
            for f in listener.found.values()
        ),
        key=lambda c: c["said_at"],
    )
    alarm = listener.alarm
    caller = call.caller_label()
    return ReportPack(
        call_id=call.id,
        duration=call.duration,
        level=alarm.level.name.lower(),
        rule=alarm.rule,
        claims=claims,
        warned_at=listener.first_time(Level.AMBER),
        mentioned=extract(" \n ".join(t.text for t in call.turns if t.speaker == caller)),
        transcript=[{"speaker": CALLER if t.speaker == caller else LISTENER, "start": t.start, "text": t.text}
                    for t in call.turns],
        facts=facts_for(alarm.signals, lang, country),
        lang=lang,
        caller_number=caller_number,
        country=country,
    )
