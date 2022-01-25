"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

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
from typing import Any, Union, Optional, List
from uuid import uuid4
from asyncio import TimeoutError
import discord
import logging
import io


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
        except discord.HTTPException as e:
            logging.warning(f'Context React Error. {e.status}. {e.text}')
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

        def reaction_check(pl: discord.RawReactionActionEvent):
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
            result = True if str(payload.emoji) == '✅' else False
        finally:
            if ephemeral:
                await prompt.delete()
            return result

    async def send(
            self, content: str = None, *, tts: bool = False, embed: discord.Embed = None, file: discord.File = None,
            files: List[discord.File] = None, delete_after: float = None, nonce: int = None,
            allowed_mentions: discord.AllowedMentions = None,
            reference: Union[discord.Message, discord.MessageReference] = None, mention_author: bool = None,
            safe_send: bool = False, escape_mentions: bool = False
    ) -> discord.Message:
        """
        Sends a message to the destination with the content given.

        Parameters:
            content (str): The content of the message to send.
            tts (bool): Indicates if the message should be sent using text-to-speech.
            embed (discord.Embed): The rich embed for the content.
            file (discord.File): The file to upload.
            files (List[discord.File]): A list of files to upload. Must be a maximum of 10.
            nonce (int): The nonce to use for sending this message. If the message was successfully sent, then the
                message will have a nonce with this value.
            delete_after (float): If provided, the number of seconds to wait in the background before deleting the
                message we just sent. If the deletion fails, then it is silently ignored.
            allowed_mentions (discord.AllowedMentions): Controls the mentions being processed in this message. If this
                is passed, then the object is merged with discord.Client.allowed_mentions. The merging behaviour only
                overrides attributes that have been explicitly passed to the object, otherwise it uses the attributes
                set in discord.Client.allowed_mentions. If no object is passed at all then the defaults given by
                discord.Client.allowed_mentions are used instead.
            reference (Union[discord.Message, discord.MessageReference]): A reference to the discord.Message to which
                you are replying, this can be created using discord.Message.to_reference or passed directly as a
                discord.Message. You can control whether this mentions the author of the referenced message using the
                discord.AllowedMentions.replied_user attribute of allowed_mentions or by setting mention_author.
            mention_author (Optional[bool]): If set, overrides the discord.AllowedMentions.replied_user attribute of
                allowed_mentions.
            safe_send (Optional[bool]): If the content length exceeds 2000 characters, whether to send the content as a
                file instead. Defaults to false.
            escape_mentions (Optional[bool]): Whether mentions in the message content should be escaped.
                Defaults to false.

        Returns:
            (discord.Message): The message that was sent.
        """

        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000 and safe_send:
            fp = io.BytesIO(content.encode())
            return await self.channel.send(
                file=discord.File(fp, filename='content.txt'),
                tts=tts, embed=embed, delete_after=delete_after, nonce=nonce, allowed_mentions=allowed_mentions,
                reference=reference, mention_author=mention_author
            )
        else:
            return await self.channel.send(
                content, file=file, files=files, tts=tts, embed=embed, delete_after=delete_after, nonce=nonce,
                allowed_mentions=allowed_mentions, reference=reference, mention_author=mention_author
            )
