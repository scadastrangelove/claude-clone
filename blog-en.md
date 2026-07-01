# Two Claude Desktops on one Mac: a small, practical one

*By Sergey Gordeychik*

I usually write about heavier stuff — decision-support systems, the coming
crisis in how professions reproduce themselves, and assorted AI dread. Today,
something short and useful: how to run **two Claude Desktop apps on one macOS**,
under different accounts, at the same time — so personal and work never mix.

## The problem

Claude Desktop keeps your session in a single fixed profile
(`~/Library/Application Support/Claude`). A second window is the same account.
Even `open -n` reuses the profile. But I want a personal and a work account side
by side without logging in and out ten times a day.

## The idea

It turns out the app can run against a different profile — not via a CLI flag,
but via an environment variable. Right there in the Electron main process:

```js
if (process.env.CLAUDE_USER_DATA_DIR) {
  app.setPath("userData", process.env.CLAUDE_USER_DATA_DIR)
}
```

So you can wrap the **same signed binary** in a tiny `.app` launcher that sets
`CLAUDE_USER_DATA_DIR` to a separate folder. No second download, no 400 MB copy —
just a different profile. Claude's single-instance lock is per-profile, so two
profiles are two real instances running happily side by side.

## Two traps I hit

**1. The Rosetta trap.** The binary is universal (x86_64 + arm64). Launched the
naive way, the second instance started under Rosetta as *translated x86_64* —
and Chromium pinned a CPU core near 100%, everything crawling. Diagnosis is
instant:

```bash
sample "Claude Work" 1 | grep 'Code Type'
# Code Type: X86-64 (translated)   ← there it is
```

Fixed by forcing arm64 in the launcher (`exec /usr/bin/arch -arm64 …`) plus
`LSArchitecturePriority` / `LSRequiresNativeExecution` in Info.plist. After that:
`Code Type: ARM64`, CPU back to normal.

**2. Claude Code sessions.** The transcripts live globally in
`~/.claude/projects` and are shared by everything. But the desktop keeps a
**per-profile, per-account index** of them
(`claude-code-sessions/<account>/<org>/…`). A fresh profile can't see that index,
so the list looks empty even though the transcripts are right there. Copy the
relevant account's folder over and the sessions come back.

## How to install

I packaged it into a small repo — **claude-clone** — with a one-command deploy:

```bash
git clone https://github.com/<you>/claude-clone && cd claude-clone
chmod +x install.sh sync-sessions.sh
./install.sh -n "Claude Work" -b W --copy-settings --copy-sessions
```

The script builds the `.app` wrapper, an isolated profile, and a **distinct icon**
(recolored background + a letter badge in the corner) so the two Claudes don't
blur together in the Dock. `--copy-sessions` brings over your existing Claude Code
sessions (or starts fresh if there are none). Then launch "Claude Work", sign in
with the second account, done.

Deliberately **not** copied: login tokens, cookies, local storage — the whole
point is a different account. If you use a macOS **system** proxy, both instances
inherit it automatically (Chromium reads system settings).

## Result

Five minutes of setup and two independent Claudes live side by side — personal
and work, each with its own history, its own icon, and proper native speed.

**Scripts / repo:** https://github.com/scadastrangelove/claude-clone

*P.S. This is an unofficial trick based on app behavior (the
`CLAUDE_USER_DATA_DIR` env var) and may change in future versions. As of writing
it works on Apple Silicon, Claude Desktop 1.17.x.*
