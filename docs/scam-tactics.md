# Scam-call tactics in India: what Teesra Kaan listens for

Version 1, Oct 28, 2026. Built from public advisories by Indian government bodies and regulators. Each pattern lists its source. Patterns marked *source to add* are well known but not yet tied to an official advisory, and must be before they appear in the demo.

## The signals

Teesra Kaan doesn't ask a model "is this a scam?". After each caller turn, Muse Spark answers a fixed set of yes/no questions about what the caller has said so far, and quotes the words that support each yes. Fixed rules (below) turn those answers into a warning.

| ID | Question about the caller | Example words |
|---|---|---|
| **A1 Authority** | Claims to be police, CBI, ED, customs, narcotics, a court, RBI, TRAI, DoT, or a bank or government official? | "Main CBI se bol raha hoon", "Mumbai crime branch" |
| **A2 Threat** | Threatens arrest, a case, a fine, or blocking an account, card or SIM? | "Aapke naam pe FIR hai", "number 2 ghante mein band ho jayega" |
| **A3 Urgency** | Demands action right now or within a deadline? | "abhi ke abhi", "within two hours" |
| **A4 Isolation** | Tells you to keep it secret, not to tell family, stay on the call or video, or go somewhere alone? | "kisi ko mat batana", "call disconnect mat karna" |
| **A5 Secrets** | Asks for an OTP, PIN, CVV, password, or Aadhaar, PAN or card number? | "OTP bata dijiye" |
| **A6 Money** | Asks you to pay or move money (a fine, a "verification" deposit, a "safe" or "RBI" account, a UPI request)? | "verification ke liye paise transfer karo" |
| **A7 Remote control** | Asks you to install an app, share your screen, or open a link? | "AnyDesk download karo" |
| **A8 Channel switch** | Moves you to a video call, WhatsApp or Skype? | "Skype pe aaiye, video on rakhiye" |
| **A9 Parcel** | Says a parcel or courier in your name holds illegal items? | "aapke parcel mein drugs mile hain" |
| **A10 Press-a-key** | An automated voice says to press a key to talk to an officer? | "press 9" |
| **A11 PIN to receive** | Says you must enter a UPI PIN or approve a request to *receive* money? | "PIN daalo, paise aa jayenge" |

**Draft alarm rules** (tuned on the development set only, then frozen; see `evaluation-rule.md`):
- **Danger (red):** an ask (A5, A6, A7 or A11) together with pressure (A1, A2, A3 or A4).
- **Danger (red), before any ask:** authority plus threat plus isolation (A1 + A2 + A4). That's the "digital arrest" opening, which moves to money later.
- **Caution (amber):** any two of A1, A2, A3, A8, A9 or A10.
- **Never on one signal alone.** A real bank's fraud team says "bank" and may say "urgent", but never asks for an OTP or PIN.

## The patterns

| # | Pattern | How the call goes | Signals | Source |
|---|---|---|---|---|
| 1 | **"Digital arrest"** | A "police", "CBI", "ED" or "customs" officer says you're linked to a crime (drugs, money laundering, Aadhaar misuse). They move you to a video call, keep you on it, forbid you to tell anyone, show fake documents or uniforms, then demand money "for verification" | A1 A2 A4 A8 → A6 | I4C via PTI, Oct 2024: "CBI/Police/Custom/ED/Judges DO NOT arrest you on video call" ([Tribune](https://www.tribuneindia.com/news/india/cbi-ed-dont-nab-via-video-calls-advisory-to-curb-digital-arrest/), [Deccan Herald](https://www.deccanherald.com/india/amid-rise-in-digital-arrest-cases-indian-cyber-crime-coordination-centre-issues-advisory-for-citizens-3221509)). Prime Minister, Mann Ki Baat, Oct 27, 2024: no investigating agency enquires by phone or video call, and there is no "digital arrest" in law; "Stop – Think – Take Action" ([Organiser](https://organiser.org/2024/10/27/262496/bharat/mann-ki-baat-pm-modi-warns-about-digital-arrest/)). Gujarat Police awareness note ([PDF](https://gujaratcybercrime.org/Digital_Arrest_Awareness_Watermarked.pdf)) |
| 2 | **Courier or customs parcel** | An automated "FedEx" or "DHL" call says a parcel in your name was seized, then puts you through to a "customs officer". It's usually the opening of pattern 1 | A9 A10 → A1 A2 | Same I4C coverage; first-person account in [The South First](https://thesouthfirst.com/opinion/why-a-video-call-with-a-scammer-could-put-you-at-risk-a-reporters-first-person-account) |
| 3 | **"Your number will be blocked"** | An automated voice says TRAI or DoT will disconnect your number within 2 hours: "press 9". The caller then asks for Aadhaar or OTP details, or moves into pattern 1 | A1 A2 A3 A10 → A5 | DoT advisory (PIB, May 2024): DoT and TRAI don't authorise anyone to make such calls; report on Chakshu, Sanchar Saathi ([Sanchar Saathi PDF](https://www.sancharsaathi.gov.in/SancharSaathiDocuments/ImportantDocuments/Threatening%20fake%20call%20for%20disconnection%20of%20mobile%20connections.pdf), [Storyboard18](https://www.storyboard18.com/how-it-works/dot-warns-against-fake-calls-threatening-disconnection-of-mobile-numbers-31548.htm)) |
| 4 | **KYC update or account block** | A "bank" caller says your account or card will be blocked unless you update KYC now, then asks for card details, an OTP or a link click | A1 A2 A3 → A5 A7 | RBI, "BE(A)WARE" booklet on fraudsters' methods, 2022 ([PDF](https://website.rbi.org.in/documents/87730/39016390/BEAWARE07032022.pdf)): genuine banks never ask for a password, card details, CVV or OTP |
| 5 | **"Enter PIN to receive money"** | The caller promises a refund, prize or "wrong transfer" return and asks you to approve a UPI request or enter your PIN | A6 A11 | NPCI UPI Safety Shield: the UPI PIN is needed only to send money, never to receive it ([NPCI](https://npci.org.in/what-we-do/upi/upi-safety-shield)) |
| 6 | **Fake customer care or refund** | "Customer care" for an app, bank or courier asks you to install a screen-sharing app or open a link to get a refund | A1 A7 → A5 A6 | RBI BE(A)WARE (screen-sharing apps, fake helplines) |
| 7 | **Family emergency** | "Your son has been arrested" or "had an accident": money needed right now, don't call anyone. Sometimes a cloned voice | A2 A3 A4 → A6 | *Source to add (police advisories on voice-clone calls)* |
| 8 | **Electricity disconnection** | "Your power will be cut tonight because the bill isn't updated; call this officer" | A1 A2 A3 → A6 A7 | *Source to add (MSEDCL or other discom advisory)* |
| 9 | **Prize, lottery or KBC** | You've won, but must pay a fee or tax first | A6 | RBI BE(A)WARE (lottery fraud) |

**Where to report**, as the warning and the report pack say:
- money lost: **1930**, or **cybercrime.gov.in**;
- suspected fraud calls: **Chakshu on Sanchar Saathi** (sancharsaathi.gov.in).

## What genuine callers do (hard negatives for testing)
A genuine caller may sound alarming but never asks for secrets or money on the call. These must **not** trigger red:
- a real bank fraud alert ("did you make this transaction? If not, call the number on your card");
- a courier delivery call;
- a family member asking for money calmly, with no secrecy;
- a hospital or school call;
- a legal telemarketing call.
