"""A keyword judge: fixed word lists in Hinglish, Hindi, Marathi and English, no model.

It is two things: the offline stand-in for Muse Spark, so everything runs without the
API, and comparison A in docs/evaluation-rule.md (keywords + the same rules).
Its known weakness is meaning: "we never ask for your OTP" still matches "OTP ... ask".
The paraphrase test must avoid every pattern in this file.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from .judge import Answer, Reply
from .signals import Signal
from .transcript import Transcript

_L = r"[\wऀ-ॿ]"  # a letter, digit or Devanagari character


def word(p: str) -> str:
    return rf"(?<!{_L})(?:{p})(?!{_L})"


def stem(p: str) -> str:
    """Matches at a word start, any ending: for Hindi and Marathi inflections."""
    return rf"(?<!{_L})(?:{p})"


def near(a: str, b: str, gap: int = 40) -> str:
    """a and b in either order, at most `gap` characters apart, in the same sentence."""
    within = rf"[^.!?।\n]{{0,{gap}}}"
    return rf"(?:{a}){within}(?:{b})|(?:{b}){within}(?:{a})"


_OTP = word(r"otp|o\.t\.p|pin|cvv|password|ओटीपी|पिन|पासवर्ड") + "|" + stem(
    r"aadhaar|aadhar|adhar|pan card|card number|account number|आधार|पैन|कार्ड नंबर|खाता नंबर|अकाउंट नंबर"
)
_TELL = stem(
    r"bata do|bataiye|batayiye|batao|bataye|boliye|bol do|share kar|share ki|bhejo|bhejiye|bhej do|bhej dijiye|"
    r"send|tell me|give me|read out|de do|dijiye|sanga|sangaa|dya|"
    r"बता दो|बताइए|बताओ|बताएं|बताएँ|बोलिए|शेयर कर|भेजो|भेजिए|भेज दो|दीजिए|दे दो|सांगा|द्या|पाठवा"
)
_MONEY = stem(r"paise|paisa|paisay|rupaye|rupay|rupees|rs\b|lakh|hazaar|hajar|amount|fee|fine|deposit|payment|"
              r"पैसे|पैसा|रुपये|रुपए|लाख|हज़ार|हजार|रक्कम|शुल्क|फ़ीस|जुर्माना|दंड") + "|₹|\\d[\\d,]{2,}"
_PAY = stem(r"transfer|bhejo|bhejiye|bhej do|bhej dijiye|pay|jama karo|jama kariye|jama kijiye|jama karni|jama karna|jama karne|bharo|bhariye|"
            r"chahiye|send|deposit|ट्रांसफ़र|ट्रांसफर|भेजो|भेजिए|भेज दो|भेज दीजिए|जमा करो|जमा करें|जमा कीजिए|जमा करनी|"
            r"चाहिए|भरो|भरिए|पाठवा|भरा|भरावे|जमा करा")

PATTERNS: dict[str, tuple[str, ...]] = {
    "A1": (
        word(r"cbi|ncb|trai|dot|rbi|ed officer|सीबीआई|ट्राई|आरबीआई"),
        stem(r"police|crime branch|cyber cell|customs|narcotics|enforcement directorate|income tax|"
             r"court|judge|inspector|officer|reserve bank|department of telecom|telecom department|"
             r"पुलिस|पोलीस|क्राइम ब्रांच|कस्टम|नारकोटिक्स|कोर्ट|न्यायालय|अदालत|इंस्पेक्टर|अधिकारी|ऑफिसर"),
        near(stem(r"main|mai|hum|i am|we are|calling from|this is|मैं|हम|मी|आम्ही"),
             stem(r"bank|बैंक|बँक"), 30),
        # v1.2, from FTC dev: agencies and companies the caller pretends to be
        stem(r"social security|ssa\b|irs\b|internal revenue|federal|department of|consulate|embassy|"
             r"legal department|amazon|flipkart|paytm|apple support|jio\b|airtel|vodafone|bsnl|"
             r"electricity (?:company|board|department)|power company|msedcl|mahavitaran|discover\b|spectrum|"
             r"at&t|directv|direct tv|अमेज़न|अमेजन|फ्लिपकार्ट|बिजली विभाग|महावितरण|वीज मंडळ"),
    ),
    "A2": (
        stem(r"arrest|giraftar|giraftaar|warrant|fir\b|jail|money laundering|legal action|suspend|deactivat|"
             r"disconnect|गिरफ्तार|गिरफ़्तार|वारंट|एफआईआर|जेल|अटक|गुन्हा|कानूनी कार्रवाई|कारवाई"),
        near(stem(r"case|केस"), stem(r"darj|register|file|दर्ज|दाखल"), 20),
        # The courier opening (pattern 2): drugs "found" in a parcel, and a case "linked" to you.
        stem(r"mdma|narcotic|drug trafficking|drugs? (?:were |was )?found|ड्रग्स|ड्रग|तस्करी|अमली पदार्थ"),
        near(stem(r"case|केस"), stem(r"linked|connected|juda|jud gaya|जुड़ा|जुडा|जोडल"), 25),
        stem(r"pakad liya|पकड़ा गया|पकड़ लिया|arrested|"
             r"suspicious activit|unauthori[sz]ed|fraudulent (?:activit|charge|transaction)|"
             r"order (?:has been |was )?placed|disconnection|संदिग्ध|अनधिकृत|संशयास्पद"),
        near(stem(r"block|band|bandh|suspend|cut|ब्लॉक|बंद|कट"),
             stem(r"ho jayega|ho jaayega|kar diya jayega|hoga|will be|होगा|हो जाएगा|कर दिया जाएगा|होईल|केला जाईल"), 25),
    ),
    "A3": (
        stem(r"abhi ke abhi|abhi turant|turant|immediately|right now|urgent|jaldi|aaj hi|today itself|"
             r"as soon as possible|final notice|final courtesy|limited time|"
             r"तुरंत|अभी के अभी|जल्दी|आज ही|ताबडतोब|लगेच|आत्ताच|आजच"),
        near(stem(r"within|andar|ke andar|में|आत|च्या आत"), stem(r"\d+ ?(?:hours?|minutes?|ghante|minute|घंटे|मिनट|तास|मिनिट)"), 20),
        stem(r"\d+ ?(?:ghante|घंटे|तासात|तासांत)|do ghante|दो घंटे|दोन तास"),
    ),
    "A4": (
        stem(r"kisi ko bataya to|told anyone|किसी को बताया तो|कोणाला सांगितलं तर"),
        near(stem(r"kisi|kisi ko|anyone|family|ghar|mummy|papa|parents|husband|wife|uncle|aunty|"
                  r"किसी|कोणाला|कुणाला|घर|मम्मी|पापा|अंकल|काकांना|घरच्यांना"),
             stem(r"mat bata|na bata|nahi bata|don't tell|do not tell|don't inform|do not inform|"
                  r"मत बता|न बता|सांगू नका|सांगू नकोस|कळवू नका"), 25),
        near(stem(r"call|phone|line|कॉल|फोन|फ़ोन"),
             stem(r"cut mat|disconnect mat|mat kaat|mat kat|don't disconnect|do not disconnect|don't hang|"
                  r"मत काट|ठेवू नका|कट करू नका"), 25),
        stem(r"confidential|secret|गोपनीय|गुप्त|stay on the (?:call|line)|camera on|video on|akele|alone|अकेले|एकटे"),
    ),
    "A5": (
        near(_OTP, _TELL, 30),
    ),
    "A6": (
        near(_MONEY, _PAY, 40),
        stem(r"safe account|rbi account|verification ke liye|सुरक्षित खाते|वेरिफिकेशन"),
    ),
    "A7": (
        stem(r"anydesk|any desk|teamviewer|team viewer|quicksupport|quick support|screen share|share (?:your|the|my) screen|apk|"
             r"एनीडेस्क|स्क्रीन शेयर"),
        near(stem(r"app|ऐप|अ‍ॅप|ॲप"), stem(r"download|install|डाउनलोड|इंस्टॉल"), 25),
        near(stem(r"link|लिंक"), stem(r"click|open|khol|क्लिक|खोल|उघड"), 25),
    ),
    "A8": (
        stem(r"skype|स्काइप|telegram|टेलीग्राम"),
        near(stem(r"video call|video pe|whatsapp|वीडियो कॉल|व्हिडिओ कॉल|व्हाट्सएप|व्हॉट्सअ‍ॅप"),
             stem(r"aaiye|aa jaiye|aao|join|stay on|rahiye|connect|switch|move|आइए|आ जाइए|रहिए|बयान|या|connect"), 25),
    ),
    "A9": (
        near(stem(r"parcel|courier|fedex|dhl|package|पार्सल|कूरियर|कुरियर"),
             stem(r"drug|illegal|seiz|ganja|narcotic|mdma|passport|customs|ड्रग|गैरकानूनी|जब्त|अवैध|बेकायदेशीर|पासपोर्ट"), 60),
    ),
    "A10": (
        near(stem(r"press|dabaye|dabaiye|dabao|दबाएं|दबाइए|दबाएँ|दाबा"), r"\d|one|two|nine|zero", 15),
        near(r"\d", stem(r"dabaye|dabaiye|dabao|दबाएं|दबाइए|दबाएँ|दाबा"), 10),
    ),
    "A11": (
        near(word(r"pin|upi pin|पिन"),
             stem(r"receive|paise aa jayenge|aa jayega|milenge|credit ho|refund|पैसे आ जाएंगे|मिलेंगे|जमा होईल|मिळतील"), 50),
    ),
    "A12": (
        stem(r"bonus|बोनस|qualif(?:y|ied|ies) for|eligible for|\d+% off|rate reduction|relief (?:payment|program)|pre-approved|"
             r"lottery|prize|you have won|aap jeet|jeet gaye|jeete|kbc|kaun banega|cashback|refund|by mistake|"
             r"galti se|wrong transfer|लॉटरी|इनाम|जीत|रिफंड|कैशबैक|गलती से|बक्षीस|चुकून"),
    ),
}



def _nukta_tolerant(pattern: str) -> str:
    """Lets every Devanagari consonant match with or without a nukta: गिरफ्तार also matches गिरफ़्तार."""
    pattern = unicodedata.normalize("NFC", pattern)
    return re.sub("([\u0915-\u0939])\u093c?", "\\1\u093c?", pattern)


_COMPILED = {
    sid: [re.compile(_nukta_tolerant(p), re.IGNORECASE) for p in ps]
    for sid, ps in PATTERNS.items()
}
_SENTENCE_END = re.compile(r"[.!?।\n]")


def _clause(text: str, start: int, end: int, max_words: int = 25) -> str:
    """The sentence around a match, cut to about max_words around it. Whole words only."""
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace() and not _SENTENCE_END.match(text[end]):
        end += 1
    left = max((m.end() for m in _SENTENCE_END.finditer(text, 0, start)), default=0)
    right_match = _SENTENCE_END.search(text, end)
    right = right_match.start() if right_match else len(text)
    before = text[left:start].split()
    after = text[end:right].split()
    room = max(max_words - len(text[start:end].split()), 0)
    keep_before = before[-(room // 2):] if room // 2 else []
    keep_after = after[: room - len(keep_before)]
    return " ".join([*keep_before, text[start:end].strip(), *keep_after]).strip()


class KeywordJudge:
    name = "keywords-v1"

    def ask(self, questions: Sequence[Signal], transcript: Transcript) -> Reply:
        caller = transcript.caller
        lines = [unicodedata.normalize("NFC", line.text) for line in transcript.lines if line.speaker == caller]
        answers = []
        for q in questions:
            hit = None
            for line in lines:
                for pattern in _COMPILED.get(q.id, ()):
                    if m := pattern.search(line):
                        hit = _clause(line, m.start(), m.end())
                        break
                if hit:
                    break
            if hit:
                answers.append(Answer(q.id, hit))
        return Reply(answers)


def keyword_hits(text: str) -> list[tuple[str, str]]:
    """(signal, matched words) for every baseline pattern in `text`. The paraphrase test needs none."""
    text = unicodedata.normalize("NFC", text)
    return [(sid, m.group(0)) for sid, patterns in _COMPILED.items() for p in patterns for m in p.finditer(text)]
