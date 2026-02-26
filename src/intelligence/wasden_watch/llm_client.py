"""Dual-LLM client with Claude primary, Gemini fallback, and round-robin key rotation."""

import itertools
import json
import logging
import re

from .config import WasdenWatchSettings
from .exceptions import LLMError, VerdictParsingError

logger = logging.getLogger("wasden_watch")


class LLMClient:
    """LLM client with Claude primary and Gemini fallback, using key rotation."""

    def __init__(self, settings: WasdenWatchSettings):
        self._settings = settings
        self._claude_key_cycle = (
            itertools.cycle(settings.claude_api_keys) if settings.claude_api_keys else None
        )
        self._gemini_key_cycle = (
            itertools.cycle(settings.gemini_api_keys) if settings.gemini_api_keys else None
        )

    def generate_verdict(self, system_prompt: str, user_prompt: str) -> tuple[dict, str]:
        """Generate a verdict using Claude with Gemini fallback.

        Args:
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with ticker analysis request.

        Returns:
            Tuple of (parsed JSON dict, model name used).

        Raises:
            LLMError: If both Claude and Gemini fail.
            VerdictParsingError: If response cannot be parsed as valid JSON.
        """
        # Try Claude first
        if self._claude_key_cycle is not None:
            try:
                raw_response = self._call_claude(system_prompt, user_prompt)
                parsed = self._parse_response(raw_response)
                logger.info(f"Verdict generated via Claude ({self._settings.claude_model})")
                return parsed, self._settings.claude_model
            except VerdictParsingError:
                raise
            except Exception as e:
                logger.warning(f"Claude call failed: {e}, falling back to Gemini")

        # Fallback to Gemini
        if self._gemini_key_cycle is not None:
            try:
                raw_response = self._call_gemini(system_prompt, user_prompt)
                parsed = self._parse_response(raw_response)
                logger.info(f"Verdict generated via Gemini fallback ({self._settings.gemini_model})")
                return parsed, self._settings.gemini_model
            except VerdictParsingError:
                raise
            except Exception as e:
                logger.warning(f"Gemini call also failed: {e}")
                raise LLMError(f"Both Claude and Gemini failed. Last error: {e}")

        raise LLMError("No API keys configured for either Claude or Gemini")

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude API with round-robin key rotation.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.

        Returns:
            Raw response text from Claude.
        """
        import anthropic

        key = next(self._claude_key_cycle)
        client = anthropic.Anthropic(api_key=key)

        message = client.messages.create(
            model=self._settings.claude_model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API with round-robin key rotation.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.

        Returns:
            Raw response text from Gemini.
        """
        import google.generativeai as genai

        key = next(self._gemini_key_cycle)
        genai.configure(api_key=key)

        model = genai.GenerativeModel(
            model_name=self._settings.gemini_model,
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=self._settings.temperature,
                max_output_tokens=self._settings.max_tokens,
            ),
        )

        return response.text

    def _parse_response(self, raw: str) -> dict:
        """Parse LLM response as JSON.

        Args:
            raw: Raw response text.

        Returns:
            Parsed JSON dict.

        Raises:
            VerdictParsingError: If response is not valid JSON.
        """
        # Try direct JSON parsing first
        text = raw.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find a JSON object in the text
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise VerdictParsingError(
            f"Could not parse LLM response as JSON. Raw response: {text[:500]}"
        )
