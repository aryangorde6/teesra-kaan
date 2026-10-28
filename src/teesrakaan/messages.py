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

# Where a red warning sends you depends on where you are. India is the default; the US
# lines follow the FTC's consumer advice (consumer.ftc.gov, "government impersonator scam").
COUNTRIES = ("IN", "US")

RED_ACTION_US = {
    "en": "Hang up now. Don't share any code or PIN, and don't send money, gift cards or crypto. "
          "If you already have, call your bank now, then report it at ReportFraud.ftc.gov.",
    "hi": "अभी फ़ोन काटें। कोई कोड या PIN न बताएँ, और पैसे, गिफ़्ट कार्ड या क्रिप्टो न भेजें। "
          "अगर भेज दिए हैं तो अभी अपने बैंक को कॉल करें, फिर ReportFraud.ftc.gov पर शिकायत करें।",
    "mr": "आत्ताच फोन ठेवा. कोणताही कोड किंवा PIN सांगू नका, आणि पैसे, गिफ्ट कार्ड किंवा क्रिप्टो पाठवू नका. "
          "पाठवले असतील तर आत्ताच तुमच्या बँकेला कॉल करा, मग ReportFraud.ftc.gov वर तक्रार करा.",
}


def action(level: Level, lang: str, country: str = "IN") -> str:
    """What to do now. Only a red warning names a helpline, so only it changes with the country."""
    if level == Level.RED and country == "US":
        return RED_ACTION_US[lang]
    return ACTION[level][lang]


CALLER_SAID = {"en": "The caller said:", "hi": "कॉल करने वाले ने कहा:", "mr": "फोन करणाऱ्याने सांगितले:"}

SIGNAL_NAME = {
    "A1": {"en": "Claims to be an official", "hi": "अधिकारी होने का दावा", "mr": "अधिकारी असल्याचा दावा"},
    "A2": {"en": "Threat or alarm", "hi": "धमकी या डर", "mr": "धमकी किंवा भीती"},
    "A3": {"en": "Rushing you", "hi": "जल्दबाज़ी", "mr": "घाई"},
    "A4": {"en": "Told to keep it secret", "hi": "किसी को न बताने को कहा", "mr": "कोणाला न सांगण्यास सांगितले"},
    "A5": {"en": "Asked for OTP or PIN", "hi": "OTP/PIN माँगा", "mr": "OTP/PIN मागितला"},
    "A6": {"en": "Asked for money", "hi": "पैसे माँगे", "mr": "पैसे मागितले"},
    "A7": {"en": "Asked to open an app or link", "hi": "ऐप या लिंक खुलवाया", "mr": "अ‍ॅप किंवा लिंक उघडायला सांगितले"},
    "A8": {"en": "Moved you to video or WhatsApp", "hi": "वीडियो कॉल या व्हाट्सएप पर बुलाया", "mr": "व्हिडिओ कॉल किंवा व्हॉट्सअ‍ॅपवर बोलावले"},
    "A9": {"en": "Says your parcel is illegal", "hi": "पार्सल में ग़ैरक़ानूनी सामान", "mr": "पार्सलमध्ये बेकायदेशीर वस्तू"},
    "A10": {"en": "Press-a-key message", "hi": "बटन दबाने को कहा", "mr": "बटण दाबायला सांगितले"},
    "A11": {"en": "PIN to receive money", "hi": "पैसे पाने के लिए PIN", "mr": "पैसे मिळवण्यासाठी PIN"},
    "A12": {"en": "Prize, refund or offer bait", "hi": "इनाम, रिफंड या ऑफ़र का लालच", "mr": "बक्षीस, रिफंड किंवा ऑफरचे आमिष"},
}

# (signals that must all be present, country, fact). The matching facts for the country are shown.
FACTS: tuple[tuple[frozenset[str], str, dict[str, str]], ...] = (
    (frozenset({"A1", "A8"}), "IN", {
        "en": "No police, CBI, ED or customs officer arrests anyone on a video call. There is no 'digital arrest' in law.",
        "hi": "कोई भी पुलिस, CBI, ED या कस्टम अधिकारी वीडियो कॉल पर किसी को गिरफ़्तार नहीं करता। कानून में 'डिजिटल अरेस्ट' जैसा कुछ नहीं है।",
        "mr": "कोणताही पोलीस, CBI, ED किंवा कस्टम अधिकारी व्हिडिओ कॉलवर कोणालाही अटक करत नाही. कायद्यात 'डिजिटल अरेस्ट' असे काहीही नाही.",
    }),
    (frozenset({"A1", "A2", "A4"}), "IN", {
        "en": "No police, CBI, ED or customs officer arrests anyone on a video call. There is no 'digital arrest' in law.",
        "hi": "कोई भी पुलिस, CBI, ED या कस्टम अधिकारी वीडियो कॉल पर किसी को गिरफ़्तार नहीं करता। कानून में 'डिजिटल अरेस्ट' जैसा कुछ नहीं है।",
        "mr": "कोणताही पोलीस, CBI, ED किंवा कस्टम अधिकारी व्हिडिओ कॉलवर कोणालाही अटक करत नाही. कायद्यात 'डिजिटल अरेस्ट' असे काहीही नाही.",
    }),
    (frozenset({"A11"}), "IN", {
        "en": "Your UPI PIN is only for sending money. You never need it to receive money.",
        "hi": "UPI PIN सिर्फ़ पैसे भेजने के लिए होता है। पैसे पाने के लिए PIN की कभी ज़रूरत नहीं होती।",
        "mr": "UPI PIN फक्त पैसे पाठवण्यासाठी असतो. पैसे मिळवण्यासाठी PIN ची कधीच गरज नसते.",
    }),
    (frozenset({"A5"}), "IN", {
        "en": "Your bank will never ask for your OTP, PIN, CVV or password.",
        "hi": "आपका बैंक कभी भी आपका OTP, PIN, CVV या पासवर्ड नहीं माँगता।",
        "mr": "तुमची बँक कधीही तुमचा OTP, PIN, CVV किंवा पासवर्ड मागत नाही.",
    }),
    (frozenset({"A10"}), "IN", {
        "en": "TRAI and DoT don't make calls about blocking your number.",
        "hi": "TRAI और DoT नंबर बंद करने के बारे में ऐसे कॉल नहीं करते।",
        "mr": "TRAI आणि DoT नंबर बंद करण्याबद्दल असे कॉल करत नाहीत.",
    }),
    # The US facts quote the FTC's "How to avoid a government impersonator scam".
    (frozenset({"A1", "A2"}), "US", {
        "en": "The IRS won't threaten to arrest you, and the real Social Security Administration won't threaten you or suspend your Social Security number.",
        "hi": "IRS आपको गिरफ़्तारी की धमकी नहीं देता, और असली Social Security Administration न आपको धमकाता है, न आपका Social Security नंबर बंद करता है।",
        "mr": "IRS तुम्हाला अटकेची धमकी देत नाही, आणि खरे Social Security Administration तुम्हाला धमकावत नाही किंवा तुमचा Social Security नंबर बंद करत नाही.",
    }),
    (frozenset({"A1", "A6"}), "US", {
        "en": "No government agency will demand that you wire money or pay with gift cards, cryptocurrency or a payment app.",
        "hi": "कोई भी सरकारी एजेंसी वायर ट्रांसफ़र, गिफ़्ट कार्ड, क्रिप्टो या पेमेंट ऐप से पैसे नहीं माँगती।",
        "mr": "कोणतीही सरकारी संस्था वायर ट्रान्सफर, गिफ्ट कार्ड, क्रिप्टो किंवा पेमेंट अ‍ॅपने पैसे मागत नाही.",
    }),
    (frozenset({"A1", "A5"}), "US", {
        "en": "Government agencies will never call, email or text you to ask for money or personal information.",
        "hi": "सरकारी एजेंसियाँ कभी कॉल, ईमेल या मैसेज करके पैसे या निजी जानकारी नहीं माँगतीं।",
        "mr": "सरकारी संस्था कधीही कॉल, ईमेल किंवा मेसेज करून पैसे किंवा वैयक्तिक माहिती मागत नाहीत.",
    }),
)


def facts_for(signals: frozenset[str], lang: str, country: str = "IN") -> list[str]:
    seen, out = set(), []
    for needed, where, text in FACTS:
        if where == country and needed <= signals and text["en"] not in seen:
            seen.add(text["en"])
            out.append(text[lang])
    return out


def warning(alarm: Alarm, quotes: dict[str, str], lang: str = "en", country: str = "IN") -> dict | None:
    """The warning screen's content, or None when there's nothing to warn about."""
    if alarm.level == Level.NONE:
        return None
    return {
        "level": alarm.level.name.lower(),
        "headline": HEADLINE[alarm.level][lang],
        "action": action(alarm.level, lang, country),
        "caller_said_label": CALLER_SAID[lang],
        "signals": [
            {"id": sid, "name": SIGNAL_NAME[sid][lang], "quote": quotes.get(sid, "")}
            for sid in sorted(alarm.signals, key=lambda s: int(s[1:]))
        ],
        "facts": facts_for(alarm.signals, lang, country),
    }


# The next line (playbook.py): each signal as a scam script's caller says it.
NEXT_LABEL = {
    "en": "Next line in this scam's script:",
    "hi": "इस ठगी की स्क्रिप्ट की अगली लाइन:",
    "mr": "या फसवणुकीच्या स्क्रिप्टमधली पुढची ओळ:",
}

NEXT_LINE = {
    "A1": {"en": "I'm calling from the police, or your bank.", "hi": "मैं पुलिस या बैंक से बोल रहा हूँ।",
           "mr": "मी पोलीस किंवा बँकेतून बोलतोय."},
    "A2": {"en": "There's a case against you.", "hi": "आपके नाम पर केस दर्ज है।", "mr": "तुमच्या नावावर केस दाखल आहे."},
    "A3": {"en": "You must do it right now.", "hi": "अभी के अभी करना होगा।", "mr": "आत्ताच्या आत्ता करावं लागेल."},
    "A4": {"en": "Don't tell anyone. Don't hang up.", "hi": "किसी को मत बताना। फ़ोन मत काटना।",
           "mr": "कोणालाही सांगू नका. फोन ठेवू नका."},
    "A5": {"en": "Tell me the OTP.", "hi": "OTP बताइए।", "mr": "OTP सांगा."},
    "A6": {"en": "Transfer the money for verification.", "hi": "वेरिफ़िकेशन के लिए पैसे ट्रांसफ़र कीजिए।",
           "mr": "पडताळणीसाठी पैसे ट्रान्सफर करा."},
    "A7": {"en": "Install this app, or open this link.", "hi": "यह ऐप डाउनलोड कीजिए, या यह लिंक खोलिए।",
           "mr": "हे ॲप डाउनलोड करा, किंवा ही लिंक उघडा."},
    "A8": {"en": "Come on a video call.", "hi": "वीडियो कॉल पर आइए।", "mr": "व्हिडिओ कॉलवर या."},
    "A9": {"en": "A parcel in your name has been seized.", "hi": "आपके नाम का पार्सल पकड़ा गया है।",
           "mr": "तुमच्या नावाचं पार्सल पकडलं आहे."},
    "A10": {"en": "Press 9 to speak to an officer.", "hi": "अधिकारी से बात करने के लिए 9 दबाइए।",
            "mr": "अधिकाऱ्याशी बोलण्यासाठी 9 दाबा."},
    "A11": {"en": "Enter your UPI PIN to receive the money.", "hi": "पैसे पाने के लिए UPI PIN डालिए।",
            "mr": "पैसे मिळवण्यासाठी UPI PIN टाका."},
    "A12": {"en": "You've won a prize, or you're owed a refund.", "hi": "आपने इनाम जीता है, या आपका रिफ़ंड बाकी है।",
            "mr": "तुम्ही बक्षीस जिंकलं आहे, किंवा तुमचा रिफंड बाकी आहे."},
}

CAME_TRUE = {
    "en": "The caller just said it: “{quote}”. This call is following a scam script.",
    "hi": "कॉल करने वाले ने अभी यही कहा: “{quote}”। यह कॉल ठगी की स्क्रिप्ट पर चल रहा है।",
    "mr": "फोन करणाऱ्याने आत्ता हेच सांगितलं: “{quote}”. हा कॉल फसवणुकीच्या स्क्रिप्टप्रमाणे चालला आहे.",
}


def next_line(step: str, lang: str = "en") -> dict:
    return {"id": step, "label": NEXT_LABEL[lang], "line": NEXT_LINE[step][lang], "name": SIGNAL_NAME[step][lang]}


def came_true(step: str, quote: str, lang: str = "en") -> dict:
    return {"id": step, "text": CAME_TRUE[lang].format(quote=quote), "quote": quote}


def prediction_events(update, lang: str = "en") -> list[dict]:
    """The page events for a Listener update's next line: any that came true, then the one now shown."""
    out = [{"type": "came_true", "said_at": round(p.said_at, 1), **came_true(p.step, p.quote, lang)}
           for p in update.came_true]
    if update.next_changed:
        out.append({"type": "next", **next_line(update.next.step, lang)} if update.next else {"type": "next", "id": None})
    return out
