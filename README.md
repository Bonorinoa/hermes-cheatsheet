# Hermes Cheatsheet

Title-bar cheatsheet for Hermes Desktop. Describe what you want to do and it
points to a real command or a cited passage. Commands and plugins are live from
this gateway. Practices retrieves cited passages from this Hermes install's docs.

## Intent search

Type a situation ("ask a question without interrupting the model") and the
Commands tab shows a **Suggested** block: a curated map of phrases to command
ids, plus cited passages retrieved from the docs index on your own words.
Nothing is generated — every suggestion is either a command that exists in this
gateway's `commands.catalog` or a passage copied from this install's docs.

The map is data (`cheatsheet_intents.py`) served by the plugin's local
`/suggest` route. Suggested command ids are validated against the live catalog
before render; unknown ids are dropped. If the backend half is disabled, the tab
falls back to plain filtering — no fake suggestions.

## What this plugin reads

- It reads `website/docs` next to the installed `hermes_cli` package and returns copied passages. It does not send those files anywhere.
- It does not fetch GitHub, Reddit, or X at runtime. Issue excerpts in `community.json` were copied at release time.
- It does not update its own files. Code updates are `hermes plugins update cheatsheet` after a reviewed catalog pin.
- It registers no tools and asks for no environment variables.

## Install

```bash
hermes plugins install Bonorinoa/hermes-cheatsheet
hermes plugins enable cheatsheet
```

Then enable **Cheatsheet** in Settings → Plugins and run ⌘K → **Reload desktop plugins**.

If you previously hand-copied a plugin to `~/.hermes/desktop-plugins/cheatsheet/`,
delete that folder first: a package install never overwrites a marker-less
standalone plugin.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pytest fastapi
.venv/bin/python -m pytest
```
