# M1 isolation repair: design of an enforced default-deny test runner

Date: 2026-10-04. Status: **proposal only.** This file authorizes no code, no test run, no workflow change and no application
change. It contacts no hosted service. **Finding M1 stays open** (`docs/KNOWN_ISSUES.md`, the entry of 2026-10-04) until a separately
authorized repair is proven. The decision owner accepts or refuses the design. A review of it is a prerequisite.

**Revision 2 (2026-10-04).** Revised after the review of pull request 90, which tested the mechanism with live local probes and broke three claims of
revision 1. (1) A filesystem Unix-domain socket crosses a network namespace, so Layer 1 is now a network namespace **plus a mount namespace**. (2) A test
process must not run as real root, and `sudo` drops the environment. (3) The loopback interface is **down** in a new namespace. The revision also
completes the list of audited events, removes the `--collect-only` exemption, specifies the declared-absent mechanism and its limits, and
adds the missing allowlist rules and canaries. The first version stays in the git history. This is still a proposal.

Pins: DataForge `origin/master` `ca7ce99625bdecbf465022b6005a97e749f3ee88`. Line numbers are for that commit and can drift.
Nothing here was measured by running the DataForge suite. The only thing that was run is a local capability probe (section 4.1).

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

The runner must **permit**: the in-process ASGI app, in-memory SQLite, and the explicitly identified disposable services of section 5.

## 4. The design: four layers

No single layer is enough. Layer 1 is the enforcement. Layers 2 to 4 give defense in depth, diagnostics and visibility.

### 4.1 Layer 1: a network namespace plus a mount namespace

The runner starts the test process in a new **user namespace** with a new **network namespace** and a new **mount namespace**.

- **The network namespace** has only a loopback interface. It refuses every TCP, UDP and DNS route to the outside for every process inside it,
  including children, `libpq` and non-Python programs. **The loopback interface is down when the namespace is created.** The runner must bring it up
  (`ip link set lo up`, which needs iproute2 as a precondition) and must prove loopback with a self-connect before it starts a service.
- **The network namespace does not isolate filesystem Unix-domain sockets.** A socket that is a path on the filesystem is reachable from inside the
  namespace. The mount namespace closes that gap.
- **The mount namespace** hides `/var/run`, `/run`, `/run/user`, `/var/run/postgresql` and the Docker socket. It binds in only the run directory (for the
  disposable sockets), the repository and the virtual environment (read only where possible), and the system libraries. `bwrap` is installed on this machine. The
  runner unsets `PGHOST`, `DOCKER_HOST`, `SSH_AUTH_SOCK` and `DBUS_SESSION_BUS_ADDRESS`, and it sets `PGHOST` to the manifest socket directory. The guard
  (section 4.2) also **denies any `AF_UNIX` path that is not in the manifest**, after `os.path.realpath` (which resolves `..` and symbolic links), and it treats an
  **empty host as the default socket and denies it**.
- **Abstract Unix sockets** do not cross a network namespace (a probe of the reviewer). The disposable services therefore use **filesystem** sockets that sit in the
  run directory, which the mount namespace binds in.

**Local capability probes (no network used, nothing contacted).**

| Probe | Result |
|---|---|
| `unshare -rn` as a normal user | Works. The only interface is `lo`, and it is **down**. |
| A connection to `192.0.2.1` (RFC 5737 TEST-NET, never routed) inside the namespace | Fails at once with `Network is unreachable` (errno 101). |
| A listener on a **filesystem** Unix socket outside the namespace, a client inside | **The client reached it.** The namespace does not isolate this. (Reproduced here.) |
| `ip link set lo up`, then IPv4 and IPv6 loopback connects | Both worked here. The reviewer's host reported that `::1` gave "Address family not supported", so the guard must not depend on IPv6. |
| An unprivileged process inside the namespace tries `nsenter --net=/proc/1/ns/net` and `setns` | **Refused** (permission denied). (Reproduced here.) |
| A hostless `psycopg2.connect` inside the namespace (the reviewer's probe) | It reached this machine's system PostgreSQL over `/var/run/postgresql/.s.PGSQL.5432`, and the server answered (peer authentication failed). A connect to `/var/run/docker.sock` also succeeded. The SSH agent and D-Bus sockets are filesystem sockets as well. |

`kernel.apparmor_restrict_unprivileged_userns` is `1` here, so restrictions exist on this class of host. The runner must **probe at start** and not assume.

**Properties.**

- The system PostgreSQL on `127.0.0.1:5432` is unreachable **by TCP**. Its **Unix socket** is reachable unless the mount namespace hides it. That is why Layer 1 needs both namespaces.
- Disposable services enter the namespace by **explicit means** (section 5): a Unix-domain socket in the run directory, or a loopback process that the runner starts
  inside the namespace.
- If the namespaces cannot be created, or `ip`, `bwrap` or the loopback proof is missing, the runner **refuses to run**. It never falls back to an unguarded
  run (section 6). The runner also refuses to run tests with an effective user of root.

**Provider for CI (a decision).**
Option A: the runner creates the namespaces **unprivileged** with a user namespace (as above) on the hosted runner, where the kernel allows it. If the
runner needs `sudo` to create them, the test process **drops to the unprivileged user and drops its capabilities** (`setpriv`) before it starts. Real root has
`CAP_SYS_ADMIN` and could `setns` into the host network namespace, which an unprivileged process cannot. `sudo` also resets the environment and drops
`PYTHONPATH`, so the runner passes the sanitized environment explicitly. Whether the hosted runner allows either route is **inferred and not verified**. The
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
  `socket.getnameinfo`, `socket.sendto`, `socket.bind` (a bind to a non-loopback address is a violation), `subprocess.Popen`, `os.system`, `os.exec` and
  `os.posix_spawn`. The reviewer probed that the asyncio calls `create_connection`, `sock_connect` and `loop.getaddrinfo` fire `connect` and `getaddrinfo`.
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
2. It creates a run directory with a random name and writes the manifest after the services are up.
3. It starts the disposable services (section 5) and verifies their identity.
4. It starts the namespace and, inside it, `python -m pytest ...` with the sanitized environment and `PYTHONPATH` set to the runner directory first.
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
| Stub of the NeuroForge embedding endpoint | A small process that the runner starts **inside** the namespace on a loopback port that the runner chose | `tcp:127.0.0.1:<port>`, service `neuroforge-stub` | A health request answers with the run identifier. |
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
| A precondition fails (no namespace, `.env` present, proxy variable set, a service does not start, an identity check fails) | The runner stops before any test. It prints the reason. | 86 | The run directory with the logs |
| `pytest` is started without the runner | `conftest` stops the run | 87 | none |
| The guard is not installed before the first import | The plugin stops the run | 87 | The snapshot |
| A violation (any layer) | The test fails. The run continues so that all violations show. The outer runner fails the run at the end. | 87 | `violations.jsonl` |
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
| Loopback | The runner brings `lo` up and proves it with a self-connect. If `ip` is missing or the proof fails, the runner exits 86. |
| Privilege | A test process cannot `setns` or `nsenter` into the host network namespace. The runner exits 86 if its effective user is root. |
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
9. **Root.** Is "the runner refuses to run tests as root, and drops capabilities if it needs `sudo`" the right rule for CI?

## 11. Dependencies, review and stop conditions

- This design needs the decision owner's acceptance and a recorded review. The implementation is a separate authorization.
- It needs no change in DataForge application code, no credential and no network.
- **Stop** if a layer needs privilege that the owner has not allowed, if a hosted service would be contacted, if the design needs a production change, or if a
  held scope (RG-7, the W2 lift, WP-DF-01, role grants) is touched.

## 12. What this document does not do

It writes no code, runs no suite and contacts no hosted service. It does not repair M1, and it does not close it. It changes no
workflow, no application file and no credential.
