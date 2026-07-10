#!/usr/bin/env python3
"""Mailpit sink client — capture checkpoints, presence waits, absence assertions.

The sink log is the msg-channel census (FIXTURES §2.2): every outbound
message a fixture sends lands in its leg's Mailpit instance, and claims
about messaging are made against checkpoints of that log. Absence claims
("no message matching M arrived after checkpoint C") are first-class:
they are what clean verdicts are made of (ATTAINABILITY O-2).

Windows are *script positions*, not wall time: virtual-clock advances
happen between checkpoints, so "no reminder in the 30 virtual days after
deletion" is asserted as "no matching message between checkpoint(post-
deletion) and now(post-advance)", with only a small wall-clock settle for
delivery latency.

Stdlib only. Mailpit search syntax applies to queries (e.g. "to:x@y",
'subject:"renewal reminder"').
"""
import json
import time
import urllib.parse
import urllib.request


class Mailsink:
    def __init__(self, base_url="http://127.0.0.1:8025", timeout=10):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path, **params):
        url = f"{self.base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def count(self, query=None):
        """Total messages matching query (all messages if query is None)."""
        if query is None:
            return self._get("/api/v1/messages", limit=1)["total"]
        return self._get("/api/v1/search", query=query, limit=1)["messages_count"]

    def search(self, query, limit=50):
        """Matching message summaries, newest first."""
        return self._get("/api/v1/search", query=query, limit=limit)["messages"]

    def checkpoint(self, query=None):
        """Opaque checkpoint: the current match count for query."""
        return (query, self.count(query))

    def wait_new(self, checkpoint, timeout=30, poll=0.5):
        """Block until a message beyond `checkpoint` arrives; return the newest
        match. Raises TimeoutError otherwise. Wall-clock timeout covers
        delivery latency only — the *event* being waited on is a fixture
        action, not the passage of time."""
        query, baseline = checkpoint
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            n = self.count(query)
            if n > baseline:
                if query is None:
                    return self._get("/api/v1/messages", limit=1)["messages"][0]
                return self.search(query, limit=1)[0]
            time.sleep(poll)
        raise TimeoutError(f"no new message matching {query!r} within {timeout}s "
                           f"(count stayed at {baseline})")

    def assert_none_new(self, checkpoint, settle=3.0):
        """Assert no message beyond `checkpoint` has arrived, after a short
        wall-clock settle for in-flight delivery. This is the absence
        primitive: call it after the virtual-clock advance that closes the
        window."""
        query, baseline = checkpoint
        time.sleep(settle)
        n = self.count(query)
        if n > baseline:
            newest = (self.search(query, limit=3) if query
                      else self._get("/api/v1/messages", limit=3)["messages"])
            raise AssertionError(
                f"absence violated: {n - baseline} new message(s) matching "
                f"{query!r} since checkpoint; newest: "
                + "; ".join(f"{m.get('Subject')!r} to {m.get('To')}" for m in newest))
        return True

    def message(self, msg_id):
        """Full message body/headers by ID."""
        return self._get(f"/api/v1/message/{msg_id}")


if __name__ == "__main__":
    import sys
    sink = Mailsink(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8025")
    print(f"sink reachable, {sink.count()} message(s) held")
