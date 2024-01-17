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

from datetime import datetime, timedelta
from typing import Optional

from discord.ext import commands

from utils.context import Context


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

        return min(2 ** (5 + self.__count), self.__max_cooldown)

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


async def cooldown_predicate(ctx: Context) -> bool:
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

    if ctx.command is None:
        return True

    command_cooldown_mapping = ctx.bot.dynamic_cooldowns.get(ctx.command.qualified_name)

    if command_cooldown_mapping is None:
        return True

    author_mapping = command_cooldown_mapping.get(ctx.author.id, CooldownMapping())

    if cooldown := author_mapping.remaining_cooldown:
        raise commands.CommandOnCooldown(cooldown, cooldown.per, commands.BucketType.user)

    return True
