"""
MIT License

Copyright (c) 2019-Present Jake Sichley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re
from os import getenv
from json import JSONDecodeError
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import quote as url_quote

from google import genai
from langfuse import get_client as get_langfuse_client
from pydantic import ValidationError
from langfuse.api.core import ApiError as LangfuseAPIError

from utils.observability.loggers import bot_logger
from utils.models.gemini.fact_check_models import FACT_CHECK_DEBUG_SCOPE, FactCheckResponse, build_fact_check_config

if TYPE_CHECKING:
    from langfuse import Langfuse


class GeminiService:
    """
    A service class for interacting with the Gemini API.

    Attributes:
        _model (str): The name of the Gemini API model.
        _client (genai.Client): The Gemini API client.
        _langfuse (langfuse.Langfuse): The bot's Langfuse client.
    """

    def __init__(self) -> None:
        """
        The constructor for the GeminiService class.

        Parameters:
            None.

        Returns:
            None.
        """

        self._model = 'gemini-3.1-flash-lite'
        self._client = genai.Client(api_key=getenv('GEMINI_TOKEN'))
        self._langfuse: Langfuse = get_langfuse_client()

    async def fact_check(
        self, message: str, additional_context: List[str], bot_nickname: str, debug_identifier: str
    ) -> FactCheckResponse:
        """
        Performs a fact check on a given message using the Gemini API.

        Parameters:
            message (str): The message to fact check.
            additional_context (List[str]): A list of additional messages to provide as context.
            debug_identifier (str): A unique identifier for debugging purposes.
            bot_nickname (str): The bot's nickname for this context.

        Returns:
            (FactCheckResponse): A FactCheckResponse object containing the results of the fact check.
        """

        if system_prompt := await self._get_system_prompt():
            response = await self._client.aio.models.generate_content(
                model=self._model,
                config=build_fact_check_config(system_prompt),
                contents=_build_fact_check_prompt(message, additional_context, bot_nickname),
            )
        else:
            return FactCheckResponse(  # type: ignore[call-arg]  # this is actually optional
                is_actionable=False, refusal_reason='This feature is currently unavailable due to an internal error.'
            )

        return _clean_and_parse_json(response.text, debug_identifier)

    async def _get_system_prompt(self) -> Optional[str]:
        """
        A helper method for asynchronously fetching the fact check system prompt.

        Parameters:
            None.

        Returns:
            (Optional[str]): The fact check system prompt.
        """

        # https://github.com/langfuse/langfuse/issues/8006#issue-3249047350
        # Langfuse's asynchronous methods are auto-generated from an OpenAPI spec and do not automatically encode
        # url parameters like the synchronous `get_prompt` variant does
        prompt_identifier = url_quote('Discord-Bot/Gemini/fact-check', safe='')

        try:
            system_prompt = await self._langfuse.async_api.prompts.get(prompt_identifier)

            if isinstance(system_prompt.prompt, str):
                return system_prompt.prompt
            bot_logger.error(
                f'Prompt identifer `Discord-Bot/Gemini/fact-check` did not return a text-based prompt. '
                f'Possible model mismatch: `langfuse.model.Prompt_Chat` versus `langfuse.model.Prompt_Text`'
            )
            return None
        except LangfuseAPIError as e:
            bot_logger.error(f'Failed to fetch fact check system prompt. Error: {e}')
            return None

    async def close(self) -> None:
        """
        Closes the Gemini API client.

        Parameters:
            None.

        Returns:
            None.
        """

        self._client.close()
        await self._client.aio.aclose()


def _build_fact_check_prompt(statement: str, context_list: List[str], bot_nickname: str) -> str:
    """
    Builds a prompt for the Gemini API to perform a fact check.

    Parameters:
        statement (str): The statement to fact check.
        context_list (List[str]): A list of additional messages to provide as context.
        bot_nickname (str): The bot's nickname for this context.

    Returns:
        (str): The prompt to send to the Gemini API.
    """

    # Format the context list into a clearly labeled block
    formatted_context = '\n'.join([f'- {msg}' for msg in context_list]) if context_list else 'NONE'

    return f"""
    TARGET STATEMENT:
    "{statement}"

    POTENTIAL CONTEXT MESSAGES:
    {formatted_context}
    
    REFERENCE NICKNAME:
    <nickname>
    {bot_nickname}
    </nickname>
    """


def _clean_and_parse_json(raw_response: Optional[str], debug_identifier: str) -> FactCheckResponse:
    """
    Attempts to coerce a raw string (potentially containing markdown) into a FactCheckResponse.

    Parameters:
        raw_response (str): The raw text to parse.
        debug_identifier (str): A unique identifier for debugging purposes.

    Returns:
        (FactCheckResponse): A FactCheckResponse object.
    """

    if raw_response is None:
        bot_logger.debug(f'{debug_identifier} Fact check returned an empty response.', extra=FACT_CHECK_DEBUG_SCOPE)

        return FactCheckResponse(  # type: ignore[call-arg]  # this is actually optional
            is_actionable=False, refusal_reason='System Error: Model did not generate a response.'
        )

    try:
        text = re.sub(r'^```(json)?', '', raw_response, flags=re.MULTILINE)
        text = re.sub(r'```$', '', text, flags=re.MULTILINE)
        text = text.strip()

        parsed_model = FactCheckResponse.model_validate_json(text)
        bot_logger.debug(
            f'{debug_identifier} Fact check response parsed successfully. Parsed model:\n{parsed_model}',
            extra=FACT_CHECK_DEBUG_SCOPE,
        )
        return parsed_model

    except (JSONDecodeError, ValidationError) as e:
        print(f'Failed to parse model output: {e}')
        print(f'Raw output was: {raw_response}')

        bot_logger.debug(
            f'{debug_identifier} Fact check returned a response that could not be parsed. Error: {type(e)} - {e}. '
            f'Raw response:\n{raw_response}',
            extra=FACT_CHECK_DEBUG_SCOPE,
        )

        return FactCheckResponse(  # type: ignore[call-arg]  # this is actually optional
            is_actionable=False, refusal_reason='System Error: Model generated invalid JSON format.'
        )
