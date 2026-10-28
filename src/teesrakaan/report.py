"""The report pack at hang-up: what a victim needs for 1930 or cybercrime.gov.in, already written down.

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

WHAT_TO_DO = {
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

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    def to_markdown(self) -> str:
        out = [f"# Scam call report: {self.call_id}", ""]
        out.append(f"- **Call length:** {_clock(self.duration)}")
        if self.caller_number:
            out.append(f"- **Caller's number:** {self.caller_number}")
        out.append(f"- **Teesra Kaan's verdict:** {self.level}" + (f" ({self.rule})" if self.rule else ""))
        if self.warned_at is not None:
            out.append(f"- **First warning at:** {_clock(self.warned_at)} into the call")
        out += ["", "## What to do now", *[f"{i}. {s}" for i, s in enumerate(WHAT_TO_DO[self.lang], 1)]]
        if self.facts:
            out += ["", *[f"> {fact}" for fact in self.facts]]
        out += ["", "## What the caller claimed and asked for"]
        for c in self.claims:
            out.append(f"- **{_clock(c['said_at'])} · {c['name']}:** \"{c['quote']}\"")
        if not self.claims:
            out.append("- Nothing matched the warning signs.")
        labels = {
            "amounts": "Amounts", "phone_numbers": "Phone numbers", "upi_ids": "UPI IDs", "emails": "Emails",
            "account_numbers": "Account numbers", "links": "Links", "apps": "Apps",
        }
        found = [(labels[k], v) for k, v in self.mentioned.items() if v]
        out += ["", "## Mentioned by the caller (for the complaint form)"]
        out += [f"- **{name}:** {', '.join(values)}" for name, values in found] or ["- None."]
        out += ["", "## Transcript", ""]
        who = {CALLER: "Caller", "listener": "You"}
        out += [f"- `{_clock(line['start'])}` **{who[line['speaker']]}:** {line['text']}" for line in self.transcript]
        out += ["", "_Prepared automatically by Teesra Kaan from the call audio. Check it before you submit it._", ""]
        return "\n".join(out)


def build_report(call: Call, listener: Listener, lang: str = "en", caller_number: str = "") -> ReportPack:
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
        facts=facts_for(alarm.signals, lang),
        lang=lang,
        caller_number=caller_number,
    )
