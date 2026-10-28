"""What the person on the call sees and hears, in English, Hindi and Marathi.

DRAFT, Oct 28: the Hindi and Marathi lines must be checked by a native speaker
before they're recorded or shown. Each fact line comes from an advisory cited in
docs/scam-tactics.md.
"""

from __future__ import annotations

from .signals import Alarm, Level

LANGS = ("en", "hi", "mr")

HEADLINE = {
    Level.RED: {
        "en": "Danger: this looks like a scam call",
        "hi": "ख़तरा: यह धोखाधड़ी वाला कॉल लग रहा है",
        "mr": "धोका: हा फसवणुकीचा कॉल वाटतो",
    },
    Level.AMBER: {
        "en": "Careful: the caller is using pressure tactics",
        "hi": "सावधान: कॉल करने वाला आप पर दबाव डाल रहा है",
        "mr": "सावध राहा: फोन करणारा तुमच्यावर दबाव टाकत आहे",
    },
}

ACTION = {
    Level.RED: {
        "en": "Hang up now. Don't share any OTP or PIN, and don't send money. If you already have, call 1930.",
        "hi": "अभी फ़ोन काटें। कोई OTP या PIN न बताएँ, पैसे न भेजें। अगर भेज दिए हैं तो 1930 पर कॉल करें।",
        "mr": "आत्ताच फोन ठेवा. कोणताही OTP किंवा PIN सांगू नका, पैसे पाठवू नका. पाठवले असतील तर 1930 वर कॉल करा.",
    },
    Level.AMBER: {
        "en": "Don't share or send anything. You can hang up and call the official number yourself.",
        "hi": "कुछ भी न बताएँ, न भेजें। आप फ़ोन काटकर ख़ुद आधिकारिक नंबर पर कॉल कर सकते हैं।",
        "mr": "काहीही सांगू नका किंवा पाठवू नका. फोन ठेवून तुम्ही स्वतः अधिकृत नंबरवर कॉल करू शकता.",
    },
}

CALLER_SAID = {"en": "The caller said:", "hi": "कॉल करने वाले ने कहा:", "mr": "फोन करणाऱ्याने सांगितले:"}

SIGNAL_NAME = {
    "A1": {"en": "Claims to be an official", "hi": "अधिकारी होने का दावा", "mr": "अधिकारी असल्याचा दावा"},
    "A2": {"en": "Threat", "hi": "धमकी", "mr": "धमकी"},
    "A3": {"en": "Rushing you", "hi": "जल्दबाज़ी", "mr": "घाई"},
    "A4": {"en": "Told to keep it secret", "hi": "किसी को न बताने को कहा", "mr": "कोणाला न सांगण्यास सांगितले"},
    "A5": {"en": "Asked for OTP or PIN", "hi": "OTP/PIN माँगा", "mr": "OTP/PIN मागितला"},
    "A6": {"en": "Asked for money", "hi": "पैसे माँगे", "mr": "पैसे मागितले"},
    "A7": {"en": "Asked to open an app or link", "hi": "ऐप या लिंक खुलवाया", "mr": "अ‍ॅप किंवा लिंक उघडायला सांगितले"},
    "A8": {"en": "Moved you to video or WhatsApp", "hi": "वीडियो कॉल या व्हाट्सएप पर बुलाया", "mr": "व्हिडिओ कॉल किंवा व्हॉट्सअ‍ॅपवर बोलावले"},
    "A9": {"en": "Says your parcel is illegal", "hi": "पार्सल में ग़ैरक़ानूनी सामान", "mr": "पार्सलमध्ये बेकायदेशीर वस्तू"},
    "A10": {"en": "Press-a-key message", "hi": "बटन दबाने को कहा", "mr": "बटण दाबायला सांगितले"},
    "A11": {"en": "PIN to receive money", "hi": "पैसे पाने के लिए PIN", "mr": "पैसे मिळवण्यासाठी PIN"},
    "A12": {"en": "Prize or refund bait", "hi": "इनाम या रिफंड का लालच", "mr": "बक्षीस किंवा रिफंडचे आमिष"},
}

# (signals that must all be present, fact). The first matching facts are shown.
FACTS: tuple[tuple[frozenset[str], dict[str, str]], ...] = (
    (frozenset({"A1", "A8"}), {
        "en": "No police, CBI, ED or customs officer arrests anyone on a video call. There is no 'digital arrest' in law.",
        "hi": "कोई भी पुलिस, CBI, ED या कस्टम अधिकारी वीडियो कॉल पर किसी को गिरफ़्तार नहीं करता। कानून में 'डिजिटल अरेस्ट' जैसा कुछ नहीं है।",
        "mr": "कोणताही पोलीस, CBI, ED किंवा कस्टम अधिकारी व्हिडिओ कॉलवर कोणालाही अटक करत नाही. कायद्यात 'डिजिटल अरेस्ट' असे काहीही नाही.",
    }),
    (frozenset({"A1", "A2", "A4"}), {
        "en": "No police, CBI, ED or customs officer arrests anyone on a video call. There is no 'digital arrest' in law.",
        "hi": "कोई भी पुलिस, CBI, ED या कस्टम अधिकारी वीडियो कॉल पर किसी को गिरफ़्तार नहीं करता। कानून में 'डिजिटल अरेस्ट' जैसा कुछ नहीं है।",
        "mr": "कोणताही पोलीस, CBI, ED किंवा कस्टम अधिकारी व्हिडिओ कॉलवर कोणालाही अटक करत नाही. कायद्यात 'डिजिटल अरेस्ट' असे काहीही नाही.",
    }),
    (frozenset({"A11"}), {
        "en": "Your UPI PIN is only for sending money. You never need it to receive money.",
        "hi": "UPI PIN सिर्फ़ पैसे भेजने के लिए होता है। पैसे पाने के लिए PIN की कभी ज़रूरत नहीं होती।",
        "mr": "UPI PIN फक्त पैसे पाठवण्यासाठी असतो. पैसे मिळवण्यासाठी PIN ची कधीच गरज नसते.",
    }),
    (frozenset({"A5"}), {
        "en": "Your bank will never ask for your OTP, PIN, CVV or password.",
        "hi": "आपका बैंक कभी भी आपका OTP, PIN, CVV या पासवर्ड नहीं माँगता।",
        "mr": "तुमची बँक कधीही तुमचा OTP, PIN, CVV किंवा पासवर्ड मागत नाही.",
    }),
    (frozenset({"A10"}), {
        "en": "TRAI and DoT don't make calls about blocking your number.",
        "hi": "TRAI और DoT नंबर बंद करने के बारे में ऐसे कॉल नहीं करते।",
        "mr": "TRAI आणि DoT नंबर बंद करण्याबद्दल असे कॉल करत नाहीत.",
    }),
)


def facts_for(signals: frozenset[str], lang: str) -> list[str]:
    seen, out = set(), []
    for needed, text in FACTS:
        if needed <= signals and text["en"] not in seen:
            seen.add(text["en"])
            out.append(text[lang])
    return out


def warning(alarm: Alarm, quotes: dict[str, str], lang: str = "en") -> dict | None:
    """The warning screen's content, or None when there's nothing to warn about."""
    if alarm.level == Level.NONE:
        return None
    return {
        "level": alarm.level.name.lower(),
        "headline": HEADLINE[alarm.level][lang],
        "action": ACTION[alarm.level][lang],
        "caller_said_label": CALLER_SAID[lang],
        "signals": [
            {"id": sid, "name": SIGNAL_NAME[sid][lang], "quote": quotes.get(sid, "")}
            for sid in sorted(alarm.signals, key=lambda s: int(s[1:]))
        ],
        "facts": facts_for(alarm.signals, lang),
    }
