"""
Gemini AI Service using LangChain
---------------------------------
Provides a robust interface to Google Gemini via LangChain's ChatGoogleGenerativeAI.
"""

import os
import logging
from typing import List, Dict, Optional, Any
import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)


class GeminiAIService:
    """
    Service for AI operations using Google Gemini via LangChain.
    """

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_AI_API_KEY", "")
        self.model_name = "gemini-2.5-flash"  

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if not self.is_configured:
            logger.error("GOOGLE_AI_API_KEY not set for Gemini.")
            return None

        return ChatGoogleGenerativeAI(
            google_api_key=self.api_key,
            model=self.model_name,
            convert_system_message_to_human=True,
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a single-turn response from Gemini.
        Adds debug logging for diagnosis.
        """
        client = self._get_client()
        if not client:
            logger.warning("Gemini client not available; using fallback.")
            return "Gemini not available"

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            result = client.invoke(messages)
            logger.debug(f"Gemini raw result: {result!r}")
            if hasattr(result, "content") and result.content:
                logger.info(f"Gemini response content: {result.content}")
                return result.content
            logger.warning(f"Gemini result missing 'content': {result!r}")
            return str(result)
        except Exception as e:
            logger.error(f"Gemini generate exception: {e}", exc_info=True)
            return f"Gemini error: {e}"

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and safely parse a JSON response from Gemini.
        Returns dict if valid JSON, else None. Logs all errors.
        """
        client = self._get_client()
        if not client:
            logger.error("Gemini client not available for generate_json.")
            return None

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            result = client.invoke(messages)
            logger.debug(f"Gemini generate_json raw result: {result!r}")
            content = getattr(result, "content", None)
            if not content:
                logger.error(f"Gemini generate_json: No content in result: {result!r}")
                return None
            logger.info(f"Gemini generate_json response content: {content}")
            # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
            stripped = re.sub(r'^```(?:json)?\s*', '', content.strip(), flags=re.IGNORECASE)
            stripped = re.sub(r'\s*```$', '', stripped.strip())

            def _repair_json(s: str) -> str:
                """
                Light JSON repair for known Gemini quirks:
                1. Remove orphan bare-string values inside objects.
                   e.g.  {"id": "c", "d", "text": "foo"}
                         → {"id": "c", "text": "foo"}
                   Pattern: ,  "some_string"  , "key":
                             ^^^^^^^^^^^^^^^ orphan – no colon follows it
                """
                # Remove orphan bare strings: , "val" , "key": ...
                s = re.sub(
                    r',\s*"(?:[^"\\]|\\.)*"\s*(?=,\s*"[^"]*"\s*:)',
                    '',
                    s,
                )
                # Remove leading orphan bare strings at object start: { "val" , "key": ...
                s = re.sub(
                    r'({\s*)"(?:[^"\\]|\\.)*"\s*,\s*(?="[^"]*"\s*:)',
                    r'\1',
                    s,
                )
                return s

            # Try to extract JSON from the response
            try:
                # Pass 1: direct parse (works when content is pure JSON or stripped cleanly)
                return json.loads(stripped)
            except Exception as e1:
                # Pass 2: light structural repair then reparse
                repaired = _repair_json(stripped)
                try:
                    return json.loads(repaired)
                except Exception:
                    pass
                # Pass 3: try to extract the outermost {...} substring then repair + parse
                logger.warning(f"Gemini generate_json: direct JSON parse failed: {e1}")
                match = re.search(r'\{.*\}', repaired, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except Exception as e2:
                        logger.error(f"Gemini generate_json: JSON substring parse failed: {e2}")
                logger.error(f"Gemini generate_json: Could not parse JSON from content: {content}")
                return None
        except Exception as e:
            logger.error(f"Gemini generate_json exception: {e}", exc_info=True)
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Multi-turn chat conversation with Gemini.
        """
        client = self._get_client()
        if not client:
            return "Gemini not available"

        chat_messages = []

        if system_prompt:
            chat_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_messages.append(AIMessage(content=msg["content"]))

        try:
            result = client.invoke(chat_messages)
            return result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return f"Gemini error: {e}"


# Singleton instance
_gemini_service: Optional[GeminiAIService] = None


def get_gemini_service() -> GeminiAIService:
    """Get or create GeminiAIService instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiAIService()
    return _gemini_service
