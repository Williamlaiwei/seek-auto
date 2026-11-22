"""Run: python -m unittest -v"""
import json
import uuid
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import server


class DashboardTests(unittest.TestCase):
    def setUp(self):
        test_root = server.ROOT / ".local" / "tests"
        test_root.mkdir(parents=True, exist_ok=True)
        self.test_data = test_root / (uuid.uuid4().hex + ".sqlite3")
        self.data_patch = patch.object(server, "DATA", self.test_data)
        self.data_patch.start()
        self.job = server.dispatch("/api/manual", {"title": "Engineer", "company": "Example",
            "description": "Build Python services. Requires three years of experience. Sydney hybrid role."})["job"]

    def tearDown(self):
        self.data_patch.stop()
        self.test_data.unlink(missing_ok=True)

    def test_profile_save_never_persists_key(self):
        server.dispatch("/api/preferences", {"profile": "My experience", "config": {
            "base_url": "https://example.com/v1", "model": "example", "api_key": "SECRET-KEY"}})
        with server.db() as con:
            raw = con.execute("SELECT data FROM preferences").fetchone()[0]
        self.assertNotIn("SECRET-KEY", raw)
        self.assertNotIn("api_key", raw)

    def generation_request(self):
        return {"id": self.job["id"], "profile": "Five years of Python API experience, including database design.",
                "examples": "My preferred letter style.", "writing_style": "Australian English, concise.",
                "config": {"base_url": "http://localhost:11434/v1", "model": "test-model"}}

    def generation_result(self):
        return {"score": 80, "verdict": "Apply", "summary": "Skills match; work rights need confirmation.", "strengths": ["Python APIs"],
                "gaps": [], "must_confirm": ["Work rights"], "next_steps": ["Review and apply"],
                "cover_letter": "Dear Hiring Manager,\n\nI am applying for the Engineer position. My experience building Python APIs and designing databases aligns with your team's requirements. I would welcome a conversation about how I can contribute.\n\nKind regards,"}

    def test_generation_context_caching_and_profile_change(self):
        request = self.generation_request()
        with patch.object(server, "completion", return_value=self.generation_result()) as complete:
            first = server.dispatch("/api/generate", request)
            self.assertFalse(first["cached"])
            context = json.loads(complete.call_args.args[1][1]["content"])
            self.assertEqual(context["candidate_profile"], request["profile"])
            self.assertEqual(context["examples"], request["examples"])
            self.assertEqual(context["job"]["description"], self.job["description"])
            self.assertTrue(server.dispatch("/api/generate", request)["cached"])
            self.assertEqual(complete.call_count, 1)
            server.dispatch("/api/generate", {**request, "profile": request["profile"] + " Additional relevant experience."})
            self.assertEqual(complete.call_count, 2)
        self.assertEqual(len(server.get_job(self.job["id"])["letter_history"]), 1)

    def test_revision_receives_current_draft_and_archives_previous_letter(self):
        request = self.generation_request()
        with patch.object(server, "completion", return_value=self.generation_result()) as complete:
            server.dispatch("/api/generate", request)
            edited = server.dispatch("/api/letter", {"id": self.job["id"], "letter": "My edited letter."})["job"]
            self.assertTrue(edited["cover_letter"]["edited"])
            revised = server.dispatch("/api/generate", {**request, "revision": "Make it shorter.", "current_draft": "My edited letter."})
            context = json.loads(complete.call_args.args[1][1]["content"])
        self.assertEqual(context["revision"], "Make it shorter.")
        self.assertEqual(context["current_draft"], "My edited letter.")
        self.assertEqual(revised["job"]["letter_history"][-1]["text"], "My edited letter.")

    def test_failed_generation_preserves_edited_letter(self):
        request = self.generation_request()
        with patch.object(server, "completion", return_value=self.generation_result()):
            server.dispatch("/api/generate", request)
        server.dispatch("/api/letter", {"id": self.job["id"], "letter": "Keep this draft."})
        bad = {**self.generation_result(), "cover_letter": ""}
        with patch.object(server, "completion", return_value=bad), self.assertRaises(RuntimeError):
            server.dispatch("/api/generate", {**request, "regenerate": True})
        self.assertEqual(server.get_job(self.job["id"])["cover_letter"]["text"], "Keep this draft.")

    def test_manual_url_and_attach_link_preserve_draft(self):
        with self.assertRaises(ValueError):
            server.dispatch("/api/job-link", {"id": self.job["id"], "url": "javascript:alert(1)"})
        with patch.object(server, "completion", return_value=self.generation_result()):
            server.dispatch("/api/generate", self.generation_request())
        linked = server.dispatch("/api/job-link", {"id": self.job["id"], "url": "https://au.seek.com/job/12345678?ref=test"})["job"]
        self.assertEqual(linked["url"], "https://www.seek.com.au/job/12345678")
        self.assertEqual(linked["cover_letter"]["text"], self.generation_result()["cover_letter"])
        self.assertEqual(len(server.jobs()), 1)

    def test_api_failure_does_not_erase_letter(self):
        with patch.object(server, "completion", return_value=self.generation_result()):
            server.dispatch("/api/generate", self.generation_request())
        with patch.object(server, "completion", side_effect=RuntimeError("API unavailable")), self.assertRaises(RuntimeError):
            server.dispatch("/api/generate", {**self.generation_request(), "regenerate": True})
        self.assertIn("Dear Hiring Manager", server.get_job(self.job["id"])["cover_letter"]["text"])

    def test_search_preserves_analysis_and_status(self):
        server.save_job({"id": "12345678", "analysis": {"score": 80}, "application_status": "Saved", "description": "full text"})
        with patch.object(server.seek, "fetch_page", return_value={"data": [{"id": 12345678, "title": "New title"}]}):
            result = server.search_jobs({"keywords": "Python"})
        self.assertEqual(result["jobs"][0]["analysis"]["score"], 80)
        self.assertEqual(result["jobs"][0]["application_status"], "Saved")
        self.assertEqual(result["jobs"][0]["description"], "full text")

    def test_search_failure_is_not_reported_as_no_results(self):
        with patch.object(server.seek, "fetch_page", side_effect=URLError("offline")):
            with self.assertRaises(RuntimeError):
                server.search_jobs({"keywords": "Python"})

    def test_partial_search_keeps_results_with_warning(self):
        with patch.object(server.seek, "fetch_page", side_effect=[{"data": [{"id": "12345678", "title": "Engineer"}]}, URLError("offline")]), patch.object(server.time, "sleep"):
            result = server.search_jobs({"keywords": "Python", "pages": 2})
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(len(result["warnings"]), 1)

    def test_analysis_uses_full_jd_and_rejects_incomplete_response(self):
        request = {"id": self.job["id"], "profile": "I have five years of experience building Python APIs.",
                   "config": {"base_url": "http://localhost:11434/v1", "model": "example"}}
        result = {"score": 75, "verdict": "Apply", "summary": "Relevant Python experience.",
                  "strengths": ["Five years of Python"], "gaps": [], "must_confirm": ["Work rights"], "next_steps": ["Confirm requirements"]}
        with patch.object(server, "completion", return_value=result) as complete:
            saved = server.dispatch("/api/analyze", request)["job"]
            context = json.loads(complete.call_args.args[1][1]["content"])
        self.assertEqual(context["job"]["description"], self.job["description"])
        self.assertEqual(saved["analysis"]["score"], 75)
        with patch.object(server, "completion", return_value={"score": 100}):
            with self.assertRaises(RuntimeError):
                server.dispatch("/api/analyze", request)
        self.assertEqual(server.get_job(self.job["id"])["analysis"]["score"], 75)

    def test_invalid_scores_and_wrong_types_rejected(self):
        for score in (True, -1, 101, "85", float("nan")):
            with self.subTest(score=score), self.assertRaises(RuntimeError):
                server.validate_analysis({"score": score})

    def test_missing_profile_does_not_call_provider(self):
        with patch.object(server, "completion") as complete:
            with self.assertRaises(ValueError):
                server.dispatch("/api/analyze", {"id": self.job["id"], "profile": "",
                    "config": {"base_url": "http://localhost:11434/v1", "model": "example"}})
            complete.assert_not_called()

    def test_api_url_and_import_validation(self):
        for url in ("http://remote.example/v1", "https://user:password@example.com", "https://example.com?key=secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                server.ai_config({"config": {"base_url": url, "model": "test", "api_key": "secret"}})
        with self.assertRaises(ValueError):
            server.dispatch("/api/import", {"url": "https://evil.example/job/12345678"})

    def test_provider_payload_and_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]}).encode()
        with patch.object(server, "build_opener") as opener:
            opener.return_value.open.return_value = Response()
            result = server.completion(("https://example.com/v1", "secret", "my-model"), [{"role": "user", "content": "JSON"}])
            request = opener.return_value.open.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(request.full_url, "https://example.com/v1/chat/completions")
        self.assertEqual(json.loads(request.data)["response_format"], {"type": "json_object"})
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")

    def test_http_serves_only_app_and_rejects_cross_origin(self):
        http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http.server_port}"
        try:
            with urlopen(base) as response:
                self.assertIn("SEEK CL Studio", response.read().decode())
            with urlopen(base + "/api/state") as response:
                self.assertEqual(len(json.load(response)["jobs"]), 1)
            for path in ("/.local/dashboard.sqlite3", "/../README.md"):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base + path)
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
            request = Request(base + "/api/status", data=b'{}', headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
            with self.assertRaises(HTTPError) as caught:
                urlopen(request)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        finally:
            http.shutdown()
            http.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
