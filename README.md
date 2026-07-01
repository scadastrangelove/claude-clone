# claude-clone

Run a **second, fully independent Claude Desktop** on macOS — a different account,
its own login and history, a distinct Dock icon — side by side with your main one.

No second download, no full app copy: it wraps the *same* signed binary and just
points it at a separate profile.

![Two Claude Desktop icons in the Dock](docs/demo.gif)

## Why it isn't trivial

Claude Desktop stores your session in one fixed profile directory
(`~/Library/Application Support/Claude`). Opening a second window — or even
`open -n` — reuses that profile, so it's always the same account.

The app **does** support an alternate profile, but not via a CLI flag. It reads
an environment variable:

```js
if (process.env.CLAUDE_USER_DATA_DIR) {
  app.setPath("userData", process.env.CLAUDE_USER_DATA_DIR)
}
```

Two extra gotchas this repo handles for you:

1. **The Rosetta trap (Apple Silicon).** The binary is universal (x86_64 + arm64).
   Launched the naive way, the second instance can start under Rosetta as
   *translated x86_64* — Chromium then pins a CPU core near 100% and feels
   painfully slow. The launcher forces `arch -arm64` **and** sets
   `LSArchitecturePriority`/`LSRequiresNativeExecution` in the wrapper's plist.
2. **Single-instance lock.** It's per-profile, so a different `CLAUDE_USER_DATA_DIR`
   is genuinely a separate instance that coexists with your main one.

## Install

```bash
git clone https://github.com/<you>/claude-clone && cd claude-clone
chmod +x install.sh sync-sessions.sh
./install.sh -n "Claude Work" -b W --copy-settings
```

Then launch **Claude Work** from Spotlight or `/Applications` and sign in with
your second account. Drag it to the Dock to pin it.

Want your existing Claude Code sessions in the new instance from the start? Add
`--copy-sessions`:

```bash
./install.sh -n "Claude Work" -b W --copy-settings --copy-sessions
```

### Options

| Flag | Meaning | Default |
|------|---------|---------|
| `-n NAME` | Instance / app name | `Claude Work` |
| `-b LETTER` | Badge letter drawn on the icon | first letter of `NAME` |
| `-H HUE` | Hue shift (0–255) for the icon background | `150` |
| `-s PATH` | Source `Claude.app` | `/Applications/Claude.app` |
| `--copy-settings` | Clone UI prefs (`claude_desktop_config.json`) | off |
| `--copy-sessions` | Copy your Claude Code session list if present, else start fresh | off (fresh) |

The icon generator needs Pillow (`pip3 install Pillow`); without it you still get
a working instance, just with the stock icon.

## What gets created

```
/Applications/<NAME>.app                         # thin wrapper (execs the real binary)
~/Library/Application Support/Claude-<slug>/      # isolated profile (login, history)
```

Your main install is never touched.

## Bringing over Claude Code sessions

Claude Code **transcripts** live globally in `~/.claude/projects` and are shared
by every instance. But Claude Desktop keeps a **per-profile, per-account index**
of them, so a fresh profile shows an empty Claude Code list even though the
transcripts exist.

You can pull the index in at install time with `--copy-sessions` (above), or any
time afterwards with the standalone script:

```bash
./sync-sessions.sh \
  "$HOME/Library/Application Support/Claude" \
  "$HOME/Library/Application Support/Claude-work"
```

Only the account you're logged into displays; other accounts' entries are inert.
Restart the target app afterwards. Note: these lists **don't auto-sync** — re-run
when you want to refresh.

## What is and isn't copied

- **Copied (with `--copy-settings`):** `claude_desktop_config.json` — UI prefs
  only (sidebar mode, toggles, etc.). No credentials.
- **Never copied:** `config.json` (OAuth token cache), cookies, local/session
  storage. That's deliberate — the whole point is a *different* login.
- **Proxy:** if you use a macOS **system** proxy, both instances inherit it
  automatically (Chromium reads system settings). Nothing to configure.

## Uninstall

```bash
rm -rf "/Applications/Claude Work.app"
rm -rf "$HOME/Library/Application Support/Claude-work"   # deletes that profile's login/history
```

## Troubleshooting

**The second instance is slow / a CPU core sits near 100%.**
It's running under Rosetta (translated x86_64). Check:

```bash
sample "Claude Work" 1 | grep 'Code Type'   # want ARM64, not "X86-64 (translated)"
```

Re-run `install.sh` (it forces arm64). If you launched it by hand, make sure the
launcher uses `exec /usr/bin/arch -arm64 …`. Also confirm you didn't tick
*"Open using Rosetta"* in Finder → Get Info on the app.

**Clicking the new app just focuses my main Claude / it's the same account.**
The profile isn't being isolated. Verify the running process actually has the env
var set:

```bash
pid=$(pgrep -f "Claude.app/Contents/MacOS/Claude" | head -1)
ps eww -p "$pid" | tr ' ' '\n' | grep CLAUDE_USER_DATA_DIR
```

If it's empty, you launched the main app, not the wrapper. Launch via
`/Applications/<NAME>.app`. Don't use `open -n` on the original app — that shares
the profile.

**macOS says the app "cannot be opened" / is from an unidentified developer.**
The wrapper is an unsigned local bundle. Right-click → **Open** once, or:

```bash
xattr -dr com.apple.quarantine "/Applications/Claude Work.app"
```

**The Dock still shows the old (identical) icon.**
Icon caches are sticky. Re-run `install.sh`, or:

```bash
rm -rf "$(getconf DARWIN_USER_CACHE_DIR)/com.apple.iconservices.store"
killall Dock
```

If it still lags, log out and back in.

**"Icon: (no Python/Pillow)" — I got the stock icon.**
Install Pillow and re-run: `pip3 install Pillow && ./install.sh -n "Claude Work"`.

**Claude Code session list is empty.**
Expected on a fresh profile — see [above](#bringing-over-claude-code-sessions).
Run with `--copy-sessions`, or `sync-sessions.sh`, then **restart** the instance.

**It broke after a Claude Desktop update.**
An update can move or replace the binary. Just re-run `install.sh` to regenerate
the wrapper against the new build.

## Notes & caveats

- Tested on macOS (Apple Silicon), Claude Desktop 1.17.x.
- The wrapper is an unsigned local bundle that execs the signed Claude binary.
  Gatekeeper may prompt once on first launch — right-click → Open.
- If a Claude Desktop update relocates its binary, re-run `install.sh` to
  regenerate the wrapper.
- Not affiliated with or endorsed by Anthropic. Uses a documented-by-behavior
  env var; could change in a future build.

## License

MIT.
