import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.run_openrouter import main, select_prompts, complete


class OpenRouterTests(unittest.TestCase):
    def test_sol_low_reasoning_request_omits_unsupported_temperature(self):
        payload = {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}
        with patch("scripts.run_openrouter.urllib.request.urlopen", return_value=io.StringIO(json.dumps(payload))) as network:
            result = complete("test", "openai/gpt-6.1-sol", "dummy", reasoning_effort="low")
        body = json.loads(network.call_args.args[0].data)
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertNotIn("temperature", body)
        self.assertEqual(result["settings"]["reasoning_effort"], "low")
    def test_dry_run_does_not_read_key_or_call_network(self):
        with patch("sys.argv", ["runner", "--model", "test/model"]), \
             patch("scripts.run_openrouter.getpass.getpass") as key, \
             patch("scripts.run_openrouter.urllib.request.urlopen") as network, \
             contextlib.redirect_stdout(io.StringIO()):
            main()
        key.assert_not_called()
        network.assert_not_called()

    def test_private_records_rejected(self):
        with self.assertRaises(ValueError):
            select_prompts("data/examples/private.jsonl", 3)

    def test_bounded_mock_run_and_no_secret_in_saved_output(self):
        payload = {"model": "test/model", "id": "generation-test", "usage": {"total_tokens": 10},
                   "choices": [{"message": {"content": '{}'}, "finish_reason": "stop"}]}
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as scratch:
            output = Path(scratch) / "responses.jsonl"
            def response(*args, **kwargs):
                return io.StringIO(json.dumps(payload))
            with patch("sys.argv", ["runner", "--model", "test/model", "--execute", "--output", str(output)]), \
                 patch("sys.stdin.isatty", return_value=True), \
                 patch("scripts.run_openrouter.getpass.getpass", return_value="dummy-secret"), \
                 patch("scripts.run_openrouter.urllib.request.urlopen", side_effect=response) as network, \
                 contextlib.redirect_stdout(io.StringIO()) as log:
                main()
            self.assertEqual(network.call_count, 3)
            self.assertEqual(len(output.read_text().splitlines()), 3)
            self.assertNotIn("dummy-secret", output.read_text() + log.getvalue())
            self.assertNotIn("Authorization", output.read_text() + log.getvalue())


if __name__ == "__main__":
    unittest.main()
