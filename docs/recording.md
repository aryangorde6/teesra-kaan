# Recording the re-enactments

Version 1, Oct 28, 2026. How the IN-scam and IN-genuine calls are recorded, so the test sounds like the real use: a call on speakerphone, heard by a laptop or phone in the same room.

## Who records what
- **Scripts:** [`eval/scripts/in-scam.json`](../eval/scripts/in-scam.json) (40) and [`in-genuine.json`](../eval/scripts/in-genuine.json) (30). The dev/test split is fixed in [`eval/scripts/split.csv`](../eval/scripts/split.csv) (28 dev, 42 test).
- **Voices:** Aryan and friends or family who agree in writing (below). Any gender can play any role; change the verb forms to match (bol raha / bol rahi).
- **Order:** the 28 dev scripts first (Thu Oct 29), then the 42 test scripts (by Fri Oct 30).
- **Test recordings are kept away from tuning.** The person tuning prompts and rules doesn't open or listen to them until the freeze (Sun Nov 1, 12:00 IST).

## Setup (about 2 minutes per call)
1. Two phones. The "caller" phones the "listener".
2. The listener puts the call **on speaker** and lays the phone on a table.
3. A laptop or a third phone, about an arm's length away, **records the room** (Audacity, or any voice recorder). This is what Teesra Kaan will hear.
4. A normal room: fan on is fine, no music.
5. Start the recording, then dial. Stop the recording after the call ends.

## Acting
- Read the card once. Then **say each line in your own words**, in order. Don't read word for word: real callers don't, and a test that only works on the script's exact words is worthless.
- Keep the made-up names, numbers, amounts and IDs.
- Lines marked "recorded voice" are said flat, like an automated message. "A second voice" means another person takes over the call, if there's one available; otherwise the same caller changes tone.
- The listener can react naturally (hesitate, ask "who is this?"), but shouldn't add new scam content or change how the call ends.

## Files
- Name each file by its script ID: `IS07.m4a`, `IG21.wav`.
- Put dev recordings in `data/recordings/dev/` and test recordings in `data/recordings/test/` (both gitignored).
- After each session, fill the labelling sheet for the **dev** calls ([labelling.md](labelling.md)): `t0` and `t_ask` by listening. Test calls are labelled the same way, by Aryan, any time before the test run.

## Consent (each voice, once, in writing; a WhatsApp message is fine)
> I agree that my voice, in re-enacted calls for the Teesra Kaan project, may be used to test the system and may be shown in its demo video. The calls are acted from scripts; they are not real.
> ☐ The recordings may also be published with the project's code as test data. (Leave unticked to keep them private.)
> Name, date.

Recordings without the second tick stay private, like donated calls.

## Also recorded by Aryan (Fri Oct 30)
- **The warning lines** in Hindi, Marathi and English (`HEADLINE`, `ACTION` and the fact lines in [`src/teesrakaan/messages.py`](../src/teesrakaan/messages.py)), after a native speaker has checked the wording. These play aloud when the screen turns amber or red.
- **Two or three video-only calls,** separate from the test set, for the demo video (shot 6 of the shot list). The written demo calls in `examples/calls/` are ready for this.
