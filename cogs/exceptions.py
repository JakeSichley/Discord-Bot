from discord.ext import commands
from discord import HTTPException
from sys import stderr
from traceback import print_exception, format_exception
from dreambot import DreamBot
from aiohttp import ClientResponseError


class Exceptions(commands.Cog):
    """
    A Cogs class that provides centralized exception handling for the bot.

    Attributes:
        bot (DreamBot): The Discord bot.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Exceptions class.

        Parameters:
            bot (DreamBott): The Discord bot.
        """

        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        A listener method that is called whenever a command encounters an error.
        Most user-facing exceptions output a message detailing why the command invocation failed.
        Other exceptions are either handled silently or logged.

        Parameters:
            ctx (commands.Context): The invocation context.
            error (Exception): The encountered error.

        Output:
            (Not Guaranteed): The status of the error, should the user require context.

        Returns:
            None.
        """

        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandInvokeError):
            error = error.__cause__

        ignored = (commands.CommandNotFound, commands.UserInputError, commands.CheckFailure, ClientResponseError)

        if not isinstance(error, ignored):
            print('Ignoring exception in command {}:'.format(ctx.command), file=stderr)
            print_exception(type(error), error, error.__traceback__, file=stderr)

        permissions = (commands.NotOwner, commands.MissingPermissions)
        # Allows us to check for original exceptions raised and sent to CommandInvokeError
        # If nothing is found, keep the exception passed in
        error = getattr(error, 'original', error)

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'`{ctx.command}` has been disabled.')
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
                return
            except HTTPException as e:
                print(f'Commands Error Handler Error: (NoPrivateMessage) {e}')

        # Using the permissions tuple allows us to handle multiple errors of similar types
        # Errors where the user does not have the authority to execute the command
        elif isinstance(error, permissions):
            await ctx.send(f'{ctx.message.author.mention}, you do not have permission to use this command!')
            return

        # Calling a command currently on cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == self.bot.owner_id:
                await ctx.reinvoke()
            else:
                await ctx.send(f'{ctx.message.author.mention}, please wait {int(error.retry_after)} seconds '
                               f'before calling this command again!')
            return

        # External network error
        elif isinstance(error, ClientResponseError):
            await ctx.send(f'`{ctx.command}` encountered a network error: `{error.message} ({error.status})`')
            return

        # Check failure
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f'One or more checks failed during the invocation of command: '
                           f'`{ctx.command.qualified_name}`.')
            return

        # Calling a command without the required role
        elif isinstance(error, commands.MissingRole):
            if ctx.author.id == self.bot.owner_id:
                await ctx.reinvoke()
            else:
                await ctx.send(f'{ctx.message.author.mention}, you do not have the required role to use this command!')
            return

        # Calling a command currently at max concurrency
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(f'{ctx.message.author.mention}, the maximum concurrency for this command has been reached. '
                           f'It can be used a maximum of {error.number} time(s) per {error.per.name} concurrently.')
            return

        # Bot cannot execute command due to insufficient permissions
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f'{ctx.message.author.mention}, I lack the {error}\n{error.__dict__}'
                           f' permissions for this command')
            return

        # Reloading an extension that currently has errors
        elif isinstance(error, commands.ExtensionError):
            await ctx.send(f'```py\n{"".join(format_exception(type(error), error, error.__traceback__))}```')


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Exceptions(bot))
    print('Completed Setup for Cog: Exceptions')
