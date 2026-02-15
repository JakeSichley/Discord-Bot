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

from typing import List, Optional

from pydantic import Field, BaseModel
from google.genai import types

SYSTEM_INSTRUCTION = """
You are a dual-mode AI: part precision Fact-Checker, part Comedian.

[STRICT OUTPUT FORMAT]
You must return a single JSON object. Do not include any conversational text outside the JSON.
The JSON object must have these fields:
{
    "is_actionable": boolean (true/false),
    "refusal_reason": string or null (if not checkable),
    "verdict": string ("True", "False", "Misleading", "Unverified", etc.) or null,
    "short_explanation": string (max 2 sentences),
    "witty_comment": string (max 2 sentences),
    "supporting_sources": list of strings (URLs found in search)
}

[ASSUMPTIONS]
- If required and otherwise unspecified, treat the context as originating from the United States of America.

STEP 1: CLASSIFY
Analyze the user's statement.
- Is it an **Objective Claim**? (e.g. "The earth is flat", "Shrek was released in 2001") -> GO TO MODE A.
- Is it a **Subjective Opinion/Preference**? (e.g. "Pineapple belongs on pizza", "Cats are better than dogs", "Chivalry is dead") -> GO TO MODE B.
- Is it **Noise**? (e.g. Commands: "Write me a poem.", Greetings/Noise: "Hello", "test", "asdf") -> GO TO MODE C.

STEP 2: EXECUTE MODE
[MODE A: The Researcher]
- Set "is_actionable": true
- Perform a rigorous Google Search.
- Fill "verdict".
- Fill "short_explanation" with a concise, serious summary of the evidence.
- Fill "supporting_sources".
- Leave "witty_comment" null.

[MODE B: The Comedian]
- Set "is_actionable": true
- DO NOT search.
- Fill "witty_comment" with a short, funny, light-hearted reaction to their opinion. Keep it friendly/playful.
- Fill "verdict" with something funny and light-hearted that matches "witty_comment" (e.g.: 'Maybe', 'Probably', 'Definitely', 'True', 'False', 'Definitely Not')
- Leave "short_explanation" null.
- Set "supporting_sources": []

[MODE C: Unactionable]
- Set "is_actionable": false
- Set "supporting_sources": []
- DO NOT search.
- Provide "refusal_reason". STOP there.
"""


FACT_CHECK_CONFIG = types.GenerateContentConfig(
    temperature=0.7,
    tools=[types.Tool(google_search=types.GoogleSearch())],
    system_instruction=SYSTEM_INSTRUCTION,
)


class FactCheckResponse(BaseModel):
    """
    A Pydantic model for the response from the fact-checking API.

    Attributes:
        is_actionable (bool): Whether the input is a checkable claim.
        refusal_reason (Optional[str]): The reason for refusal if the input is not checkable.
        verdict (Optional[str]): The verdict of the claim.
        short_explanation (Optional[str]): A short explanation of the verdict.
        witty_comment (Optional[str]): A witty comment of the verdict.
        supporting_sources (List[str]): A list of URLs supporting the verdict.
    """

    is_actionable: bool = Field(
        ..., description='Set to False if the input is a question, command, subjective opinion, or greeting.'
    )
    refusal_reason: Optional[str] = Field(
        None, description="If is_actionable is False, explain why (e.g. 'Input is a question, not a claim')."
    )
    verdict: Optional[str] = Field(
        None, description='The verdict of the claim. Required ONLY if is_actionable is True.'
    )
    short_explanation: Optional[str] = Field(
        None, description='A 1-2 sentence explanation of the verdict. Required ONLY if is_actionable is True.'
    )
    witty_comment: Optional[str] = Field(
        None,
        description='A 1-2 sentence witty response if this claim is not strictly checkable. '
        'Required ONLY if is_actionable is True.',
    )
    supporting_sources: List[str] = Field(default_factory=list, description='URLs supporting the verdict.')

    @property
    def formatted_refusal_reason(self) -> str:
        """
        Returns a formatted refusal reason.

        Parameters:
            None.

        Returns:
            (str).
        """

        return self.refusal_reason if self.refusal_reason else 'No refusal reason was provided for this request'

    @property
    def response_content(self) -> Optional[str]:
        """
        Convenience method for accessing the main response object.

        Parameters:
            None.

        Returns:
            (Optional[str]).
        """

        return self.short_explanation or self.witty_comment

    @property
    def formatted_verdict(self) -> str:
        """
        Returns a formatted verdict.

        Parameters:
            None.

        Returns:
            (str): The formatted verdict.
        """
        components: List[str] = []

        if self.verdict:
            components.append(f'**Verdict: {self.verdict}**')

        if self.response_content:
            components.append(self.response_content)

        if self.supporting_sources:
            components.append(
                'Sources:\n'
                + '\n'.join(f'{index + 1}) <{source}>' for index, source in enumerate(self.supporting_sources))
            )

        if not components:
            return 'Unable to generate fact-checking response - please try again later.'

        return '\n\n'.join(components)
