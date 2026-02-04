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

from enum import Enum
from typing import TYPE_CHECKING, List, Union, Optional
from dataclasses import field, dataclass

import discord
from aiohttp import ClientError

from utils.network.exceptions import EmptyResponseError
from utils.observability.loggers import bot_logger

if TYPE_CHECKING:
    from utils.context import Context
    from utils.network.client import NetworkClient


@dataclass
class EmojiComponent:
    """
    A dataclass that represents the raw components of an Emoji.
        Optional typing here does not imply that these components are optional for constructing real emoji,
        merely that they are optional during EmojiComponent initialization.

    Attributes:
        animated (bool): Whether the emoji is animated.
        name (str): The name of the emoji.
        id (Optional[int]): The internal (Discord) id of the emoji.
        content (Optional[bytes]): The emoji's content.
        status (str): The status message associated with this emoji. Generally contains success or failure information.
        failed (bool): Whether yoinking this emoji has failed at some point during execution.
    """

    animated: bool = False
    name: Optional[str] = ''
    id: Optional[int] = 0
    content: Optional[bytes] = field(default_factory=bytes, repr=False)
    status: str = ''
    failed: bool = False

    @property
    def extension(self) -> str:
        """
        Returns the file extension for this emoji.

        Parameters:
            None.

        Returns:
            (str).
        """

        return 'gif' if self.animated else 'webp'

    @property
    def viable(self) -> bool:
        """
        Whether this emoji can be used in an emoji creation request to Discord.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return bool(self.content) and not self.failed

    def set_failed(self, status: str) -> None:
        """
        Sets this emoji's failure state to True and sets the status message.

        Parameters:
            status (str): The status message to set.

        Returns:
            None.
        """

        self.failed = True
        self.status = status


class FailureStage(Enum):
    """
    An Enum class that representing the stage at which an exception was raised.
    """

    UNKNOWN = -1
    NO_NETWORKING = 0
    NETWORKING = 1


class FailureStageError(Exception):
    """
    An Exception class that contains `FailureStage` information.

    Attributes:
        stage (FailureStage): The stage the exception was raised at.
    """

    def __init__(self, stage: FailureStage = FailureStage.UNKNOWN) -> None:
        """
        The constructor for the UtilityFunctions class.

        Parameters:
            stage (FailureStage): The stage the exception was raised at.
        """

        self.stage: FailureStage = stage


class NoRemainingEmojiSlotsError(FailureStageError):
    """
    Error raised when the invocation guild has no remaining emoji slots.
    """


class NoViableEmojiError(FailureStageError):
    """
    Error raised when all potential emoji are marked as failed during execution.
    """


class NoEmojisFoundError(FailureStageError):
    """
    Error raised when no `EmojiComponents` are able to be extract from the source message or provided arguments.
    """


class EmojiManager:
    """
    Managers the full execution flow of turning raw emoji components (EmojiComponents) into full-fledged emoji.

    The required process is as follows:
        Check for duplicate emoji requests (id and name)
        Check for emoji slot limits (static and animated)
            Fail extraneous emojis, allowing for partial completion
        Fetch emoji content from Discord
        Create emojis in the target Guild
        Send a status message detailing the manager's execution.

    Checks are performed at each step to ensure there are still viable emoji to use in the next step.

    Attributes:
        __guild (discord.Guild): The target Guild.
        __emojis (List[__emojis]): The list of desired EmojiComponents.
    """

    def __init__(self, guild: discord.Guild, emojis: Union[EmojiComponent, List[EmojiComponent]]) -> None:
        """
        The constructor for the EmojiManager class.

        Parameters:
            guild (discord.Guild): The target Guild.
            emojis (Union[EmojiComponent, List[EmojiComponent]]): The EmojiComponent(s) to process.
                Converted to a list for iterability.
        """

        self.__guild = guild
        self.__emojis = emojis if isinstance(emojis, list) else [emojis]

    @property
    def __no_viable_emoji(self) -> bool:
        """
        Returns whether all emoji have failed.

        Parameters:
            None.

        Returns:
            (bool).
        """

        return all(x.failed for x in self.__emojis)

    @property
    def __existing_emoji_ids(self) -> List[int]:
        """
        Returns a list of the all the ids of the guild's existing emoji.

        Parameters:
            None.

        Returns:
            (List[int]).
        """

        return [x.id for x in self.__guild.emojis]

    @property
    def __existing_emoji_names(self) -> List[str]:
        """
        Returns a list of the all the names of the guild's existing emoji.

        Parameters:
            None.

        Returns:
            (List[str]).
        """

        return [x.name for x in self.__guild.emojis]

    @property
    def __available_static_slots(self) -> int:
        """
        Returns the number of available static emoji slots the guild current has.

        Parameters:
            None.

        Returns:
            (int).
        """

        return self.__guild.emoji_limit - len([x for x in self.__guild.emojis if not x.animated])

    @property
    def __available_animated_slots(self) -> int:
        """
        Returns the number of available animated emoji slots the guild current has.

        Parameters:
            None.

        Returns:
            (int).
        """

        return self.__guild.emoji_limit - len([x for x in self.__guild.emojis if x.animated])

    def status_message(self) -> str:
        """
        Generates a message summarizing the statuses all emoji.

        Parameters:
            None.

        Returns:
            (str): The status message.
        """

        # okay to copy since we're not modifying the components
        successful_emoji = list(filter(lambda x: not x.failed and x.status, self.__emojis))
        failed_emoji = list(filter(lambda x: x.failed and x.status, self.__emojis))

        status = ''

        if successful_emoji:
            status += '**Successful Yoinks:**\n' + '\n'.join(x.status for x in successful_emoji)

        if failed_emoji:
            status += '\n\n**Failed Yoinks:**\n' + '\n'.join(x.status for x in failed_emoji)

        if not status:
            status = 'Failed to generate status message'
            bot_logger.error(
                f'Failed to Generate Yoink Status Message.\n'
                f'Details: Guild={self.__guild.id}, EmojiComponents={self.__emojis}'
            )

        return status

    async def yoink(self, ctx: Context, network_client: NetworkClient) -> None:
        """
        Primary driver method. Performs all checks and required requests for creating emojis.

        This method exists to ensure all internal methods are called in the correct order, since all methods
        modify the internal state of the EmojiComponents list. Checks are performed in an order designed to reduce
        network requests.

        Parameters:
            ctx (Context): The invocation context.
            network_client (NetworkClient): The bot's network client.

        Raises:
            NoEmojisFound (Directly)
            NoViableEmoji (Indirectly)
            NoRemainingEmojiSlots (Indirectly)

        Returns:
            None.
        """

        if not self.__emojis:
            raise NoEmojisFoundError(FailureStage.NO_NETWORKING)

        self.__check_for_duplicate_emoji()
        self.__check_emojis_slots()
        await self.__fetch_partial_emoji_content(network_client)
        await self.__create_emoji(ctx)

    def __check_for_duplicate_emoji(self) -> None:
        """
        Checks the potential emoji's names and id's versus the guild's existing emoji.

        Parameters:
            None.

        Raises:
            NoViableEmoji

        Returns:
            None.
        """

        names = self.__existing_emoji_names
        ids = self.__existing_emoji_ids

        for emoji in self.__emojis:
            if emoji.id in ids:
                emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `DuplicateID [{emoji.id}]`')
            elif emoji.name in names:
                emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `DuplicateName`')

        if self.__no_viable_emoji:
            raise NoViableEmojiError(FailureStage.NO_NETWORKING)

    def __check_emojis_slots(self) -> None:
        """
        Checks the guild's number of available static and animated emoji slots.
        If there are 0 combined slots available, NoRemainingEmojiSlots is raised. Otherwise, emojis that would exceed
        the guild's available slots are failed, allowing for partial creation.

        Parameters:
            None.

        Raises:
            NoRemainingEmojiSlots
            NoViableEmoji

        Returns:
            None.
        """

        if self.__available_static_slots == self.__available_animated_slots == 0:
            raise NoRemainingEmojiSlotsError(FailureStage.NO_NETWORKING)

        # fail extra static emojis
        for index, emoji in enumerate(filter(lambda x: not x.animated and not x.failed, self.__emojis)):
            if index >= self.__available_static_slots:
                emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `NotEnoughSlots [Static]`')

        # fail extra animated emoji
        for index, emoji in enumerate(filter(lambda x: x.animated and not x.failed, self.__emojis)):
            if index >= self.__available_animated_slots:
                emoji.set_failed(f'Emoji **{emoji.name}** failed with Error: `NotEnoughSlots [Animated]`')

        if self.__no_viable_emoji:
            raise NoViableEmojiError(FailureStage.NO_NETWORKING)

    async def __fetch_partial_emoji_content(self, network_client: NetworkClient) -> None:
        """
        Fetches the emoji's content from Discord's CDN.

        Parameters:
            network_client (NetworkClient): The bot's network client.

        Raises:
            NoViableEmoji.

        Returns:
            None.
        """

        for emoji in filter(lambda x: not x.failed, self.__emojis):
            try:
                emoji.content = await network_client.fetch_bytes(
                    f'https://cdn.discordapp.com/emojis/{emoji.id}.{emoji.extension}?size=96&quality=lossless',
                    raise_for_empty_response=True,
                )
            except (ClientError, EmptyResponseError):
                emoji.set_failed(f'**{emoji.name}** failed with Error: `ContentDoesNotExist`')

        if self.__no_viable_emoji:
            raise NoViableEmojiError(FailureStage.NETWORKING)

    async def __create_emoji(self, ctx: Context) -> None:
        """
        Uses the completed EmojiComponents to create emojis.

        Parameters:
            None.

        Raises:
            NoViableEmoji.

        Returns:
            None.
        """

        for emoji in filter(lambda x: not x.failed, self.__emojis):
            try:
                if emoji.name is None or emoji.content is None:
                    emoji.set_failed(f'**{emoji.name}** failed with Error: `MissingNameOrContent`')
                    continue

                created_emoji = await self.__guild.create_custom_emoji(
                    name=emoji.name, image=emoji.content, reason=f"Yoink'd by {ctx.author}"
                )
                emoji.status = f"Successfully yoink'd emoji: **{emoji.name}**"
                try:
                    await ctx.react(created_emoji, raise_exceptions=True)
                except discord.HTTPException as e:
                    bot_logger.warning(f'Yoink Add Reaction Error. {e.status}. {e.text}')
            except discord.HTTPException as e:
                bot_logger.error(f'Yoink Creation Error. {e.status}. {e.text}')
                emoji.set_failed(f'**{emoji.name}** failed with Error: `FailedToCreateEmoji`')

        if self.__no_viable_emoji:
            raise NoViableEmojiError(FailureStage.NETWORKING)
