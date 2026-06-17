# Virtuoso Bridge Lite setup

Updated: 2026-06-17

## Source and Git

- Upstream: https://github.com/Arcadia-1/virtuoso-bridge-lite.git
- Local source: `E:\8bitvcmvirtuoso\virtuoso-bridge-lite`
- Local branch: `main`
- Upstream tracking: `origin/main`
- Current upstream commit: `d11bb3f docs: document direct CLI SKILL execution`

The source directory already existed in the project root, so it was not
overwritten. It has been initialized in place as a Git repository and bound to
the upstream remote. The parent SAR project still tracks the source files.

When running Git commands inside the child repository from the Codex sandbox,
use:

```powershell
& 'C:\Program Files\Git\cmd\git.exe' `
  -c safe.directory=E:/8bitvcmvirtuoso/virtuoso-bridge-lite `
  -C E:\8bitvcmvirtuoso\virtuoso-bridge-lite status
```

## Virtual environment install

- Project venv: `E:\8bitvcmvirtuoso\.venv`
- Python: `E:\8bitvcmvirtuoso\.venv\Scripts\python.exe`
- CLI: `E:\8bitvcmvirtuoso\.venv\Scripts\virtuoso-bridge.exe`
- Package: `virtuoso-bridge==0.7.0`
- Editable project location: `E:\8bitvcmvirtuoso\virtuoso-bridge-lite`

Verification commands:

```powershell
.\.venv\Scripts\python.exe -m pip show virtuoso-bridge
.\.venv\Scripts\python.exe -c "import virtuoso_bridge, sys; print(virtuoso_bridge.__version__); print(virtuoso_bridge.__file__); print(sys.executable)"
.\.venv\Scripts\virtuoso-bridge.exe --help
```

## Project-level skills

The repository provides three agent skills:

- `virtuoso`
- `spectre`
- `optimizer`

They are registered locally as NTFS junctions in both project skill locations:

```text
E:\8bitvcmvirtuoso\.claude\skills\virtuoso  -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\virtuoso
E:\8bitvcmvirtuoso\.claude\skills\spectre   -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\spectre
E:\8bitvcmvirtuoso\.claude\skills\optimizer -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\optimizer

E:\8bitvcmvirtuoso\.codex\skills\virtuoso   -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\virtuoso
E:\8bitvcmvirtuoso\.codex\skills\spectre    -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\spectre
E:\8bitvcmvirtuoso\.codex\skills\optimizer  -> E:\8bitvcmvirtuoso\virtuoso-bridge-lite\skills\optimizer
```

Restarting the agent/session may be needed before newly registered project
skills appear in the available skills list.

`.codex/skills/` is ignored by the parent SAR repository because these entries
are local NTFS junctions; the real skill files live under
`virtuoso-bridge-lite\skills`.

## Resolved bridge profile

Current user-level config file:

```text
C:\Users\Chonghao Chen\.virtuoso-bridge\.env
```

Resolved values:

```text
VB_REMOTE_HOST=192.168.225.132
VB_REMOTE_USER=IC
VB_REMOTE_PORT=65140
VB_LOCAL_PORT=65141
VB_JUMP_HOST is unset
VB_JUMP_USER is unset
VB_PROFILE is unset, so the default profile is used
```

Current `virtuoso-bridge status`:

```text
[tunnel] running
remote host : 192.168.225.132
remote user : IC
local port  : 65141

[daemon] OK - connected to Virtuoso CIW
daemon user: IC
tunnel user: IC
hostname   : IC
Virtuoso   : 6.1.8-64b, build 2018-10-01
workdir    : /home/IC/Desktop/Project
```

## Recommended config additions

Spectre is available on the remote host at:

```text
/opt/eda/cadence/SPECTRE181/bin/spectre
```

This was verified with:

```text
sub-version 18.1.0.077
```

Add this line to `C:\Users\Chonghao Chen\.virtuoso-bridge\.env` if you want
`virtuoso-bridge status`, `license`, and Spectre simulations to find it without
setting a temporary environment variable:

```text
VB_SPECTRE_BIN=/opt/eda/cadence/SPECTRE181/bin/spectre
```

On this Windows SSH setup, the bridge reports a ControlMaster warning:

```text
ControlMaster failed on 192.168.225.132 (getsockname failed: Not a socket)
```

It is non-fatal. To silence it, add:

```text
VB_DISABLE_CONTROL_MASTER=1
```

Temporary verification without editing `.env`:

```powershell
$env:VB_SPECTRE_BIN='/opt/eda/cadence/SPECTRE181/bin/spectre'
.\.venv\Scripts\virtuoso-bridge.exe status
```

Expected result:

```text
[spectre] OK
path : /opt/eda/cadence/SPECTRE181/bin/spectre
```
