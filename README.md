# Unlist

Local agent for removing your records from people-search sites and data brokers.

This is not Incogni. There is no account, no authorized-agent SaaS, and no one else holds your file. The playbook plus a CLI generate the work. You — or a Grok Bot driving a browser — submit the forms.

## What it does

- Holds a playbook of high-impact brokers (`data/brokers.json`)
- Builds search queries from your identifiers
- Writes deletion / suppression letters
- Tracks sent / verified / completed / reappeared on disk
- Hands a Grok Bot a standing procedure (`BOT.md` + skill)

It does **not** submit forms by itself. Form-fill and CAPTCHA still need a browser session.

## Setup

```bash
cd unlist
cp profile.example.json profile.json
# edit profile.json
python3 scripts/unlist.py init
```

## Daily loop

```bash
python3 scripts/unlist.py queries      # search strings
python3 scripts/unlist.py queue --open
python3 scripts/unlist.py next
python3 scripts/unlist.py letter spokeo --url 'https://www.spokeo.com/...'
python3 scripts/unlist.py log spokeo sent --url 'https://www.spokeo.com/...'
python3 scripts/unlist.py status
```

Custom site the playbook does not know:

```bash
python3 scripts/unlist.py custom 'https://example.com/profile/you'
python3 scripts/unlist.py log-custom 'https://example.com/profile/you' sent
```

Authorization text if a broker demands an agent letter:

```bash
python3 scripts/unlist.py auth
```

## Grok Bot

1. Create a Bot.
2. Paste `BOT.md` as its identity.
3. Copy `.grok/skills/unlist/` into the Bot's skills path (or `~/.grok/skills/unlist/`).
4. Give it this repo as the working directory.
5. First message: `Start Unlist. Load profile.json and run wave 1.`

Weekly routine: `Run unlist status. Do follow-ups and rechecks. Do not contact brokers that still need a phone code without me.`

## Waves

| Wave | What |
|---|---|
| 0 | California DROP, only if in scope |
| 1 | Spokeo, Whitepages, BeenVerified, PeopleConnect, TruePeopleSearch, FastPeopleSearch, Radaris, MyLife |
| 2 | Clone people-search sites |
| 3 | Acxiom/LiveRamp, Epsilon, LexisNexis, Oracle, Experian marketing, CoreLogic |

Wave 1 removes most of what a stranger sees in Google. Wave 3 is the pipe that feeds those sites.

## Limits

- Opt-out URLs rot. Re-open the URL before submitting.
- Some brokers require ID, a phone call, or a wet-ink form. The agent prepares; you finish.
- Suppression is not deletion of every internal file, and records come back. That is why `recur_days` exists.
- This is not legal advice and not a consumer-reporting dispute (FCRA).

## Layout

```
profile.json              # gitignored identifiers
data/brokers.json         # playbook
data/state.json           # gitignored tracker
templates/                # letter + authorization
scripts/unlist.py         # CLI
BOT.md                    # Grok Bot identity
.grok/skills/unlist/      # skill pack
```
