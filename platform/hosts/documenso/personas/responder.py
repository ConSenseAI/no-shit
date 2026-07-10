#!/usr/bin/env python3
"""Scripted support persona (F0 criterion 4 / FIXTURES §2.4).

A minimal stub proving the timed-response machinery: it watches the Mailpit
sink for a trigger message (subject contains a keyword), then replies after a
SCRIPTED VIRTUAL DELAY — an explicit `advance()` step the demo makes on the
persona's own virtual clock, never a wall-clock sleep. The reply is SMTP'd back
into the same sink so the request -> response round-trip is visible in the
msg-channel census.

Reads via the shared harness Mailsink; sends via stdlib smtplib. Stdlib only.
"""
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid


class SupportPersona:
    def __init__(
        self,
        sink,
        smtp_host="127.0.0.1",
        smtp_port=1026,
        address="support@noshit.test",
        virtual_now=None,
    ):
        self.sink = sink
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.address = address
        # The persona's OWN virtual clock. It only moves when the script steps it.
        self.virtual_now = virtual_now or datetime(2026, 1, 1, 9, 0, 0)

    def advance(self, **delta) -> datetime:
        """Advance the persona's virtual clock by an explicit step (no sleep)."""
        self.virtual_now = self.virtual_now + timedelta(**delta)
        return self.virtual_now

    def find_trigger(self, keyword="support request"):
        """Newest sink message whose subject contains `keyword`, or None."""
        for m in self.sink.search(f'subject:"{keyword}"', limit=5):
            return m
        return None

    def respond_to(self, trigger, sla_note="scripted virtual delay"):
        """SMTP a reply into the sink, stamped with the persona's virtual time."""
        subject = trigger.get("Subject", "")
        to_addr = self._sender_of(trigger)
        reply = EmailMessage()
        reply["From"] = self.address
        reply["To"] = to_addr
        reply["Subject"] = f"Re: {subject}"
        reply["Message-Id"] = make_msgid(domain="noshit.test")
        reply.set_content(
            "Hello,\n\n"
            f"This is the scripted support persona replying at virtual time "
            f"{self.virtual_now.isoformat()} ({sla_note}).\n\n"
            f"Your request ({subject!r}) has been received and actioned.\n\n"
            "-- F0 persona stub"
        )
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as s:
            s.send_message(reply)
        return reply

    @staticmethod
    def _sender_of(msg) -> str:
        frm = msg.get("From")
        if isinstance(frm, dict):
            return frm.get("Address") or "user@noshit.test"
        if isinstance(frm, list) and frm:
            return frm[0].get("Address", "user@noshit.test")
        return "user@noshit.test"
