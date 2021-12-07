from discord.ext import commands
from typing import Callable


def check_memecoin_channel() -> Callable:
    """
    Memecoin Channel Check.
    """

    def predicate(ctx: commands.Context) -> bool:
        """
        A commands.check decorator that ensures MemeCoin commands are only executed in the proper channel.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            (boolean): Whether or not the invocation channel is the authorized MemeCoin channel.
        """

        return ctx.message.channel.id == 636356259255287808
    return commands.check(predicate)


def ensure_git_credentials() -> Callable:
    """
    Admin['git'] Group Check.
    """

    def predicate(ctx: commands.Context) -> bool:
        """
        A commands.check decorator that git commands are able to properly execute.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            (boolean): Whether or not the bot was initialized with git credentials.
        """

        return ctx.bot.git
    return commands.check(predicate)
