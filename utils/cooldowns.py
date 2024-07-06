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

from datetime import datetime
from datetime import timedelta
from typing import (
    Tuple, Optional, TypeVar, Union
)

from discord import Interaction
from discord.app_commands import Command, ContextMenu, CommandOnCooldown
from discord.ext import commands
from fuzzywuzzy import fuzz  # type: ignore

# noinspection PyUnresolvedReferences
import dreambot  # needed for typehint, actual usage causes circular import
from utils.context import Context

CooldownContext = TypeVar('CooldownContext', Context, Interaction['dreambot.DreamBot'])


class CooldownMapping:
    """
    Stores Cooldown information related to various mappings (the most common being User: CooldownMapping).
    Used to enforce dynamically changing cooldowns based on the number of consecutive failures.

    Attributes:
        __count (int): The number of consecutive command failures for this mapping.
        __start_time (Optional[datetime]): The time the current cooldown started. None if there isn't a cooldown.
        __max_cooldown (float): The maximum allowable cooldown duration.
        __impose_cooldowns_threshold (int): The number of allowable failures before a cooldown will be enforced.
    """

    def __init__(self, max_cooldown: float = 604800, impose_cooldowns_threshold: int = 2) -> None:
        """
        The constructor for the CooldownMapping class.

        Parameters:
            max_cooldown (float): The maximum allowable cooldown duration. Default: 1 week (in seconds).
            impose_cooldowns_threshold (int): The number of allowable failures before a cooldown will be enforced.

        Returns:
            None.
        """

        self.__count: int = 0
        self.__start_time: Optional[datetime] = None
        self.__max_cooldown: float = max_cooldown
        self.__impose_cooldowns_threshold: int = impose_cooldowns_threshold

    def __repr__(self) -> str:
        """
        Provides a string representation of this object.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f'{self.__count=}, {self.__start_time=}, {self.__max_cooldown=}'

    @property
    def base_duration(self) -> float:
        """
        Returns the duration a cooldown of `n` failures should be.

        Parameters:
            None.

        Returns:
            (float).
        """

        return min(2 ** (5 + self.__count), self.__max_cooldown)  # type: ignore[no-any-return]

    @property
    def remaining_cooldown(self) -> Optional[commands.Cooldown]:
        """
        Calculates the remaining cooldown for the current failure count, if any.
        Cooldowns may not be enforced depending on the `impose cooldowns` threshold.

        Parameters:
            None.

        Returns:
            (Optional[commands.Cooldown]).
        """

        if self.__count < self.__impose_cooldowns_threshold or self.__start_time is None:
            return None

        remaining_time = (self.__start_time + timedelta(seconds=self.base_duration)) - datetime.now()

        if remaining_time.total_seconds() <= 0:
            return None

        return commands.Cooldown(1, remaining_time.total_seconds())

    def increment_failure_count(self) -> None:
        """
        Increments the failure count and sets the current cooldown start time to now.

        Parameters:
            None.

        Returns:
            None.
        """

        self.__count += 1
        self.__start_time = datetime.now()

    def reset(self) -> None:
        """
        Resets the failure count and removes the cooldown start time.

        Parameters:
            None.

        Returns:
            None.
        """

        self.__count = 0
        self.__start_time = None


async def cooldown_predicate(ctx: CooldownContext) -> bool:
    """
    The dynamic cooldown predicate, designed to be used in a command.Check.
    Retrieves the current dynamic cooldown information from the bot for the given context, raising a
        commands.CommandOnCooldown error if a cooldown exists, or otherwise returning true.

    Parameters:
        ctx (Context) The invocation context.

    Raises:
        commands.CommandOnCooldown.

    Returns:
        (bool).
    """

    command_name, author_id = get_cooldown_keys(ctx)

    if command_name is None or author_id is None:
        return True

    if isinstance(ctx, Context):
        bot = ctx.bot
    else:
        bot = ctx.client

    command_cooldown_mapping = bot.dynamic_cooldowns.get(command_name)

    if command_cooldown_mapping is None:
        return True

    author_mapping = command_cooldown_mapping.get(author_id, CooldownMapping())

    if cooldown := author_mapping.remaining_cooldown:
        if isinstance(ctx, Context):
            raise commands.CommandOnCooldown(cooldown, cooldown.per, commands.BucketType.user)
        else:
            raise CommandOnCooldown(cooldown, cooldown.per)

    return True


def get_cooldown_keys(context: CooldownContext) -> Tuple[Optional[str], Optional[int]]:
    """
    Parses the command name and author id from command invocation context/interaction for use in `DynamicCooldown`.

    Note:
        The typing here is overly verbose due to arg-type issues with discord.py's `CachedSlotProperty`.

    Parameters:
        context (Union[Context, Interaction[DreamBot]]): The command invocation context/interaction.

    Returns:
        Tuple[Optional[str], Optional[int]].
    """

    if isinstance(context, Context) and context.command is not None:
        return context.command.qualified_name, context.author.id
    elif isinstance(context, Interaction) and context.command is not None and isinstance(context.command, Command):
        return context.command.qualified_name, context.user.id
    elif isinstance(context, Interaction) and context.command is not None and isinstance(context.command, ContextMenu):
        return context.command.name, context.user.id
    else:
        return None, None
