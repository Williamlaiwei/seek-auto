"""Exercise the actual AI HTTP transport using a local synthetic provider."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class ProviderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "studio.sqlite3"
        self.patch = patch.object(server, "DATA", self.database)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.requests = []
        self.fail = False
        self.malformed = False
        case = self

        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                case.requests.append((self.path, self.headers.get("Authorization"), body))
                if case.fail:
                    self.send_response(429)
                    self.end_headers()
                    return
                result = {
                    "score": 82, "verdict": "Apply", "summary": "Relevant Python experience.",
                    "strengths": ["Python APIs"], "gaps": [], "must_confirm": ["Work rights"],
                    "next_steps": ["Review the letter"],
                    "cover_letter": "Dear Hiring Manager,\n\n" + "I build Python services and maintain databases. " * 5 + "\n\nKind regards,",
                }
                content = "not JSON" if case.malformed else json.dumps(result)
                payload = json.dumps({"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_provider)
        self.job = server.dispatch("/api/manual", {
            "title": "Python Engineer", "company": "Example Studio",
            "description": "Build Python APIs and maintain SQL databases in a collaborative engineering team.",
        })["job"]
        self.request = {
            "id": self.job["id"], "profile": "I build and maintain Python APIs backed by SQL databases.",
            "config": {"base_url": f"http://127.0.0.1:{self.http.server_port}/v1",
                       "model": "synthetic-model", "api_key": "SYNTHETIC-TRANSPORT-KEY"},
        }

    def stop_provider(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)

    def test_generation_sends_real_http_and_caches_without_saving_key(self):
        generated = server.dispatch("/api/generate", self.request)
        self.assertFalse(generated["cached"])
        self.assertIn("Dear Hiring Manager", generated["job"]["cover_letter"]["text"])
        path, auth, payload = self.requests[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(auth, "Bearer SYNTHETIC-TRANSPORT-KEY")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(json.loads(payload["messages"][1]["content"])["job"]["description"], self.job["description"])
        self.assertTrue(server.dispatch("/api/generate", self.request)["cached"])
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn(b"SYNTHETIC-TRANSPORT-KEY", self.database.read_bytes())

    def test_rate_limit_and_invalid_model_response_preserve_edited_letter(self):
        server.dispatch("/api/generate", self.request)
        server.dispatch("/api/letter", {"id": self.job["id"], "letter": "My reviewed draft."})
        for mode, expected in (("fail", "quota"), ("malformed", "valid JSON")):
            with self.subTest(mode=mode):
                setattr(self, mode, True)
                try:
                    with self.assertRaisesRegex(RuntimeError, expected):
                        server.dispatch("/api/generate", {**self.request, "regenerate": True})
                    self.assertEqual(server.get_job(self.job["id"])["cover_letter"]["text"], "My reviewed draft.")
                finally:
                    setattr(self, mode, False)


if __name__ == "__main__":
    unittest.main()
