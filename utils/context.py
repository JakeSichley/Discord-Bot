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
from typing import Any, Union, Optional
from uuid import uuid4
import discord


class Context(commands.Context):
    """
    A Custom commands.Context class.

    Attributes:
        id (UUID): The UUID of the context instance. Used for logging purposes.
    """

    def __init__(self, **kwargs: Any):
        """
        The constructor for the Context class.

        Parameters:
            kwargs (**kwargs): Any keyword arguments that should be passed to the parent class.

        Returns:
            None.
        """

        super().__init__(**kwargs)
        self.id = uuid4()

    async def react(self, emoji: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
                    *, raise_exceptions: bool = False) -> None:
        """
        Attempts to add the specified emoji to the message.

        Parameters:
            emoji (Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str]): The emoji to add.
            raise_exceptions (bool): Whether exceptions should be raised. Defaults to False.

        Returns:
            None.
        """

        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            if raise_exceptions:
                raise

    async def tick(self, status: Optional[bool] = True, *, raise_exceptions: bool = False) -> None:
        """
        Attempts to a status reaction to the message.

        Parameters:
            status (bool): The type of reaction to add.
                True: ✅
                False:
                None: ✖
            raise_exceptions (bool): Whether exceptions should be raised. Defaults to False.

        Returns:
            None.
        """

        reactions = {
            True: '✅',
            False: '❌',
            None: '✖'
        }

        await self.react(reactions[status], raise_exceptions=raise_exceptions)
