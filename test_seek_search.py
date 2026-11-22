"""Offline regression tests for the SEEK endpoint and job description parser."""
import json
import unittest
from unittest.mock import patch

import seek_search


class SeekDetailTests(unittest.TestCase):
    def test_detail_posts_to_canonical_host_and_parses_description(self):
        body = {"data": {"jobDetails": {"job": {
            "id": "12345678", "title": "Python Engineer", "advertiser": {"name": "Example Studio"},
            "content": "<h2>About the role</h2><p>Build Python APIs.</p><ul><li>Maintain tests</li></ul>",
            "workTypes": {"label": "Full time"}, "isExpired": False,
        }}}}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(body).encode()

        with patch.object(seek_search, "urlopen", return_value=Response()) as request:
            job = seek_search.fetch_detail("12345678")
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://au.seek.com/graphql")
        self.assertEqual(sent.get_method(), "POST")
        self.assertEqual(json.loads(sent.data)["variables"]["jobId"], "12345678")
        self.assertIn("Build Python APIs.", job["description"])
        self.assertNotIn("<p>", job["description"])
        self.assertEqual(job["company"], "Example Studio")
        self.assertFalse(job["is_expired"])


if __name__ == "__main__":
    unittest.main()
