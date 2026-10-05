# M1 isolation repair: design of an enforced default-deny test runner

Date: 2026-10-04. Status: **proposal only.** This file authorizes no code, no test run, no workflow change and no application
change. It contacts no hosted service. **Finding M1 stays open** (`docs/KNOWN_ISSUES.md`, the entry of 2026-10-04) until a separately
authorized repair is proven. The decision owner accepts or refuses the design. A review of it is a prerequisite.

**Revision 2 (2026-10-04).** Revised after the review of pull request 90, which tested the mechanism with live local probes and broke three claims of
revision 1. (1) A filesystem Unix-domain socket crosses a network namespace, so Layer 1 is now a network namespace **plus a mount namespace**. (2) A test
process must not run as real root, and `sudo` drops the environment. (3) The loopback interface is **down** in a new namespace. The revision also
completes the list of audited events, removes the `--collect-only` exemption, specifies the declared-absent mechanism and its limits, and
adds the missing allowlist rules and canaries. The first version stays in the git history. This is still a proposal.

**Revision 3 (2026-10-04).** Revised after the re-review of revision 2, which reproduced the earlier fixes and found two wording defects in how the spec handles loopback and
root under the mechanism that it names, plus six weaknesses. (1) Under `bwrap`, loopback is **already up** and `ip link set lo up` **fails**, so the loopback proof is a self-connect
inside the final sandbox and the spec names which layer brings loopback up. (2) Under `unshare -rn` the uid is 0 and cannot be switched, so the root rule is stated as "no capabilities,
`NoNewPrivs=1`, and the uid of the invoking user where the route preserves it", separately for each route. The other points: the mount namespace is an **allow-list** (`--tmpfs /`
with explicit binds), a short run-directory path for the 108-byte socket limit, `--unshare-pid`, the audit events `socket.sendmsg` and the `os.spawn*` pair, explicit DSN hosts, and
which file the exit 87 check reads. The earlier versions stay in the git history. This is still a proposal.

**Revision 5 (2026-10-04).** Revised after the re-check of revision 4, which closed all six earlier findings and reproduced the new claims, and found four mandatory gaps. (1) In the plain route the test process is **uid 0**, so
the synthetic `passwd` line must name the uid that the process has in that route and not "the invoking uid". (2) A loopback service cannot be started before the namespace: the order of events now has **outside services** and **inside services**, and an
in-sandbox launcher starts the stub. (3) **`AF_VSOCK`** (and other socket families) is a route out of a network namespace on a virtual machine: the design adds a seccomp filter, a guard rule and a minimal `/dev`. (4) The **`sudo` route** is marked
**unverified**, with its own stop condition. The optional items are recorded as residue in the pull request. The earlier versions stay in the git history. This is still a proposal.

**Revision 4 (2026-10-04).** Revised after the third review, which found the design sound and eight gaps in the sandbox that it describes. This revision (1) adds a **synthetic `/etc`** (`hosts`,
`nsswitch.conf`, `passwd`) to the allow-list, because an empty root has none, and the DSNs name a **`user=`** explicitly; (2) binds the **base interpreter** wherever it lives, with a preflight run inside the sandbox;
(3) specifies the **mount allow-list procedure of the plain `unshare` route** (mounts are built before the capability drop; it needs a pid namespace to mount `/proc`); (4) makes the capability proof
**discriminating** (it must be able to fail); (5) makes section 6 and decision 9 agree with the route-specific privilege and loopback rules, and (6) states that the refusal of `nsenter` comes from the user-namespace boundary.
The new claims were checked with local probes only (section 4.1). The earlier versions stay in the git history. This is still a proposal.

Pins: DataForge `origin/master` `ca7ce99625bdecbf465022b6005a97e749f3ee88`. Line numbers are for that commit and can drift.
Nothing here was measured by running the DataForge suite. The only things that were run are local capability probes (section 4.1), which used no network and imported no DataForge code.

## 1. The requirement

The decision owner ruled on 2026-10-04 that a future test authorization needs **network isolation that prevents hosted-service
access and permits only explicitly identified local test services**, and that overriding one URL or deselecting two tests does not
prove isolation of the whole suite. The preparation request adds: cover child processes and redirects; application-level URL overrides
alone are insufficient; establish isolation **before application imports and test collection**; make blocked network attempts **visible**
and not ordinary skips; return the exact files, the mechanism, the allowlist, the failure behavior and the regression evidence.

## 2. Facts that shape the design (verified at the pin unless marked)

| Fact | Where |
|---|---|
| Two independent hosted defaults. Both are computed at import time. Fixing one does not change the other. | `app/config.py:107` and `app/utils/embeddings.py:25-26` (`NEUROFORGE_URL`); `app/config.py:124` (`SUPABASE_API_BASE`) |
| `tests/conftest.py` sets four variables with `setdefault` (database URL, startup flag, secret key, OpenAI key) and **then imports `app.database` and `app.main` at line 30 and after**. `setdefault` does not overwrite a variable that the shell already exports. | `tests/conftest.py:19-31` |
| CI exports `DATAFORGE_DATABASE_URL` for a local Postgres service. It sets neither `NEUROFORGE_URL` nor `REDIS_URL`. It has no Redis service. | `.github/workflows/test.yml:28-36` |
| `load_dotenv()` runs at import time at five sites and walks up the directory tree for a `.env`. | `app/config.py:13`, `app/database.py:22`, `app/main.py:87`, `app/utils/auth.py:14`, `alembic/env.py:17` |
| The two embedding tests swallow the call: `except Exception` then `pytest.skip`. The embedding client turns its own `Exception` into an `HTTPException`. | `tests/test_integration/test_infrastructure_health.py:273-292`; `app/utils/embeddings.py:~186` |
| The Redis helpers swallow every `Exception` on connect and cache a disabled state for the rest of the process. | `app/utils/redis_utils.py:62-76` |
| Many other sites use `except Exception` and can swallow a guard error (`app/utils/embeddings.py`, `redis_utils.py`, `corpus_versioning.py`, `diligence_crud.py`, `resilient_embeddings.py`, `telemetry_client.py`, `main.py`). | Source survey |
| A subprocess inherits the whole environment and runs `alembic/env.py` (with `load_dotenv`). It also runs `CREATE DATABASE` and `DROP DATABASE` on the server of `DATAFORGE_RLS_TEST_POSTGRES_URL` **without checking that the host is local or disposable**. | `tests/test_security/test_rls_public_tables.py:69-108` |
| The render-git-auth tests run `bash` and real `git`, and rely on PATH shims for `curl`, `git` and `openssl`. The real script calls `curl` against GitHub. | `tests/test_render_git_auth.py:28-96`, `scripts/render-git-auth.sh:40-47` |
| Postgres drivers use `libpq`, which opens its own sockets in C. A Python-level socket patch **cannot** see those connections. | Source survey (a property of the driver) |
| `httpx` and `requests` read `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and `NO_PROXY` from the environment. No code sets `trust_env`. `requests` follows redirects by default. The opt-in load test uses `requests`. | Source survey |
| No `pytest-socket`, `respx` or `pytest-httpx` is installed. Pytest is 7.4.3, `pytest-asyncio` 0.21.1 in auto mode. `--strict-markers` is on. `addopts` already holds `--cov`. | `requirements.txt:56-59`, `pytest.ini` |
| The suite needs these local services only: in-memory SQLite (no socket), an optional PostgreSQL (three tests), an optional Redis (the infrastructure tests), and `TestClient` and `ASGITransport` (in-process). | Source survey |
| Loopback defaults exist that point at services which the suite does not start: `http://127.0.0.1:8001` (`app/neuroforge/config.py:17`) and `http://127.0.0.1:8003` (`app/config.py:182`, compression). `DATABASE_URL` is read as a fallback (`app/config.py:59-61`). | Reviewer-verified |
| Redis is probed **outside the tests** too (`app/main.py:459` and `:525`, `app/utils/embeddings.py:53`, `app/utils/corpus_versioning.py:34`). `tests/test_ci_change_scope.py` runs `bash` as a child. `tests/load/test_k6_load.py` imports `requests`. | Reviewer-verified |
| CI needs network egress for non-test steps (pip, `git ls-remote`, the app token, Codecov). The guard must scope to the pytest step. | `.github/workflows/test.yml:90-131` |

## 3. What the runner must stop

1. A TCP or UDP connection from Python code (`httpx`, `redis-py`, `urllib`, `socket`) to any host that is not allowlisted.
2. A DNS lookup of any name that is not allowlisted.
3. A connection by `libpq` (the PostgreSQL driver), which Python cannot see.
4. A connection by a **child process**, Python or not (`alembic`, `bash`, `git`, `curl`).
5. A **redirect** to a name or address that is not allowlisted, from any client, whatever its redirect setting.
6. A **proxy** that carries traffic out of an allowed local address.
7. An ambient variable or a `.env` file that changes a target (`NEUROFORGE_URL`, `REDIS_URL`, `SUPABASE_*`, a database URL).
8. A swallowed error: a blocked attempt that ends as a skip, a disabled cache, or a passing test.
9. A connection through a **filesystem Unix-domain socket** to a service that is not disposable: the system PostgreSQL socket, the Docker socket, an SSH agent, D-Bus.

10. A socket of **another address family** that leaves the namespace by a route that is not IP. `AF_VSOCK` is the case that was probed: a socket of that family **can be created** inside a network namespace (probed here; `/dev/vsock` exists on this machine),
    and on a virtual machine (a hosted CI runner is one) a connection to the hypervisor or host CID can leave the namespace, where the kernel uses the global vsock mode. `libpq`, `curl` and `ctypes` code are not seen by an audit hook. `AF_NETLINK`, `AF_PACKET` and the like are in the same class.

The runner must **permit**: the in-process ASGI app, in-memory SQLite, and the explicitly identified disposable services of section 5.

## 4. The design: four layers

No single layer is enough. Layer 1 is the enforcement. Layers 2 to 4 give defense in depth, diagnostics and visibility.

### 4.1 Layer 1: a network namespace plus a mount namespace

The runner starts the test process in a new **user namespace** with a new **network namespace** and a new **mount namespace**.

- **The network namespace** has only a loopback interface. It refuses every TCP, UDP and DNS route to the outside for every process inside it,
  including children, `libpq` and non-Python programs. **Loopback depends on the route.** In a plain `unshare -rn` namespace the loopback interface is **down**, and the runner must bring it up (`ip link set lo up`, which needs
  iproute2) before it drops privileges. Under `bwrap --unshare-net` the sandbox brings loopback **up itself**, and `ip link set lo up` **fails** there (`Operation not permitted`), so the runner
  must not run it. In both routes the **proof is a self-connect on `127.0.0.1` inside the final sandbox**, run before any **in-sandbox** service starts (the stub). The `iproute2` precondition applies only to the plain
  `unshare` route.
- **The network namespace does not isolate filesystem Unix-domain sockets.** A socket that is a path on the filesystem is reachable from inside the
  namespace. The mount namespace closes that gap.
- **The mount namespace is an allow-list.** It starts from an **empty root** (`--tmpfs /`) and binds in only: the run directory (for the disposable sockets), the repository and the virtual
  environment (read only where possible), the system libraries and the programs that the tests need, the **base interpreter** (below), a **synthetic `/etc`**, `/dev`, `/proc` and a private `/tmp`. `bwrap` is installed on this machine. A deny-list is
  **not** enough: with `--ro-bind / /` and a tmpfs over `/run`, a filesystem socket elsewhere (a test socket outside the run directory was reachable in a probe of the reviewer) stays reachable,
  and so does a socket that a non-Python child such as `psql` or `curl --unix-socket` could use. `/var/run`, `/run`, `/run/user`, `/var/run/postgresql` and the Docker socket are simply absent.
  The sandbox also uses `--unshare-pid`, so that the process cannot reach `/proc/<pid>/root` or `/proc/<pid>/ns/net` of a process outside. The host's permissions deny that today, but they do not
  guarantee it.
- **A synthetic `/etc`.** An empty root has no `/etc`, and three things need one. The runner writes three small files into the run directory and binds each **read only**:
  `hosts` (`127.0.0.1 localhost` and `::1 localhost`, so that `localhost` resolves with no DNS), `nsswitch.conf` (`hosts: files`, so that no resolver runs), and `passwd` (one line for **the uid that the test process has in the route in use**: the invoking user's uid under `bwrap`, **0** in the plain route, where the process is uid 0 inside the user namespace; so that
  `getpwuid` works). There is **no `resolv.conf`**: no name can resolve through DNS inside the sandbox, and a lookup of any other name is a violation of the guard anyway. Without the `passwd` line,
  `pwd.getpwuid` raises `KeyError` for the uid (probed: a line for uid 1000 does not help a process that is uid 0), and `libpq` would have no user name to send. The `user=` of the DSN is the name in that line. The canary reads `getpwuid(os.getuid())` in the final process. The **DSNs also name `user=` explicitly**, so that they do not depend on the lookup.
- **The base interpreter.** A virtual environment's `python` is a symbolic link to a base interpreter, and the base interpreter and its standard library can sit **outside `/usr`** (a `pyenv` tree, `/opt`, the
  `setup-python` tool cache on a hosted runner). The runner resolves `os.path.realpath(sys.executable)`, `sys.base_prefix` and `sys.prefix`, and binds each tree read only at the same path. Before any service
  starts, a **preflight runs `python -c "import ssl, sqlite3, json"` inside the final sandbox**. If it fails, the runner exits 86 and no test starts. On this machine the base interpreter is `/usr/bin/python3.12`, which the `/usr` bind already covers (probed).
- **The environment and the guard.** The runner unsets `PGHOST`, `DOCKER_HOST`, `SSH_AUTH_SOCK` and `DBUS_SESSION_BUS_ADDRESS`. The DSNs that the runner writes **name the host explicitly** (the
  manifest socket directory), so that the empty-host rule can stay strict. The guard (section 4.2) also **denies any `AF_UNIX` path that is not in the manifest**, after `os.path.realpath`
  (which resolves `..` and symbolic links), and it treats an **empty host as the default socket and denies it**.
- **A Unix-socket path is limited to 108 bytes** (`sun_path`). The run directory must be short (for example under `/tmp`), or the runner binds it at a short path such as `/r` inside the sandbox.
- **Abstract Unix sockets** do not cross a network namespace (a probe of the reviewer). The disposable services therefore use **filesystem** sockets that sit in the
  run directory, which the mount namespace binds in.

**Local capability probes (no network used, nothing contacted).**

| Probe | Result |
|---|---|
| `unshare -rn` as a normal user | Works. The only interface is `lo`, and it is **down**. |
| A connection to `192.0.2.1` (RFC 5737 TEST-NET, never routed) inside the namespace | Fails at once with `Network is unreachable` (errno 101). |
| A listener on a **filesystem** Unix socket outside the namespace, a client inside | **The client reached it.** The namespace does not isolate this. (Reproduced here.) |
| Plain `unshare -rn`: `ip link set lo up`, then IPv4 and IPv6 loopback connects | Both worked here. The reviewer's host reported that `::1` gave "Address family not supported", so the guard must not depend on IPv6. |
| An unprivileged process inside the namespace tries `nsenter --net=/proc/1/ns/net` and `setns` | **Refused** (permission denied). (Reproduced here.) The refusal comes from the **user-namespace boundary**: the process holds capabilities only over its own user namespace, and the host network namespace belongs to another one. It does not depend on the uid, and it does not depend on `NoNewPrivs`. |
| A minimal allow-list sandbox under `bwrap` (`--tmpfs /`, read-only `/usr`, symbolic links for `/bin` and `/lib*`, a synthetic `/etc`, the virtual environment, `--proc`, `--dev`, `--unshare-pid`) | Python starts. `getpwuid` returns the synthetic user. `localhost` resolves. The root holds only the bound entries. `CapEff` is zero and `NoNewPrivs` is 1. **Without** the synthetic `passwd`, `getpwuid` raises `KeyError`. (Probed here.) |
| The same allow-list built by hand in the plain route: `unshare -rnmpf --propagation private`, `mount --rbind` into a tmpfs, `pivot_root`, then `setpriv --no-new-privs --bounding-set=-all --inh-caps=-all` | Python starts. `CapEff` and `CapBnd` are zero and `NoNewPrivs` is 1. The uid stays 0 in the user namespace. **Mounting `/proc` fails (`permission denied`) without `--pid --fork`**, because `/proc` must belong to a pid namespace that the user namespace owns. (Probed here.) |
| A hostless `psycopg2.connect` inside the namespace (the reviewer's probe) | It reached this machine's system PostgreSQL over `/var/run/postgresql/.s.PGSQL.5432`, and the server answered (peer authentication failed). A connect to `/var/run/docker.sock` also succeeded. The SSH agent and D-Bus sockets are filesystem sockets as well. |

`kernel.apparmor_restrict_unprivileged_userns` is `1` here, so restrictions exist on this class of host. The runner must **probe at start** and not assume.

**Properties.**

- The system PostgreSQL on `127.0.0.1:5432` is unreachable **by TCP**. Its **Unix socket** is reachable unless the mount namespace hides it. That is why Layer 1 needs both namespaces.
- Disposable services enter the namespace by **explicit means** (section 5): a Unix-domain socket in the run directory, or a loopback process that the runner starts
  inside the namespace.
- If the namespaces cannot be created, or the tool of the chosen route is missing (`bwrap`, or `ip` for the plain route only), or the loopback proof fails, the runner **refuses to run**. It never falls back to an unguarded
  run (section 6). The runner also refuses to run tests with **privilege** (the rule is in the next paragraph).

**Closing the other socket families (item 10 of section 3).** Three measures work together. (a) A **seccomp filter** in the sandbox allows `socket(2)` only for `AF_UNIX`, `AF_INET` and `AF_INET6` and refuses every other family (`EAFNOSUPPORT` or `EPERM`). It is the
only measure that also stops non-Python code. `bwrap` loads it with `--seccomp <fd>`. The plain route has no such option in `setpriv` (version 2.39.3 here), so the **launcher installs the filter with `prctl` after the capability drop**, which needs `NoNewPrivs`, already set. The filter is a fixed
byte string built by a pinned script and checked in with a digest, and **it is not verified here**. (b) The guard refuses the audit event `socket.__new__` for any family outside the three (probed: the event fires with family 40 for `AF_VSOCK`). (c) A **minimal `/dev`**: `null`, `zero`,
`full`, `random`, `urandom`, `tty` and `shm`, and not `/dev/vsock`. `bwrap --dev` provides this. In the plain route the launcher bind-mounts those device nodes one by one, because an unprivileged user namespace cannot create them and `mount --rbind /dev` would bring every host node. If the seccomp filter cannot be
loaded, the runner exits 86. The canary creates a socket of `AF_VSOCK` with a C-level call and expects an error. It creates the socket only and never connects.

**The privilege rule, by route.** The test process must have **no capabilities** (`CapEff` is zero), **`NoNewPrivs=1`**, and it must not be real root on the host. The route decides how that is met:

| Route | uid in the test process | How the rule is met |
|---|---|---|
| `bwrap --unshare-user --unshare-net` | The invoking user's uid (verified: `1000`, `CapEff` zero, `NoNewPrivs=1`) | Met by the sandbox. The check reads `/proc/self/status` and the uid. |
| Plain `unshare -rn` | **0 inside the user namespace**, which is not real root. The uid is unmapped, so `setpriv --reuid` **fails** (`Invalid argument`). | Drop the capabilities and set no-new-privs: `setpriv --no-new-privs --bounding-set=-all --inh-caps=-all`, **after** every mount and the loopback step (they need the capabilities). The check is the capability sets and `NoNewPrivs`, not the uid. (Reproduced: an unprivileged process cannot `nsenter` or `setns` into the host namespace.) |
| `sudo` (only if the kernel needs it) | Real root until the process drops | Create the namespaces under `sudo`, then **switch to the invoking user's uid** and drop the capabilities before the test process starts. The check includes the uid. **Unverified.** This route has **no user namespace**, so the probe and the explanation of the `setns` refusal above (the user-namespace boundary) do **not** apply to it. Real root can `setns` into the host namespace, and only the uid switch, the empty capability sets and `NoNewPrivs` protect. No probe was run, and the mount allow-list procedure for this route is not specified. **Stop condition:** the route is not part of this design until a separate probe and an amendment prove it. If CI needs it, the runner refuses (exit 86) rather than use it. |

**The plain route, step by step.** The runner starts `unshare -rnmpf --propagation private` (user, network, mount and pid namespaces; `--propagation private` keeps every mount inside). Inside, **while it still has
its capabilities**, a helper (1) brings loopback up (`ip link set lo up`), (2) mounts a tmpfs for the new root, (3) `mount --rbind`s each allow-list entry into it (read-only where the list says so, remounted read-only after the bind), (4) mounts `/proc` for the
new pid namespace and bind-mounts the minimal device nodes of the list above one by one, (5) runs `pivot_root` and unmounts the old root, and **only then** (6) drops the capabilities and sets no-new-privs, and starts the test process. The loopback proof and the capability proof run
after step 6, in the final process. This order is required: steps 1 to 5 need `CAP_NET_ADMIN` and `CAP_SYS_ADMIN`. The `bwrap` route does steps 2 to 6 itself.

**The capability proof must be able to fail.** A check that only reads a value that is always zero proves nothing. The runner therefore runs the check **twice**: (a) in a **control** process **before** the drop (plain route), where the
check must report non-zero `CapEff` (here `000001ffffffffff` in the plain route, probed), which shows that the check can detect privilege, and (b) in the final test process, where it must report `CapEff` and `CapBnd` zero and `NoNewPrivs` 1. If (a) shows no privilege, the
check itself is broken, and the runner exits 86.

**Provider for CI (a decision).**
Option A: the runner creates the namespaces **unprivileged** with a user namespace (as above) on the hosted runner, where the kernel allows it. If the
kernel refuses unprivileged namespaces (on Ubuntu 24.04, `kernel.apparmor_restrict_unprivileged_userns=1` can block a plain `unshare -rn`, so expect `bwrap` with an AppArmor profile, or the fallback), the `sudo` route is **not accepted** by this design (unverified, section 4.1): the runner refuses (exit 86), and Option B is the fallback. `sudo` would also reset the environment and drop
`PYTHONPATH`. Whether the hosted runner allows an unprivileged route is **inferred and not verified**. The
runner probes it in a first step.
Option B: a Docker network created with `--internal` (no gateway), with the disposable Postgres container and a test container attached to it. It works where user
namespaces are restricted, and it is heavier. The recommendation is A with a probe, and B as the documented fallback.

### 4.2 Layer 2: an in-process guard that installs at interpreter start

A small module, `netguard`, installs at interpreter start through a `sitecustomize.py` in a directory that the runner puts first on
`PYTHONPATH`. It installs **before any application, HTTP, Redis, database or pytest module is imported**. Two ordering facts apply. `.pth` files run before
`sitecustomize` (the coverage `.pth` imports `coverage` and `socket` first when `COVERAGE_PROCESS_START` is set). Audit hooks do not depend on import
order, so that early import does not weaken the guard, and the early check of section 4.5 lists the modules that matter. The guard reaches **every Python child** that inherits the
environment (the `alembic` subprocess, for example). It does not use `python -I`, which skips `PYTHONPATH`.

It installs:

- a `sys.addaudithook` for the events `socket.connect` (which `connect_ex` also fires), `socket.getaddrinfo`, `socket.gethostbyname`, `socket.gethostbyaddr`,
  `socket.getnameinfo`, `socket.sendto`, `socket.sendmsg`, `socket.bind` (a bind to a non-loopback address is a violation), `subprocess.Popen`, `os.system`, `os.exec` and
  `os.posix_spawn` (`os.spawn*` fires `os.fork` and then `os.exec` in the child, and `socket.gethostbyname_ex` fires `socket.gethostbyname`). The reviewer probed that the asyncio calls `create_connection`, `sock_connect` and `loop.getaddrinfo` fire `connect` and `getaddrinfo`.
  Raw C calls through `ctypes` fire **no** event, which is the same limit as `libpq`;
- wrappers around `psycopg2.connect` and, if it is imported, `psycopg.connect`, that check the target **before** `libpq` is called: a loopback address **and port** that
  are in the manifest, or a Unix-socket path that is in the manifest after `realpath`. An empty host is the default socket and is denied;
- a check at start that no proxy variable is set. If any is set, the guard stops the process.

Every check compares the target with the **allowlist manifest** (section 5). Anything else is a **violation**. `localhost` resolves (through `/etc/hosts` in the
namespace) to `127.0.0.1` and is allowed only on a manifest port. `::1` is treated like `127.0.0.1`, and nothing depends on IPv6 being present.

**A violation is visible, never a skip (section 4.4).** If `violations.jsonl` cannot be written, the guard treats that as fatal and stops the process.

### 4.3 Layer 3: a sanitized, explicit environment

The runner builds the child environment from nothing (`env -i`) plus a short list of variables. It sets, **unconditionally**, the values that the application reads
at import time: `NEUROFORGE_URL`, `REDIS_URL`, `DATAFORGE_DATABASE_URL`, `SUPABASE_API_BASE`, the telemetry variables (empty) and the
RLS and cloud-image test URLs. It removes every proxy variable. Before it starts, it **fails if a `.env` file exists** in the repository
or in a parent directory, because `load_dotenv()` would read it at five import sites.

This layer is **not** the enforcement. A URL override alone proves nothing. It only removes known sources of surprise and makes the manifest the
single statement of what is allowed.

### 4.4 Layer 4: visibility and fail-closed behavior

- **The violation is a `BaseException`.** The class `NetworkIsolationViolation` derives from `BaseException`, so the many `except Exception` sites (the
  embedding client, the Redis helpers, the two tests) cannot turn it into a skip or a disabled cache.
- **A record that cannot be swallowed.** Before it raises, the guard appends one line to `violations.jsonl` in the run directory (target, event,
  process id, a short stack, the test identifier). The **outer runner reads this file after pytest exits** and fails the whole run if it has any line, even
  if every test passed or skipped, and even if a violation was swallowed by code that catches `BaseException`.
- **Per-test conversion.** A pytest plugin compares the count of violations before and after each test. If it grew, the test is reported as
  **failed** with the violation text, even if its outcome was a skip or a pass.
- **Declared-absent services.** A service that the suite probes but that the runner does not provide (for example Redis) is declared in the
  manifest as `declared_absent` with a reason, with an address that cannot answer (a Unix-socket path that does not exist). A probe of it is allowed,
  is logged as `declared-absent probe` and is listed in the report. Tests that use the Redis helper of the suite (`_get_redis_or_skip`) are marked at
  collection and skipped **before any connection**, with the reason `declared absent`, and the skips are enumerated in the report. **Other code also probes Redis**
  (`app/main.py`, `app/utils/embeddings.py`, `app/utils/corpus_versioning.py`). Those probes still happen. They are allowed on the declared-absent path, they are logged,
  and they are listed in the report, so "skipped before any connection" covers only the tests that use the helper. A skip with no declared reason is a defect of the runner.
- **Direct `pytest` is refused.** `tests/conftest.py` calls a gate before it imports `app`. The gate stops the run with exit code 87 unless the
  runner set `NETGUARD_RUN_ID` and the guard is installed. There is no override and **no exemption for `--collect-only`**, because collection imports `app` and every test module.

### 4.5 Order of events (isolation before imports and collection)

1. The runner checks its preconditions: Linux, namespace creation works (a probe), no `.env`, no proxy variable, no stale run directory. Any failure
   is exit 86 with a message, and **no test starts**.
2. It creates a run directory with a random name. It **chooses the stub's loopback port** now (a random port from a fixed range; a new network namespace has no listener, so the port is free there) and writes the manifest with every endpoint, the stub's port included.
3. It starts the **outside services**: the disposable PostgreSQL container with its Unix-domain socket in the run directory, and it verifies its identity **from outside** (the socket is a file, and it crosses the namespace). A loopback service **cannot** be started here, because a listener in the host network namespace is not visible inside the sandbox.
4. It starts the namespace with an **in-sandbox launcher** (a small program of the runner) and not yet with `pytest`. **The launcher runs without the guard** (the runner sets `PYTHONPATH` to the guard directory only for the `pytest` process), so that its own loopback self-connect and the stub health request are not violations. In the plain route the launcher has **two stages**: a **privileged helper** (mounts, loopback, `/proc`, the minimal devices, `pivot_root`, and the **control** capability check) and, after the capability drop, a **second stage** (the final capability proof, the seccomp load, the stub, and the start of `pytest`). The `bwrap` route has one stage. The launcher does, in this order: the steps of the route that need privilege (section 4.1); the **loopback self-connect proof**; the **capability proof**
   (including its control); the seccomp filter (section 4.1); then the **inside services**: it starts the NeuroForge stub on the chosen port and **verifies the stub's identity** (a health request that answers with the run identifier). It reports each result through a status file in the run directory.
   If any step fails, the launcher exits and the runner exits 86. **Only then** the launcher starts `python -m pytest ...` with the sanitized environment and `PYTHONPATH` set to the runner directory first.
5. The interpreter starts. `sitecustomize` installs the guard. It records a snapshot of `sys.modules` and a counter, **before** `pytest`, `httpx`,
   `redis`, `psycopg2`, `sqlalchemy` or `app` is imported.
6. Pytest starts. The plugin loads with `-p`. In the earliest hook (`pytest_load_initial_conftests`) it checks that the guard is installed and that
   the snapshot has none of those modules. If not, the run stops with exit 87.
7. `tests/conftest.py` runs its gate, then its `setdefault` calls (now harmless, because the runner already set the values), then it imports `app`.
8. Collection and tests run. The outer runner reads `violations.jsonl` and the report, tears the services down and sets the exit code.

## 5. The allowlist of local services

The manifest names **explicit endpoints**, each tied to a process that the runner started in this run. "Loopback" alone is not "disposable".

| Service | How it is provided | Endpoint in the manifest | Identity check before tests |
|---|---|---|---|
| Disposable PostgreSQL with pgvector (the RLS tests, the cloud-image concurrency tests, and any test that needs Postgres) | A container started with `--network none` from a pinned image (`pgvector/pgvector:pg16` is cached locally), with a Unix-domain socket in the run directory mounted into it | `unix:<run-dir>/pg/.s.PGSQL.5432` | The container id and the socket path are recorded. A query returns the server version and a marker that the runner wrote into a table. Random credentials. The socket directory is under the run directory. |
| Stub of the NeuroForge embedding endpoint | A small process that the runner starts **inside** the namespace on a loopback port that the runner chose | `tcp:127.0.0.1:<port>`, service `neuroforge-stub` | The in-sandbox launcher sends a health request that answers with the run identifier, **before pytest starts**. The port is chosen in step 2 and is in the manifest and the environment. |
| Redis | **Declared absent** unless the decision owner wants a disposable Redis (the image is not cached locally) | `declared_absent: unix:<run-dir>/redis-absent.sock` | None. A probe fails with "no such file" and is logged. |
| In-process ASGI app, in-memory SQLite | Not a socket | none | none |

**Not verified here:** a container started with `--network none` that serves PostgreSQL over a bind-mounted Unix-socket directory, and the
file ownership of that socket for the container user and for the test user. The design depends on it, so the first proof step of the implementation is a
canary for exactly this. The image `pgvector/pgvector:pg16` is present in the local image store (it was not started for this design).

**Identity rules.** A TCP loopback endpoint is allowed only on a manifest port. A Unix socket is allowed only at a manifest path, after `realpath`. `localhost` is allowed
only on a manifest port. An empty host is the default socket and is denied. A DSN from an ambient variable is ignored.

Everything else is denied: any other loopback port (including this machine's system PostgreSQL), any non-loopback address, every hosted name, and any
Unix socket that is not in the manifest. A DSN that a developer supplies in an ambient variable is **ignored**. The runner uses only its own.
Supporting an external Postgres would need its own design, because an external server cannot be proven disposable.

The RLS test runs `CREATE DATABASE` and `DROP DATABASE`. Under this design it can only reach the runner's own disposable server. The design also asks for a
check in that test that the host is in the manifest (a second line, section 8).

## 6. Failure behavior

| Condition | Result | Exit code | What stays on disk |
|---|---|---|---|
| A precondition fails: no namespace or mount namespace; for the plain route, `ip` missing; the loopback self-connect proof fails; the privilege proof fails (the rule of section 4.1 for the route in use, including a control check that cannot fail); the preflight of the base interpreter fails; the seccomp filter cannot be loaded; the `AF_VSOCK` canary does not fail as expected; `.env` present; a proxy variable set; a service does not start; an identity check fails | The runner stops before any test. It prints the reason. | 86 | The run directory with the logs |
| `pytest` is started without the runner | `conftest` stops the run | 87 | none |
| The guard is not installed before the first import | The plugin stops the run | 87 | The snapshot |
| A violation (any layer). The exit-87 check reads `violations.jsonl` **only**. The log of declared-absent probes is a separate file. It is listed in the report and is not a failure. | The test fails. The run continues so that all violations show. The outer runner fails the run at the end. | 87 | `violations.jsonl` |
| A swallowed violation (the code caught `BaseException`) | Found in `violations.jsonl` by the outer runner | 87 | `violations.jsonl` |
| A skip with no declared reason | The report lists it. The run fails. | 87 | The report |
| A service does not stop in teardown | The runner kills it, records it and fails the run | 88 | The logs |
| Tests fail for their own reasons | Normal pytest exit status. It is not an isolation failure. | 1 | Normal |

There is **no flag** that turns the guard off in the runner. A developer who needs an unguarded run uses a documented separate command that prints a banner and that
cannot produce release evidence. That command is not part of this design.

## 7. Child processes, redirects and proxies

- **Python children** inherit `PYTHONPATH`, so `sitecustomize` installs the guard in them too (`alembic`).
- **Non-Python children** (`bash`, `git`, `curl`, `openssl`) are stopped by the namespace. The audit hook logs the spawn of an executable that is not in the
  manifest's list of allowed programs (`python`, `bash`, `git`, `openssl`, and the shims that the tests create), and the run fails if it sees one.
  The render-git-auth tests keep their shims. A real `curl` that a test might reach would fail with `Network is unreachable` and show as a test failure.
- **Redirects.** Every hop of a redirect opens a new connection. Each connection is checked, so a `Location` that names a hosted host is blocked at the
  DNS lookup or at the connect, **whatever the client's `follow_redirects` setting is**. The canaries test both `httpx` and `requests`.
- **Proxies.** Proxy variables are removed and checked. Inside the namespace nothing outside is reachable anyway.

## 8. Regression evidence

**The canaries are safe by construction.** They use only RFC 5737 addresses (`192.0.2.0/24`) and the reserved `.invalid` top-level domain. Even if isolation
failed, no real host would be contacted.

A separate canary suite exercises the **runner itself**. It does not import `app` and does not run the DataForge suite.

| Property | Canary |
|---|---|
| Layer 1 refuses a route | Inside the namespace, a TCP connection to `192.0.2.1` fails with `Network is unreachable`. |
| Layer 2 refuses a name | `getaddrinfo("canary.invalid")` raises the violation. |
| A loopback port that is not in the manifest | Refused and recorded. |
| An allowlisted endpoint works | The disposable Postgres answers over its socket. The stub answers. |
| Child Python process | A `subprocess` child that connects to `192.0.2.1` writes a violation. The parent run fails. |
| Child non-Python process | `bash -c` with `/dev/tcp/192.0.2.1/80`, and `curl http://192.0.2.1`, fail with an unreachable network. A spawn of an unlisted executable is recorded. |
| `libpq` | `psycopg2.connect(host="192.0.2.1")` is refused by the wrapper, and would also fail in the namespace. |
| Redirect | A local allowlisted server returns `302` with `Location: http://hosted.invalid/`. `httpx` with `follow_redirects=True` and `requests` fail at the second hop. |
| Proxy | With `HTTP_PROXY` set, the runner stops at precondition (exit 86). |
| Swallowed violation | A canary test wraps a blocked connect in `except Exception: pytest.skip()`. It is reported **failed**, and the run exits 87. |
| `except BaseException` | A canary catches `BaseException` around a blocked connect. The record in `violations.jsonl` still fails the run. |
| Order | A canary imports `app` first. The plugin stops the run. A snapshot test shows that `sitecustomize` ran before `pytest` and `httpx`. |
| Direct `pytest` | Starting `pytest` without the runner exits 87. |
| Namespace failure | A forced failure of namespace creation gives exit 86 and no tests ran. |
| Identity of a service | A manifest entry that points at an external DSN is refused. |
| Filesystem sockets | A listener that the canary starts on a socket path **outside** the run directory is refused by the guard and is absent from the mount namespace. A hostless `psycopg2.connect` is refused. `/var/run/docker.sock`, `SSH_AUTH_SOCK` and the D-Bus socket are not reachable. `PGHOST`, `DOCKER_HOST`, `SSH_AUTH_SOCK` and `DBUS_SESSION_BUS_ADDRESS` are unset in the test process. |
| Loopback | The proof is a self-connect on `127.0.0.1` inside the final sandbox. In the plain `unshare` route the runner brings `lo` up first (and exits 86 if `ip` is missing). In the `bwrap` route it must **not** run `ip link set lo up`, which fails there. If the proof fails, the runner exits 86. |
| Privilege | A test process cannot `setns` or `nsenter` into the host network namespace. The runner checks the privilege rule of section 4.1 (no capabilities in `CapEff` and `CapBnd`, `NoNewPrivs=1`, and the uid where the route preserves it) and exits 86 if it is not met. A **control** process before the drop must show non-zero `CapEff`, or the runner exits 86. |
| Synthetic `/etc` and interpreter | Inside the sandbox `getpwuid` returns the synthetic user, `localhost` resolves, there is no `resolv.conf`, and the preflight imports `ssl`, `sqlite3` and `json` from the bound interpreter. A deliberately unbound interpreter tree gives exit 86. |
| Other socket families | A C-level `socket(AF_VSOCK, ...)` in the final process fails (creation only, never a connect). The guard refuses the `socket.__new__` event for family 40. The sandbox has no `/dev/vsock`. If the seccomp filter cannot be loaded, the runner exits 86. |
| In-sandbox services | The stub starts inside the sandbox on the chosen port and answers with the run identifier **before pytest starts**. A listener started outside the sandbox on that port is not visible inside. |
| Unwritable record | If `violations.jsonl` cannot be written, the process stops. |
| Collect only | `pytest --collect-only` without the runner exits 87. |
| Teardown | After the run no container, socket or process of the run remains. |
| Declared absent | A probe of the declared-absent Redis is logged, and the dependent tests are skipped with the declared reason and listed. |

**Closure of M1** (a later, separately authorized step) needs, at least: the canaries pass; a full run of the suite under the runner has **zero
violations**, and every skip is enumerated with a declared reason; the earlier nine SQLite failures and the PostgreSQL results are unchanged, or any change is explained; a
planted violation in a copy of the suite fails the run; and an independent review of the exact head. Documenting this design does not close M1.

## 9. Proposed files (none authorized)

| Area | File |
|---|---|
| Runner | `scripts/run-tests-isolated.sh` (a thin wrapper) and `scripts/isolated_test_runner.py` (preconditions, services, namespace, report, exit codes) |
| Guard | `tests/isolation/netguard.py` (allowlist, audit hook, wrappers, violation log), `tests/isolation/sitecustomize.py` (bootstrap), `tests/isolation/pytest_plugin.py` (per-test conversion, declared-absent skips, early check) |
| Services | `tests/isolation/services.py` (disposable Postgres container with a Unix socket, Redis option), `tests/isolation/stub_neuroforge.py` |
| Canaries | `tests/isolation/canary/` (the canary suite), outside the default `testpaths` |
| Edits to existing files | `tests/conftest.py` (the gate, before the `app` imports); `pytest.ini` (register the marker; no change to `addopts`); `tests/test_security/test_rls_public_tables.py` (a sanitized child environment and a host check before `CREATE DATABASE`); `.github/workflows/test.yml` (call the runner for the pytest step only; the install and migration steps keep their egress); `doc/system/15-testing.md` and `bash doc/system/BUILD.sh`; `docs/KNOWN_ISSUES.md` (a status update only after proof) |
| Not in this repair | `app/config.py:107` and `app/utils/embeddings.py:25-26` are application code. A later, separately authorized change can remove the duplicated hosted default. The runner does not depend on it. |

## 10. Decisions and open questions

1. **Provider.** Is the namespace plus Unix-socket services the chosen mechanism, with a Docker `--internal` network as the CI fallback? What does CI need to prove with a probe step?
2. **Direct `pytest`.** Should it stop with no override (the design), or may a documented override exist?
3. **The embedding tests.** Run them against the stub (they exercise the code path) or declare them skipped? The design prefers the stub.
4. **Redis.** Provide a disposable Redis (an image is needed) or keep it declared absent?
5. **The application's hosted defaults.** Authorize a later change to remove or unify them, or leave them as they are?
6. **Postgres image.** The local host has no pgvector extension. Is a pinned container image acceptable as the provider, and which tag?
7. **Where the runner is required.** Every run, or release evidence only? The design says every run of the suite, because ordinary runs caused M1.
8. **The mount-namespace tool.** `bwrap` (installed here) or `unshare -m` with explicit bind mounts? And what is the policy for a host where neither is available (the runner refuses)?
9. **Privilege.** The `sudo` route is **not accepted** in this design (unverified, section 4.1). Is the rule of section 4.1 the right rule for CI for the other two routes: the test process has **no capabilities, `NoNewPrivs=1` and is never real root**, with the uid of the invoking user where the route keeps it (`bwrap`) and uid 0 only inside an unprivileged user namespace (the plain route)? The runner never runs tests as real root. **If the kernel refuses unprivileged namespaces, the runner refuses (exit 86) and Option B applies.** A `sudo` route is not part of this decision.

## 11. Dependencies, review and stop conditions

- This design needs the decision owner's acceptance and a recorded review. The implementation is a separate authorization.
- It needs no change in DataForge application code, no credential and no network.
- **Stop** if a layer needs privilege that the owner has not allowed, if a hosted service would be contacted, if the design needs a production change, or if a
  held scope (RG-7, the W2 lift, WP-DF-01, role grants) is touched.

## 12. What this document does not do

It writes no code, runs no suite and contacts no hosted service. It does not repair M1, and it does not close it. It changes no
workflow, no application file and no credential.
