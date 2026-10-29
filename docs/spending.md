# Spending: three layers before any card is charged

The Meta credits are $150. Paid calls stop at **$100**, so $50 is never touched and the card on the account is never charged. Each layer below can stop spending on its own.

## 1. Our own count, before every call ([`budget.py`](../src/teesrakaan/budget.py))
- Every paid call reserves its worst-case cost before it's sent, in a SQLite ledger that every process shares. It's refused if spent + reserved + this call would pass $100. Config can lower the stop, never raise it.
- A call whose outcome is unknown (timeout, dropped connection, server error) keeps its worst case as spent. Nothing is retried automatically. Spark replies are cached, so a replay costs nothing.
- Live listening reserves a whole 6-minute session up front and settles it to its real length at the end.
- The web page spends from its own **$5 share**, so visitors can't use up the evaluation's budget.
- A test fails if any module reads the API key without reserving through the ledger.

## 2. Meta's own meter ([`budget.py`](../src/teesrakaan/budget.py))
dev.meta.ai has no usage API and no spend limit (its pricing page, Oct 29), so our count could be wrong without anything noticing. The Billing page is read by hand and recorded:

```bash
.venv/bin/teesrakaan meter --credits-left 150.00 --balance-inr 0 --source "Billing, 14:30 IST"
```

Every paid call is refused while any of these holds:
- Meta's meter has never been read.
- The last reading showed a balance above ₹0. That means the card is being billed, so everything stops.
- The last reading is more than 24 hours old, or more than **$10** has been spent since it was taken.
- Meta's meter showed more than $5 spent beyond our count. That means something outside the ledger is spending, such as another machine or a leaked key. Calls stay refused until the cause is found and the reading is recorded again with `--drift-ok`.

Whichever count is higher, ours or Meta's plus what we've spent since, is the one held against the $100 stop. `teesrakaan budget` shows both counts, and whether paid calls are allowed and why.

## 3. Outside the ledger
- **A date:** paid calls end on Nov 5 at 00:00 IST (`PAID_UNTIL`), before the credits' 10-day window can close. After it, any call would go to the card.
- **The key** lives only in `.env`, which git ignores. A local pre-commit hook refuses any commit that contains the key or a key file. The key is revoked once the final runs are done.
- **The card:** in India, an automatic card debit needs a notice at least 24 hours before it (RBI's e-mandate rules). That notice is the last point at which a charge can be stopped at the bank.
- **The free credits:** Billing says content sent while using them "may be used for product improvement". So the evaluation sends only public FTC recordings and re-enactments recorded for this project. Donated calls stay local, as the [judge prompt](judge-prompt.md) already requires until zero data retention is confirmed.
