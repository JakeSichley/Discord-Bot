"""
MIT License

Copyright (c) 2019-2023 Jake Sichley

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
from sys import stderr
from traceback import print_exception, format_exception

from aiohttp import ClientResponseError
from discord import HTTPException, Interaction
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from dreambot import DreamBot
from utils.context import Context
from utils.enums.guild_feature import GuildFeature
from utils.logging_formatter import bot_logger


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
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        bot.tree.on_error = self.on_app_command_error  # type: ignore[assignment]

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError) -> None:
        """
        A listener method that is called whenever a command encounters an error.
        Most user-facing exceptions output a message detailing why the command invocation failed.
        Other exceptions are either handled silently or logged.

        Parameters:
            ctx (Context): The invocation context.
            error (Exception): The encountered error.

        Output:
            (Not Guaranteed): The status of the error, should the user require context.

        Returns:
            None.
        """

        if ctx.command is None and ctx.guild is not None and isinstance(error, commands.CommandNotFound):
            await self.try_direct_tag_invoke(ctx)

        if ctx.command is None or hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandInvokeError):
            error = error.__cause__  # type: ignore[assignment]

        not_logged = (
            commands.CommandNotFound, commands.UserInputError, commands.CheckFailure, ClientResponseError,
            commands.CommandOnCooldown, commands.DisabledCommand
        )

        if not isinstance(error, not_logged):
            bot_logger.warning(f'Ignoring exception in command {ctx.command}:')
            print_exception(type(error), error, error.__traceback__, file=stderr)

            await self.bot.report_exception(error)

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
                retry_after = int(error.retry_after)
                cooldown_expiration = datetime.now() + timedelta(seconds=error.retry_after)

                await ctx.send(
                    f'{ctx.author.mention}, you can use this command {format_dt(cooldown_expiration, "R")}.'
                )

                if retry_after > 21600:  # 6 hours
                    bot_logger.warning(
                        f'{str(ctx.author)} ({ctx.author.id}) triggered a cooldown in command '
                        f'`{ctx.command.qualified_name}` longer than 6 hours ({retry_after}).'
                    )
            return

        # External network error
        elif isinstance(error, ClientResponseError):
            await ctx.send(
                f'`{ctx.command}` encountered a network error: '
                f'`{error.message} ({error.status})`'  # type: ignore[attr-defined]
            )
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
            formatted_error = ''.join(
                format_exception(type(error), error, error.__traceback__)  # type: ignore[attr-defined]
            )
            await ctx.send(f'```py\n{formatted_error}```')

    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """
        A listener method that is called whenever an app command encounters an error.

        Parameters:
            interaction (Interaction): The invocation interaction.
            error (AppCommandError): The app command error.

        Returns:
            None.
        """

        assert interaction.command is not None

        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(f'{error}', ephemeral=True)
            return

        bot_logger.warning(
            f'Encountered AppCommandError in command {interaction.command.qualified_name}. '
            f'User: `{interaction.user}` Guild: `{interaction.guild.id if interaction.guild is not None else "None"}`\n'
        )
        print_exception(type(error), error, error.__traceback__, file=stderr)

        await self.bot.report_exception(error)

    async def try_direct_tag_invoke(self, ctx: Context) -> None:
        """
        When a `CommandNotFound` exception is raised, this method will attempt to directly invoke a corresponding tag,
        if applicable.
        The Guild Feature `TAG_DIRECT_INVOKE` must be enabled.
        During direct tag invocation, the normal suggestions or tag-not-found responses will be suppressed.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert ctx.guild is not None

        tag_cog = self.bot.get_cog('Tags')
        direct_invoke_enabled = self.bot.cache.guild_feature_enabled(ctx.guild.id, GuildFeature.TAG_DIRECT_INVOKE)

        if (
            tag_cog is None or
            not direct_invoke_enabled or
            not hasattr(tag_cog, 'get_tag')
        ):
            return

        potential_tag = ctx.message.content.removeprefix(ctx.prefix or self.bot.default_prefix)

        await ctx.invoke(tag_cog.get_tag, tag_name=potential_tag)  # type: ignore[arg-type]


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Exceptions(bot))
    bot_logger.info('Completed Setup for Cog: Exceptions')
