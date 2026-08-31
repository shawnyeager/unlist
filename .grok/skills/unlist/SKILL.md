---
name: unlist
description: Remove personal listings from data brokers and people-search sites. Use when the user says unlist, opt out, data broker, Incogni-style removal, delete my info from Spokeo or Whitepages, or wants a scan-and-remove loop.
metadata:
  version: "0.1.0"
  type: workflow
---

# Unlist

Run the local Unlist agent in this repo. Read `BOT.md` and `data/brokers.json` before acting.

## When to use

User wants their name, phones, emails, or addresses pulled off people-search sites or data brokers. Also use for a pasted profile URL.

## Inputs

- `profile.json` at repo root. If missing, copy `profile.example.json` and collect identifiers. Never commit `profile.json`.
- Optional listing URL.

## Procedure

1. Load profile. Confirm name, aliases, cities, state, CA-resident flag.
2. If California resident, flag wave 0 (`ca-drop`) before busy-work on individual CA-registered brokers.
3. Run `python3 scripts/unlist.py queue --open` and `next`.
4. For the current broker, search the site with name + city. Confirm the record is the user.
5. Prefer the official opt-out form in the playbook. Generate a letter only when the method is email or the form is broken.
   - `python3 scripts/unlist.py letter BROKER --url LISTING`
   - `python3 scripts/unlist.py custom URL`
6. Stop for CAPTCHA, phone verification, and ID upload. Hand the user the exact page and fields.
7. Log every state change.
   - `python3 scripts/unlist.py log BROKER sent --url LISTING`
   - completed / failed / reappeared as they happen
8. Return the next broker. Do not spray twenty forms in one turn unless asked.

## Validation

- Listing URL matches the user's identifiers, not a homonym.
- Opt-out URL still loads. If it 404s, search the site privacy policy and update the playbook note.
- State file updated after each real action.

## Return

For each broker: id, listing URL, opt-out URL, what was submitted, what the user must still click, log command, next id.

## Approvals

Required before sending email from the user's inbox, uploading ID, or calling a broker phone line. Form submits the user can watch may proceed when they say go.
