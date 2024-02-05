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

from __future__ import annotations

import io
from asyncio import TimeoutError
from typing import Any, Union, Optional
from uuid import uuid4

import discord
from discord.ext import commands

import dreambot
from utils.logging_formatter import bot_logger


class Context(commands.Context['dreambot.DreamBot']):
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

    def __repr__(self) -> str:
        """
        Provides a string representation of this object.

        Parameters:
            None.

        Returns:
            (str).
        """

        name = self.__class__.__name__

        command_name = f'{self.command.__class__.__name__ if self.command else "Context"}'
        command = f'name={self.command.qualified_name if self.command else "None"}'
        cog = f'cog={self.command.cog.qualified_name if self.command and self.command.cog else "None"}'

        command_repr = f'<{command_name} {cog} {command}>'

        return f'<{name} command={command_repr} message={self.message!r}>'

    async def react(
            self,
            emoji: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
            *,
            raise_exceptions: bool = False
    ) -> None:
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
        except discord.HTTPException as e:
            bot_logger.warning(f'Context React Error. {e.status}. {e.text}')
            if raise_exceptions:
                raise

    async def tick(self, status: Optional[bool] = True, *, raise_exceptions: bool = False) -> None:
        """
        Attempts to a status reaction to the message.

        Parameters:
            status (bool): The type of reaction to add.
                True: ✅
                False: ❌
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

    async def confirmation_prompt(
            self, message: str, *, timeout: float = 30.0, ephemeral: bool = True
    ) -> Optional[bool]:
        """
        Prompts the user to confirm an action.

        Parameters:
            message (str): The actual prompt to send to user.
            timeout (float): How long the user has to respond. Default: 30.0s.
            ephemeral (bool): Whether the confirmation message should be deleted afterwards. Default: True.

        Returns:
            (Optional[bool]): The user's response to the prompt. None if timeout occurs or any general exception.
        """

        confirmation_emojis = ['✅', '❌']

        prompt = await self.send(message)

        for emoji in confirmation_emojis:
            await prompt.add_reaction(emoji)

        def reaction_check(pl: discord.RawReactionActionEvent) -> bool:
            """
            Our check criteria for determining the result of the prompt.

            Return a payload if:
                (1) The reaction was to the prompt message,
                and (2) The reaction was added (not removed),
                and (3) The user adding the reaction is our original author,
                and (4) The added reaction is one of our prompt reactions

            Parameters:
                pl (discord.RawReactionActionEvent): The payload data to check requirements against.

            Returns:
                (bool): Whether the payload meets our check criteria.
            """

            return pl.message_id == prompt.id and \
                pl.member == self.author and \
                pl.event_type == 'REACTION_ADD' and \
                str(pl.emoji) in confirmation_emojis

        result = None

        try:
            payload = await self.bot.wait_for('raw_reaction_add', timeout=timeout, check=reaction_check)
        except TimeoutError:
            result = None
        else:
            result = str(payload.emoji) == '✅'
        finally:
            if ephemeral:
                await prompt.delete()
            return result

    async def safe_send(self, content: Optional[str] = None, **kwargs: Any) -> discord.Message:
        """
        Sends a message safely to the destination with the content given.

        Parameters:
            content (str): The content of the message to send.

        Returns:
            (discord.Message): The message that was sent.
        """

        if content and len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop('file', None)
            return await self.send(file=discord.File(fp, filename='content.txt'), **kwargs)
        else:
            return await self.send(content)

    def dump(self) -> str:
        """
        Creates a 'pretty-printed' version of this context for logging.

        Parameters:
            None.

        Returns:
            (str): This context instance formatted for logging.
        """

        indent = '  '
        title = 'Context Dump:\n'

        guild_context = ''
        if self.guild is not None:
            guild_context += f'{indent}Guild\n'
            guild_context += f'{indent * 2}ID: {self.guild.id}\n'
            guild_context += f'{indent * 2}Name: {self.guild.name}\n'

        category_context = ''
        if self.message.channel.category is not None:
            category_context += f'{indent}Category\n'
            category_context += f'{indent * 2}ID: {self.channel.category.id}\n'
            category_context += f'{indent * 2}Name: {self.channel.category.name}\n'

        channel_context = f'{indent}Channel\n'
        channel_context += f'{indent * 2}ID: {self.channel.id}\n'
        channel_context += f'{indent * 2}Name: {self.channel.name}\n'

        message_context = f'{indent}Message\n'
        message_context += f'{indent * 2}ID: {self.message.id}\n'
        message_context += f'{indent * 2}Flags: {self.message.flags}\n'
        message_context += f'{indent * 2}Type: {self.message.type}\n'

        author_context = f'{indent}Author\n'
        author_context += f'{indent * 2}ID: {self.author.id}\n'
        author_context += f'{indent * 2}Global Name: {self.author.global_name}\n'
        author_context += f'{indent * 2}Display Name: {self.author.display_name}\n'
        author_context += f'{indent * 2}Permissions: {self.author.guild_permissions}\n'

        args_context = ''
        if self.args:
            args_context += f'{indent}Args\n'
            for index, arg in enumerate(self.args):
                args_context += f'{indent * 2}[{index}]: {arg}\n'

        kwargs_context = ''
        if self.kwargs:
            kwargs_context += f'{indent}Kwargs\n'
            for key, value in self.kwargs.items():
                kwargs_context += f'{indent * 2}{key}: {value}\n'

        return (
                title + guild_context + category_context + channel_context + message_context + author_context
                + args_context + kwargs_context
        )
