# Unlist

Take your name off people-search sites with Grok Bot.

## Quick start

Paste this into a Grok Bot:

```
Read https://github.com/shawnyeager/unlist/blob/master/BOT.md and follow it.
```

The Bot clones this repo, submits the opt-out forms, and logs what it sent. It keeps trying until it cannot. It asks you only for the step that blocked it.

## What this repo does

This repo does not submit forms. There is no browser driver. `scripts/unlist.py` never opens a site.

`BOT.md` is the procedure the Bot follows. `data/brokers.json` is the site list. `scripts/unlist.py` writes letters and tracks state so the Bot does not invent brokers, dump extra identity, or lose follow-up dates. `profile.json` stays on the computer and is gitignored. Do not put it in a shared template.

## CLI

Use this if you want to inspect state yourself. The Bot runs the same commands.

```bash
cd unlist
cp profile.example.json profile.json
# edit profile.json
python3 scripts/unlist.py init
python3 scripts/unlist.py queries
python3 scripts/unlist.py queue --open
python3 scripts/unlist.py next
python3 scripts/unlist.py show spokeo
python3 scripts/unlist.py letter spokeo --url 'https://www.spokeo.com/...'
python3 scripts/unlist.py log spokeo sent --url 'https://www.spokeo.com/...'
python3 scripts/unlist.py followup spokeo
python3 scripts/unlist.py status
```

If the playbook does not know the site, treat it as custom:

```bash
python3 scripts/unlist.py custom 'https://example.com/profile/you'
python3 scripts/unlist.py log-custom 'https://example.com/profile/you' sent
```

If a broker demands an authorization letter, print one:

```bash
python3 scripts/unlist.py auth
```

## Waves

| Wave | What |
|---|---|
| 0 | California DROP, only if in scope |
| 1 | Spokeo, Whitepages, BeenVerified, PeopleConnect, TruePeopleSearch, FastPeopleSearch, Radaris, MyLife |
| 2 | Clone people-search sites |
| 3 | Acxiom, LiveRamp, Epsilon, LexisNexis, Oracle, Experian marketing, CoreLogic |

Wave 1 is what a stranger sees in search results. Wave 3 is the pipe that feeds those sites. PeopleConnect covers several Intelius-family sites.

## Limits

- Opt-out URLs rot. Re-open the URL before you submit.
- Some brokers require ID, a phone call, or a wet-ink form. The Bot exhausts every other path first. Then it asks you for that step.
- Suppression is not deletion of every internal file. Records come back. That is why `recur_days` exists.
- This is not legal advice and not a consumer-reporting dispute under the FCRA.
