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
from typing import List, Optional

from google import genai
from pydantic import ValidationError

from utils.models.gemini.fact_check_models import FACT_CHECK_CONFIG, FactCheckResponse


class GeminiService:
    """
    A service class for interacting with the Gemini API.

    Attributes:
        client (genai.Client): The Gemini API client.
    """

    def __init__(self) -> None:
        """
        The constructor for the GeminiService class.

        Parameters:
            None.

        Returns:
            None.
        """

        self.client = genai.Client(api_key=getenv('GEMINI_TOKEN'))

    async def fact_check(self, message: str, additional_context: List[str]) -> FactCheckResponse:
        """
        Performs a fact check on a given message using the Gemini API.

        Parameters:
            message (str): The message to fact check.
            additional_context (List[str]): A list of additional messages to provide as context.

        Returns:
            (FactCheckResponse): A FactCheckResponse object containing the results of the fact check.
        """

        response = await self.client.aio.models.generate_content(
            model='gemini-2.0-flash',
            config=FACT_CHECK_CONFIG,
            contents=_build_fact_check_prompt(message, additional_context),
        )

        print(response.text)

        return _clean_and_parse_json(response.text)

    async def close(self) -> None:
        """
        Closes the Gemini API client.

        Parameters:
            None.

        Returns:
            None.
        """

        self.client.close()
        await self.client.aio.aclose()


def _build_fact_check_prompt(statement: str, context_list: List[str]) -> str:
    """
    Builds a prompt for the Gemini API to perform a fact check.

    Parameters:
        statement (str): The statement to fact check.
        context_list (List[str]): A list of additional messages to provide as context.

    Returns:
        (str): The prompt to send to the Gemini API.
    """

    # Format the context list into a clearly labeled block
    formatted_context = '\n'.join([f'- {msg}' for msg in context_list])

    return f"""
    TARGET STATEMENT:
    "{statement}"

    POTENTIAL CONTEXT MESSAGES (Use only if relevant to the statement above):
    {formatted_context}
    """


def _clean_and_parse_json(raw_response: Optional[str]) -> FactCheckResponse:
    """
    Attempts to coerce a raw string (potentially containing markdown) into a FactCheckResponse.

    Parameters:
        raw_response (str): The raw text to parse.

    Returns:
        (FactCheckResponse): A FactCheckResponse object.
    """

    if raw_response is None:
        return FactCheckResponse(  # type: ignore[call-arg]  # this is actually optional
            is_actionable=False, refusal_reason='System Error: Model did not generate a response.'
        )

    try:
        text = re.sub(r'^```(json)?', '', raw_response, flags=re.MULTILINE)
        text = re.sub(r'```$', '', text, flags=re.MULTILINE)
        text = text.strip()

        return FactCheckResponse.model_validate_json(text)

    except (JSONDecodeError, ValidationError) as e:
        print(f'Failed to parse model output: {e}')
        print(f'Raw output was: {raw_response}')

        return FactCheckResponse(  # type: ignore[call-arg]  # this is actually optional
            is_actionable=False, refusal_reason='System Error: Model generated invalid JSON format.'
        )
