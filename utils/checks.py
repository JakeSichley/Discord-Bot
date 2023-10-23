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

from typing import Callable, Union, List

from discord.ext import commands

from utils.context import Context
from utils.cooldowns import cooldown_predicate


def dynamic_cooldown() -> Callable:
    """
    Dynamic Cooldown Check.

    Parameters:
        None.

    Returns:
        (Callable[[], Context]): The resulting wrapped predicate.
    """

    return commands.check(cooldown_predicate)


def check_memecoin_channel() -> Callable:
    """
    Memecoin Channel Check.

    Parameters:
        None.

    Returns:
        (Callable[[], Context]): The resulting wrapped predicate.
    """

    def predicate(ctx: Context) -> bool:
        """
        A commands.check decorator that ensures MemeCoin commands are only executed in the proper channel.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the invocation channel is the authorized MemeCoin channel.
        """

        return ctx.message.channel.id == 636356259255287808

    return commands.check(predicate)


def ensure_git_credentials() -> Callable:
    """
    Admin.Git Group Check.

    Parameters:
        None.

    Returns:
        (Callable[[], Context]): The resulting wrapped predicate.
    """

    def predicate(ctx: Context) -> bool:
        """
        A commands.check decorator that git commands are able to properly execute.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the bot was initialized with git credentials.
        """

        return ctx.bot.git is not None

    return commands.check(predicate)


def guild_only(guild_id: Union[int, List[int]]) -> Callable:
    """
    Only allows command execution for the specified guild.

    Parameters:
        guild_id (guild_id: Union[int, List[int]]): The id of the guild authorized to execute this command.

    Returns:
        (Callable[[], Context]): The resulting wrapped predicate.
    """

    guild_ids = guild_id if isinstance(guild_id, list) else [guild_id]

    def predicate(ctx: Context) -> bool:
        """
        A commands.check decorator that git commands are able to properly execute.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the bot was initialized with git credentials.
        """

        return ctx.guild is not None and ctx.guild.id in guild_ids

    return commands.check(predicate)
