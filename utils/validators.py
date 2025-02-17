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

import parsedatetime  # type: ignore[import-untyped]
from discord.ext import commands

ForbiddenCharacterSet = set('_~#/\`><@*')


class ForbiddenCharacters(commands.BadArgument):
    def __init__(self) -> None:
        super().__init__(f'Input contained one or more Forbidden Characters: {", ".join(ForbiddenCharacterSet)}')


def check_for_forbidden_characters(string: str) -> None:
    """
    Checks if the provided string contains any of the forbidden characters.

    Parameters:
        string (str): The string to check for forbidden characters.

    Raises:
        ForbiddenCharacters: Whether the string contains any of the forbidden characters.

    Returns:
        None.
    """

    if set(string).intersection(ForbiddenCharacterSet):
        raise ForbiddenCharacters
