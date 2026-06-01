from __future__ import annotations

import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from resume_agent.experience_bank.config import OPENAI_API_KEY_ENV_VAR
from resume_agent.experience_bank.openai_provider import (
    EXPERIENCE_DRAFT_RESPONSE_SCHEMA,
    OpenAIProviderError,
    OpenAIResponsesProvider,
)


class OpenAIResponsesProviderTests(unittest.TestCase):
    def test_calls_responses_api_with_structured_schema_and_parses_output(self) -> None:
        response_body = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"id": "experience_test"}),
                        }
                    ]
                }
            ]
        }
        fake_response = _FakeHTTPResponse(response_body)
        with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "fake-key"}, clear=True):
            with patch(
                "resume_agent.experience_bank.openai_provider.urlopen",
                return_value=fake_response,
            ) as request:
                parsed = OpenAIResponsesProvider(model="gpt-4o-mini")(
                    "system prompt",
                    "user prompt",
                )

        sent_request = request.call_args.args[0]
        payload = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(parsed, {"id": "experience_test"})
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["schema"], EXPERIENCE_DRAFT_RESPONSE_SCHEMA)
        self.assertEqual(sent_request.headers["Authorization"], "Bearer fake-key")

    def test_rejects_response_without_output_text(self) -> None:
        with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "fake-key"}, clear=True):
            with patch(
                "resume_agent.experience_bank.openai_provider.urlopen",
                return_value=_FakeHTTPResponse({"output": []}),
            ):
                with self.assertRaisesRegex(OpenAIProviderError, "did not contain"):
                    OpenAIResponsesProvider()("system prompt", "user prompt")

    def test_includes_optional_temperature_tokens_and_reasoning(self) -> None:
        response_body = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"ok": True}),
                        }
                    ]
                }
            ]
        }
        with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "fake-key"}, clear=True):
            with patch(
                "resume_agent.experience_bank.openai_provider.urlopen",
                return_value=_FakeHTTPResponse(response_body),
            ) as request:
                OpenAIResponsesProvider(
                    model="gpt-5.4",
                    temperature=0.2,
                    max_output_tokens=900,
                    reasoning_effort="low",
                )("system prompt", "user prompt")

        sent_request = request.call_args.args[0]
        payload = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_output_tokens"], 900)
        self.assertEqual(payload["reasoning"]["effort"], "low")


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.stream = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, *args: object) -> bytes:
        return self.stream.read(*args)


if __name__ == "__main__":
    unittest.main()
