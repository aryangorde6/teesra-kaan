"""The fixed yes/no questions about the caller, and the rules that turn answers into a warning.

The model never decides whether a call is a scam. It answers these questions,
quoting the caller, and the rules below decide. See docs/scam-tactics.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

RULES_VERSION = "v1.2 (Oct 28, 2026)"


@dataclass(frozen=True)
class Signal:
    id: str
    name: str
    kind: str  # "ask": the caller wants something; "flag": a pressure or lure tactic
    question: str


SIGNALS: tuple[Signal, ...] = (
    Signal("A1", "Authority", "flag",
           "Does the caller claim to be, or to speak for, the police, CBI, ED, customs, narcotics, "
           "a court or judge, RBI, TRAI, DoT, a consulate, another government office or official, a bank, "
           "or a company the listener may have an account with (such as Amazon, Flipkart, Apple, "
           "a phone, power or card company)?"),
    Signal("A2", "Threat or alarm", "flag",
           "Does the caller threaten the listener with arrest, an FIR or police case, a court case, jail, "
           "a fine, or blocking of their bank account, card, SIM, phone number or electricity; or alarm them "
           "with claimed suspicious activity, an unauthorized order or charge, or a problem on their account?"),
    Signal("A3", "Urgency", "flag",
           "Does the caller demand that the listener act right now, as soon as possible, or within a deadline "
           "(minutes, hours, today)?"),
    Signal("A4", "Isolation", "flag",
           "Does the caller tell the listener to keep this secret, not to tell family or anyone, "
           "not to hang up or disconnect, to stay on a video call, or to go somewhere alone?"),
    Signal("A5", "Secrets", "ask",
           "Does the caller ask the listener to say, type or send an OTP, PIN, CVV or password, "
           "or their Aadhaar, PAN, card or bank account number?"),
    Signal("A6", "Money", "ask",
           "Does the caller ask the listener to pay, transfer or deposit money (a fine, fee or tax, "
           "a 'verification' or 'security' deposit, a 'safe' or 'RBI' account, a UPI request)?"),
    Signal("A7", "Remote control", "ask",
           "Does the caller ask the listener to install an app (such as AnyDesk, TeamViewer or an APK file), "
           "share their screen, or open or click a link?"),
    Signal("A8", "Channel switch", "flag",
           "Does the caller ask the listener to move to a video call, WhatsApp, Skype, Telegram, "
           "or another app or number?"),
    Signal("A9", "Parcel", "flag",
           "Does the caller say a parcel, courier or package in the listener's name holds drugs, "
           "passports or other illegal items, or has been seized?"),
    Signal("A10", "Press a key", "flag",
           "Is this an automated or recorded message telling the listener to press a key "
           "to speak to an officer or agent?"),
    Signal("A11", "PIN to receive", "ask",
           "Does the caller say the listener must enter a UPI PIN, or approve a request, "
           "in order to receive money, a refund or a prize?"),
    Signal("A12", "Windfall", "flag",
           "Does the caller say the listener has won a prize, lottery, cashback or refund, qualifies for "
           "a special discount, rate cut, loan or relief payment, or that money was sent to them by mistake "
           "and must be returned?"),
)

BY_ID: dict[str, Signal] = {s.id: s for s in SIGNALS}
ASKS = frozenset(s.id for s in SIGNALS if s.kind == "ask")
FLAGS = frozenset(s.id for s in SIGNALS if s.kind == "flag")
DIGITAL_ARREST_OPENING = frozenset({"A1", "A2", "A4"})


class Level(IntEnum):
    NONE = 0
    AMBER = 1  # caution: pressure tactics, nothing asked yet
    RED = 2  # danger: hang up


@dataclass(frozen=True)
class Alarm:
    level: Level
    rule: str  # which rule fired, for the warning text and the report
    signals: frozenset[str]  # the "yes" signals at the time


def decide(yes: Iterable[str]) -> Alarm:
    """Rules v1.2. Two signals make a warning; if one of them is an ask, it's red.

    - red, "ask": an ask (A5, A6, A7, A11) together with any other signal;
    - red, "digital-arrest opening": authority + threat + isolation (A1 + A2 + A4), before any ask;
    - amber, "two flags": any two pressure or lure signals;
    - never on one signal alone.
    """
    found = frozenset(yes) & BY_ID.keys()
    asks = found & ASKS
    if asks and len(found) >= 2:
        return Alarm(Level.RED, "ask", found)
    if DIGITAL_ARREST_OPENING <= found:
        return Alarm(Level.RED, "digital-arrest opening", found)
    if len(found & FLAGS) >= 2:
        return Alarm(Level.AMBER, "two flags", found)
    return Alarm(Level.NONE, "", found)
