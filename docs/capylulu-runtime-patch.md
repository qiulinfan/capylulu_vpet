# CapyLulu Runtime Patch

The pet package can only provide `pet.json` and `spritesheet.webp`. Timing and
state transitions are controlled by the Codex avatar runtime bundled in
`app.asar`, so the advanced CapyLulu behavior lives in a local runtime patch.

The patch changes only `webview/assets/codex-avatar-*.js` inside `app.asar`:

- Idle speed changes from the Codex default `6x` base frame durations to `4x`,
  which makes idle about 1.5x faster.
- While the avatar state remains `idle`, the runtime counts completed idle
  loops.
- After every 5 completed idle loops, it randomly plays one of:
  `running` (dance), `idle` (music/listening), or `waiting` (hug plush).
- After 15 completed idle loops with no state change, it loops `failed`, which
  is the sleep row for CapyLulu.

The patcher preserves the original asar layout. It copies `app.asar`, appends
the patched avatar JS, and updates the asar header entry for that single JS
file. This avoids unpacking and repacking native/unpacked Electron resources.
If the updated header would otherwise grow past the original asar header size,
the patcher removes the optional integrity metadata for that one avatar JS
entry and leaves the rest of the archive unchanged.

## Check Current State

```powershell
node tools/patch-capylulu-runtime.mjs --check
```

## Build A Patched Archive Copy

```powershell
node tools/patch-capylulu-runtime.mjs --output "$env:USERPROFILE\.codex\capylulu-runtime-backups\app.asar.capylulu-idle-v1.patched"
```

## Apply To Codex App

```powershell
node tools/patch-capylulu-runtime.mjs --apply
```

On Microsoft Store / MSIX installs, `C:\Program Files\WindowsApps` is usually
not writable from a normal shell. In that case the command still writes a
patched archive copy and reports that installation was blocked by ACLs. Run the
same command from a shell that can write the Codex package directory, then
restart Codex.

## Restore

When `--apply` succeeds, the script creates a backup under:

```text
%USERPROFILE%\.codex\capylulu-runtime-backups
```

Restore the newest backup with:

```powershell
node tools/patch-capylulu-runtime.mjs --restore
```
