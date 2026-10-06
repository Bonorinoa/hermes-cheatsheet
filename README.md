# Hermes Cheatsheet

Title-bar cheatsheet for Hermes Desktop. Commands and plugins are live from this
gateway. Practices retrieves cited passages from this Hermes install's docs.

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
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest
```