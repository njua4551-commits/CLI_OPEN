"""Validate the Responses summary subset before relaying upstream events."""
import io
import json
from pathlib import Path
import runpy
import threading
import unittest

RESPONSES = runpy.run_path(str(Path(__file__).resolve().parents[1] / "implementacion/gateway/responses.py"))


class Stream(io.BytesIO):
    status = 200

    def getheader(self, _name, _default=None):
        return "text/event-stream"


def encode(event):
    return b"data: " + json.dumps(event).encode() + b"\n\n"


def summary(kind, value):
    return dict(type="response.reasoning_summary_" + kind, item_id="rs_fixture",
                output_index=0, summary_index=0, sequence_number=1, **value)


class ResponsesTest(unittest.TestCase):
    def test_supported_summary_payloads_and_unknown_events(self):
        identity = dict(id="fixture", model="fixture")
        created = encode(dict(type="response.created", response=identity))
        completed = encode(dict(type="response.completed", response={**identity, "status": "completed"}))
        part = {"part": {"type": "summary_text", "text": "synthetic"}}
        events = [
            summary("part.added", part), summary("text.delta", {"delta": "synthetic"}),
            summary("text.done", {"text": "synthetic"}), summary("part.done", part),
        ]
        data = created + b"".join(map(encode, events)) + completed
        output = []
        result = RESPONSES["relay"](Stream(data), "fixture", output.append, threading.Event(), 8192, None)
        self.assertEqual(result, ("complete", (None, None)))
        self.assertEqual(b"".join(output), data)
        for event in (
            summary("part.added", {"part": {"type": "unknown", "text": "synthetic"}}),
            summary("text.delta", {"delta": 4}),
            {**events[-1], "summary_index": True},
            {**events[-1], "type": "response.reasoning_summary_other"},
        ):
            with self.subTest(event=event):
                output = []
                data = created + encode(event) + completed
                with self.assertRaises(ValueError):
                    RESPONSES["relay"](Stream(data), "fixture", output.append, threading.Event(), 8192, None)
                self.assertEqual(output, [created])

    def test_rejects_nonfinite_nested_in_responses_request(self):
        base = b'{"model":"fixture","stream":true,"input":[{"type":"message","role":"user","content":"x"}],'
        for token in (b"NaN", b"Infinity", b"1e999"):
            body = base + b'"tools":[{"type":"function","name":"x","parameters":{"extra":[' + token + b']}}]}'
            with self.subTest(token=token), self.assertRaises(ValueError):
                RESPONSES["parse"](body, "fixture", 10)


if __name__ == "__main__":
    unittest.main()
