# TRANSCRIPT — noshit-f0-documenso

Verbatim capture of one successful **pristine cold-start** run of the Documenso
F0 leg. Pristine = generated state removed first so `setup.sh` regenerates
secrets + signing cert from nothing:

    rm -rf .env data/
    ./demo.sh            # down -v -> setup.sh -> build sidecar -> up --wait -> demo.py -> down -v

**Result:** all assertions passed, `demo.py` exit code 0.
**Proof wall time (`demo.py`):** 8.5 s. **Total incl. build/up/teardown:** 36 s.
**Captured:** 2026-07-10.
**Host:** Docker 26.1.5, Compose v5.3.1. Sidecar built with the classic builder
(host buildx 0.13.1 predates the 0.17 that `compose build` requires).
**Images:** documenso/documenso:v2.14.0 (1.68 GB), postgres:15-alpine (292 MB),
axllent/mailpit:v1.30.4 (34 MB), sidecar noshit-f0-documenso-scheduler:local
(121 MB = python:3.12-slim + libfaketime 0.9.10).

```text
[demo] generating local secrets + signing cert (setup.sh) ...
[setup] generating .env with fresh random secrets
[setup] generating self-signed signing certificate -> data/cert.p12
[setup] reset data/faketime/faketimerc to +0d (virtual day 0)
[setup] done.
[demo] cold start: clearing any prior stack state ...
time="2026-07-10T00:07:53Z" level=warning msg="Warning: No resource found to remove for project \"noshit-f0-documenso\"."
[demo] building fake-time sidecar image (classic builder) ...
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            BuildKit is currently disabled; enable it by removing the DOCKER_BUILDKIT=0
            environment-variable.

Sending build context to Docker daemon  6.656kB
Step 1/4 : FROM python:3.12-slim
 ---> 9cbfea842643
Step 2/4 : RUN apt-get update  && apt-get install -y --no-install-recommends libfaketime ca-certificates  && ln -sf "$(find /usr/lib -name 'libfaketime.so.1' | head -n1)" /opt/libfaketime.so  && rm -rf /var/lib/apt/lists/*
 ---> Using cache
 ---> 7439f9acad27
Step 3/4 : COPY scheduler.py /scheduler.py
 ---> Using cache
 ---> 7b127a6a4e20
Step 4/4 : CMD ["python3", "/scheduler.py"]
 ---> Using cache
 ---> d7fd6395eede
Successfully built d7fd6395eede
Successfully tagged noshit-f0-documenso-scheduler:local
[demo] starting stack (up --wait) ...
 Network noshit-f0-documenso_internal Creating 
 Network noshit-f0-documenso_internal Created 
 Volume noshit-f0-documenso_pgdata Creating 
 Volume noshit-f0-documenso_pgdata Created 
 Container noshit-f0-documenso-database-1 Creating 
 Container noshit-f0-documenso-mailpit-1 Creating 
 Container noshit-f0-documenso-database-1 Created 
 Container noshit-f0-documenso-mailpit-1 Created 
 Container noshit-f0-documenso-scheduler-1 Creating 
 Container noshit-f0-documenso-documenso-1 Creating 
 Container noshit-f0-documenso-documenso-1 Created 
 Container noshit-f0-documenso-scheduler-1 Created 
 Container noshit-f0-documenso-mailpit-1 Starting 
 Container noshit-f0-documenso-database-1 Starting 
 Container noshit-f0-documenso-database-1 Started 
 Container noshit-f0-documenso-mailpit-1 Started 
 Container noshit-f0-documenso-database-1 Waiting 
 Container noshit-f0-documenso-scheduler-1 Starting 
 Container noshit-f0-documenso-scheduler-1 Started 
 Container noshit-f0-documenso-database-1 Healthy 
 Container noshit-f0-documenso-documenso-1 Starting 
 Container noshit-f0-documenso-documenso-1 Started 
 Container noshit-f0-documenso-mailpit-1 Waiting 
 Container noshit-f0-documenso-documenso-1 Waiting 
 Container noshit-f0-documenso-scheduler-1 Waiting 
 Container noshit-f0-documenso-database-1 Waiting 
 Container noshit-f0-documenso-scheduler-1 Healthy 
 Container noshit-f0-documenso-database-1 Healthy 
 Container noshit-f0-documenso-mailpit-1 Healthy 
 Container noshit-f0-documenso-documenso-1 Healthy 
[demo] stack healthy. Running proof ...

==========================================================================
== PHASE 0 — preflight
==========================================================================
[   0.0s] sink reachable at http://localhost:8026 (0 message(s) held)
[   0.0s] documenso healthy: {"status":"ok","timestamp":"2026-07-10T00:08:20.960Z","checks":{"database":{"status":"ok"},"certificate":{"status":"ok"}}}

==========================================================================
== PHASE 1 — real signup -> confirmation email in sink (criterion 2, presence)
==========================================================================
[   0.0s] new account: f0-user-1783642100@noshit.test
[   0.5s] PASS  POST /api/auth/email-password/signup -> HTTP 201 ('OK')
[   0.5s] TIMELINE  vDAY 0                     signup for f0-user-1783642100@noshit.test (Documenso's own endpoint)
[   1.0s] confirmation email captured: subject='Please confirm your email' id=401WA7GircUqCMCxkqTgV5
[   1.0s] PASS  confirmation email landed in the sink (app -> sink coupling)
[   1.0s] TIMELINE  vDAY 0                     confirmation email captured in sink: 'Please confirm your email'

==========================================================================
== PHASE 2 — verify email FROM the captured mail -> session (real flow)
==========================================================================
[   1.0s] PASS  extracted verify token from the confirmation email (8f2364555c02...)
[   1.1s] PASS  POST verify-email -> HTTP 200 ('{"state":"VERIFIED"}')
[   1.1s] PASS  auto-authorized: signed sessionId cookie held
[   1.1s] TIMELINE  vDAY 0                     email verified -> account active + authenticated

==========================================================================
== PHASE 3 — authenticated account deletion (criterion 2, opens absence window)
==========================================================================
[   1.2s] PASS  tRPC profile.deleteAccount -> HTTP 200 ('[{"result":{"data":{"json":null,"meta":{"values":["undefined"],"v":1}}}}]')
[   1.2s] TIMELINE  vDAY 0+                    account deleted via tRPC; post-deletion absence window opens
[   1.3s] DB evidence: rows for f0-user-1783642100@noshit.test after deletion = '0' (expect 0)

==========================================================================
== PHASE 4 — stack-level fake time across a multi-day boundary (criterion 3)
==========================================================================
[   1.4s] Documenso container libc evidence:
[   1.4s]     NAME="Alpine Linux"
[   1.4s]     ID=alpine
[   1.4s]     /lib/ld-musl-x86_64.so.1
[   1.4s] => Documenso is musl/alpine: glibc libfaketime cannot LD_PRELOAD into it.
[   1.4s] => rung-2 fake time is proven on the glibc scheduler sidecar in the same stack.
[   1.4s] asserting the retention job has NOT fired at faked day 0 ...
[   4.4s] PASS  day-30 retention job absent before the virtual advance (clock-gated)
[   4.4s] TIMELINE  vDAY 0                     sidecar scheduler within retention window (no purge mail)
[   4.4s] advancing the sidecar's faked clock by +31 days ...
[   4.4s] wrote faketime offset '+31d' -> data/faketime/faketimerc
[   4.4s] TIMELINE  vDAY 0 -> vDAY 31          sidecar faked clock advanced +31d (libfaketime, seconds of wall time)
[   5.4s] retention email captured: subject='Retention window expired - scheduled data purge'
[   5.4s]     | libfaketime rung-2 proof (FIXTURES 2.1).
[   5.4s]     | The 30-day retention window has elapsed on the app-side scheduler clock.
[   5.4s]     | This day-30 job fired at faked clock 2026-08-10T00:08:26.043119 while wall-clock time advanced only seconds.
[   5.4s] PASS  day-30 retention job FIRED after crossing the faked boundary
[   5.4s] TIMELINE  vDAY 31                    retention 'data purge' mail fired into sink under fake time
[   5.4s] asserting NO further mail reached the deleted account across the window ...
[   8.4s] PASS  post-deletion absence holds: no further mail to the deleted account across the 30 virtual days
[   8.4s] TIMELINE  vDAY 31                    absence verified: 0 new messages to f0-user-1783642100@noshit.test since deletion

==========================================================================
== PHASE 5 — scripted support persona round-trip (criterion 4)
==========================================================================
[   8.4s] PASS  inbound support-request landed in sink (persona trigger)
[   8.4s] TIMELINE  persona 09:00              support request received in sink
[   8.4s] PASS  persona observed the trigger message
[   8.4s] TIMELINE  persona 09:00 -> 13:00     scripted +4h SLA virtual delay (no wall-clock sleep)
[   8.5s] PASS  persona reply round-tripped back into the sink
[   8.5s] TIMELINE  persona 13:00              persona reply delivered: 'Re: Support request: data export SLA'

==========================================================================
== PHASE 6 — virtual-time timeline
==========================================================================
VIRTUAL TIME                    WALL  EVENT
--------------------------------------------------------------------------
vDAY 0                          0.5s  signup for f0-user-1783642100@noshit.test (Documenso's own endpoint)
vDAY 0                          1.0s  confirmation email captured in sink: 'Please confirm your email'
vDAY 0                          1.1s  email verified -> account active + authenticated
vDAY 0+                         1.2s  account deleted via tRPC; post-deletion absence window opens
vDAY 0                          4.4s  sidecar scheduler within retention window (no purge mail)
vDAY 0 -> vDAY 31               4.4s  sidecar faked clock advanced +31d (libfaketime, seconds of wall time)
vDAY 31                         5.4s  retention 'data purge' mail fired into sink under fake time
vDAY 31                         8.4s  absence verified: 0 new messages to f0-user-1783642100@noshit.test since deletion
persona 09:00                   8.4s  support request received in sink
persona 09:00 -> 13:00          8.4s  scripted +4h SLA virtual delay (no wall-clock sleep)
persona 13:00                   8.5s  persona reply delivered: 'Re: Support request: data export SLA'

==========================================================================
== RESULT — F0 criteria proven on the Documenso leg
==========================================================================
  crit 2  app/sink coupling  : signup confirmation captured; post-deletion
                              absence window held via checkpoint+assert_none_new
  crit 3  stack fake time    : sidecar day-30 job fired after +31d faked advance
                              (Documenso itself is musl -> documented rung-2 sidecar)
  crit 4  persona round-trip : trigger -> scripted +4h virtual delay -> reply in sink
[   8.5s] ALL ASSERTIONS PASSED in 8.5s wall time

[demo] demo.py exit code: 0
[demo] total wall-clock duration: 36s

[demo] tearing down (scoped: docker compose -p noshit-f0-documenso down -v) ...
 Container noshit-f0-documenso-scheduler-1 Stopping 
 Container noshit-f0-documenso-documenso-1 Stopping 
 Container noshit-f0-documenso-scheduler-1 Stopped 
 Container noshit-f0-documenso-scheduler-1 Removing 
 Container noshit-f0-documenso-scheduler-1 Removed 
 Container noshit-f0-documenso-documenso-1 Stopped 
 Container noshit-f0-documenso-documenso-1 Removing 
 Container noshit-f0-documenso-documenso-1 Removed 
 Container noshit-f0-documenso-database-1 Stopping 
 Container noshit-f0-documenso-mailpit-1 Stopping 
 Container noshit-f0-documenso-database-1 Stopped 
 Container noshit-f0-documenso-database-1 Removing 
 Container noshit-f0-documenso-mailpit-1 Stopped 
 Container noshit-f0-documenso-mailpit-1 Removing 
 Container noshit-f0-documenso-database-1 Removed 
 Container noshit-f0-documenso-mailpit-1 Removed 
 Volume noshit-f0-documenso_pgdata Removing 
 Network noshit-f0-documenso_internal Removing 
 Volume noshit-f0-documenso_pgdata Removed 
 Network noshit-f0-documenso_internal Removed 
```
