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

from dataclasses import dataclass, field
from typing import List, Optional, Union
from aiohttp import ClientSession, ClientResponseError
from context import Context
from network_utils import network_request, NetworkReturnType
from logging_formatter import bot_logger
import discord


@dataclass
class EmojiComponent:
    animated: Optional[bool] = False
    name: Optional[str] = ''
    id: Optional[int] = 0
    content: Optional[bytes] = field(default_factory=bytes, repr=False)
    status: str = ""
    failed: bool = False

    @property
    def extension(self) -> str:
        return 'gif' if self.animated else 'png'

    @property
    def viable(self) -> bool:
        return self.content and not self.failed

    def set_failed(self, status: str) -> None:
        self.failed = True
        self.status = status


class NoRemainingEmojiSlots(Exception):
    pass


class NoViableEmoji(Exception):
    pass


"""
    Process:
        Check duplicate emojis
        Check emoji limits
        Fetch content
        Create Emojis
        Send status
"""


class EmojiManager:
    def __init__(self, guild: discord.Guild, emojis: Union[EmojiComponent, List[EmojiComponent]]) -> None:
        self.__guild = guild
        self.__emojis = emojis if isinstance(emojis, list) else list(emojis)

    @property
    def __no_viable_emoji(self) -> bool:
        return all(x.failed for x in self.__emojis)

    @property
    def __existing_emoji_ids(self) -> List[int]:
        return [x.id for x in self.__guild.emojis]

    @property
    def __existing_emoji_names(self) -> List[str]:
        return [x.name for x in self.__guild.emojis]

    @property
    def __available_static_slots(self) -> int:
        return len([x for x in self.__guild.emojis if not x.animated])

    @property
    def __available_animated_slots(self) -> int:
        return len([x for x in self.__guild.emojis if x.animated])

    @property
    def __desired_static_emoji(self) -> List[EmojiComponent]:
        return [x for x in self.__emojis if not x.animated and not x.failed]

    @property
    def __desired_animated_emoji(self) -> List[EmojiComponent]:
        return [x for x in self.__emojis if x.animated and not x.failed]

    @property
    def status_message(self) -> str:
        successful_emoji = filter(lambda x: not x.failed and x.status, self.__emojis)
        failed_emoji = filter(lambda x: x.failed and x.status, self.__emojis)

        status = ""

        if successful_emoji:
            status += "**Successful Yoinks:**" + '\n'.join(x.status for x in successful_emoji)

        if failed_emoji:
            status += "\n\n**Failed Yoinks:**" + '\n'.join(x.status for x in failed_emoji)

        if not status:
            status = 'Failed to generate status message'
            bot_logger.error(
                f'Failed to Generate Yoink Status Message.\n'
                f'Details: Guild={self.__guild.id}, EmojiComponents={self.__emojis}'
            )

        return status

    async def yoink(self, ctx: Context, session: ClientSession) -> None:
        self.__check_for_duplicate_emoji()
        self.__check_emojis_slots()
        await self.__fetch_partial_emoji_content(session)
        await self.__create_emoji(ctx)

    def __check_for_duplicate_emoji(self) -> None:
        names = self.__existing_emoji_names
        ids = self.__existing_emoji_ids

        for emoji in self.__emojis:
            if emoji.name in names:
                emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `DuplicateName`')
            elif emoji.id in ids:
                emoji.set_failed(f'Emoji **{emoji.name}** ({emoji.id}) failed with Error: `DuplicateID`')

        if self.__no_viable_emoji:
            raise NoViableEmoji

    def __check_emojis_slots(self) -> None:
        if self.__available_static_slots == self.__available_animated_slots == 0:
            raise NoRemainingEmojiSlots('You have no remaining emoji slots - cannot yoink any emojis!')

        # fail extra static emojis
        for emoji in filter(lambda x: not x.animated and not x.failed, self.__emojis)[:self.__available_static_slots]:
            emoji: EmojiComponent
            emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `NotEnoughSlots`')

        # fail extra animated emoji
        for emoji in filter(lambda x: x.animated and not x.failed, self.__emojis)[:self.__available_animated_slots]:
            emoji: EmojiComponent
            emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `NotEnoughSlots`')

        if self.__no_viable_emoji:
            raise NoViableEmoji

    async def __fetch_partial_emoji_content(self, session: ClientSession) -> None:
        for emoji in filter(lambda x: not x.failed, self.__emojis):
            try:
                emoji.content = await network_request(
                    session,
                    f'https://cdn.discordapp.com/emojis/{emoji.id}.{emoji.extension}?size=96',
                    return_type=NetworkReturnType.BYTES
                )
            except ClientResponseError:
                emoji.set_failed = f'**{emoji.name}** failed with Error: `FailedToFetchContent`'

        if self.__no_viable_emoji:
            raise NoViableEmoji

    async def __create_emoji(self, ctx: Context) -> None:
        for emoji in filter(lambda x: not x.failed, self.__emojis):
            try:
                created_emoji = await self.__guild.create_custom_emoji(
                    name=emoji.name, image=emoji.content, reason=f'Yoink\'d by {ctx.author}'
                )
                emoji.status = f'Successfully yoink\'d emoji: **{emoji.name}**'
                try:
                    await ctx.react(created_emoji, raise_exceptions=True)
                except discord.HTTPException as e:
                    bot_logger.warning(f'Yoink Add Reaction Error. {e.status}. {e.text}')
            except discord.HTTPException as e:
                bot_logger.error(f'Yoink Creation Error. {e.status}. {e.text}')
                emoji.set_failed = f'**{emoji.name}** failed with Error: `FailedToCreateEmoji`'
