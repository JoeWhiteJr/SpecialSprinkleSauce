"""Dual-LLM client for the debate engine — Claude=bull, Gemini=bear, no cross-fallback."""

import itertools
import json
import logging
import re

from src.intelligence.wasden_watch.config import WasdenWatchSettings
from src.intelligence.wasden_watch.exceptions import LLMError

logger = logging.getLogger("debate_engine")


class DebateLLMClient:
    """Routes bull calls to Claude only, bear calls to Gemini only.

    call_judge() uses Claude with Gemini fallback for neutral evaluations
    (agreement detection, jury votes).
    """

    def __init__(self, settings: WasdenWatchSettings):
        self._settings = settings
        self._claude_key_cycle = (
            itertools.cycle(settings.claude_api_keys) if settings.claude_api_keys else None
        )
        self._gemini_key_cycle = (
            itertools.cycle(settings.gemini_api_keys) if settings.gemini_api_keys else None
        )

    def call_bull(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude for bull case. No fallback — raises LLMError on failure."""
        if self._claude_key_cycle is None:
            raise LLMError("No Claude API keys configured for bull researcher")
        try:
            response = self._call_claude(system_prompt, user_prompt)
            logger.info("Bull argument generated via Claude")
            return response
        except Exception as e:
            raise LLMError(f"Claude bull call failed: {e}") from e

    def call_bear(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini for bear case. No fallback — raises LLMError on failure."""
        if self._gemini_key_cycle is None:
            raise LLMError("No Gemini API keys configured for bear researcher")
        try:
            response = self._call_gemini(system_prompt, user_prompt)
            logger.info("Bear argument generated via Gemini")
            return response
        except Exception as e:
            raise LLMError(f"Gemini bear call failed: {e}") from e

    def call_judge(self, system_prompt: str, user_prompt: str) -> dict:
        """Call Claude (Gemini fallback) for neutral evaluation. Returns parsed JSON."""
        # Try Claude first
        if self._claude_key_cycle is not None:
            try:
                raw = self._call_claude(system_prompt, user_prompt)
                parsed = self._parse_response(raw)
                logger.info("Judge evaluation via Claude")
                return parsed
            except Exception as e:
                logger.warning(f"Claude judge call failed: {e}, falling back to Gemini")

        # Fallback to Gemini
        if self._gemini_key_cycle is not None:
            try:
                raw = self._call_gemini(system_prompt, user_prompt)
                parsed = self._parse_response(raw)
                logger.info("Judge evaluation via Gemini fallback")
                return parsed
            except Exception as e:
                raise LLMError(f"Both Claude and Gemini judge calls failed. Last error: {e}") from e

        raise LLMError("No API keys configured for judge evaluation")

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
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
        """Parse LLM response as JSON — same strategy as wasden_watch llm_client."""
        text = raw.strip()

        # Direct JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Bare JSON object
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise LLMError(f"Could not parse judge response as JSON. Raw: {text[:500]}")
