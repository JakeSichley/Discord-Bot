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
from typing import Callable
from utils.context import Context


def check_memecoin_channel() -> Callable:
    """
    Memecoin Channel Check.
    """

    def predicate(ctx: Context) -> bool:
        """
        A commands.check decorator that ensures MemeCoin commands are only executed in the proper channel.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (boolean): Whether the invocation channel is the authorized MemeCoin channel.
        """

        return ctx.message.channel.id == 636356259255287808
    return commands.check(predicate)


def ensure_git_credentials() -> Callable:
    """
    Admin.Git Group Check.
    """

    def predicate(ctx: Context) -> bool:
        """
        A commands.check decorator that git commands are able to properly execute.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (boolean): Whether the bot was initialized with git credentials.
        """

        return ctx.bot.git
    return commands.check(predicate)
