"""
MIT License

Copyright (c) 2021 Jake Sichley

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


from discord.ext import commands
from discord import Message
from typing import Any, Optional


class MessageReply(commands.CustomDefault):
    """
    Default parameter that returns a message reply from the current context.

    Attributes:
        required (bool): Whether the argument is required for the invocation context to be valid.
    """

    def __init__(self, *, required: bool = True) -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            required (bool): Whether the argument is required for the invocation context to be valid.
        """

        self.required = required

    async def default(self, ctx: commands.Context, param: Any) -> Optional[Message]:
        """
        Attempts to default the argument into a discord.Message object.

        Parameters:
            ctx (commands.Context): The invocation context.
            param (Any): The arg to be converted.

        Returns:
            (Optional[discord.Message]): The resulting discord.Message.
        """

        try:
            return ctx.message.reference.resolved
        except AttributeError:
            if self.required:
                raise commands.MissingRequiredArgument(param)
            else:
                return None
