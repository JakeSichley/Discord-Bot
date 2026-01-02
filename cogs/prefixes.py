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

from aiosqlite import Error as aiosqliteError
from discord.ext import commands

from dreambot import DreamBot
from utils.context import Context
from utils.database.helpers import execute_query
from utils.observability.loggers import bot_logger


class Prefixes(commands.Cog):
    """
    A Cogs class that contains prefix commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Prefixes class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.group(name='prefix', aliases=['pre', 'prefixes'])
    async def prefix(self, ctx: Context) -> None:
        """
        Parent command that handles prefix related commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            # noinspection PyTypeChecker
            await ctx.invoke(self.get_prefix)

    @commands.cooldown(1, 2, commands.BucketType.guild)  # type: ignore[arg-type]
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @prefix.command(name='add', aliases=['set'])
    async def add_prefix(self, ctx: Context, prefix: str) -> None:
        """
        A method to add a command prefix for the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (2) seconds per (Guild).
            has_permissions(manage_guild): Whether the invoking user can manage the guild.
            guild_only(): Whether the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (Context): The invocation context.
            prefix (str): The new prefix to use.

        Returns:
            None.
        """

        assert ctx.guild is not None  # guild only

        prefixes = self.bot.cache.prefixes.get(ctx.guild.id, [])

        if len(prefixes) >= 3:
            await ctx.send('This guild has reached the maximum number of prefixes.')
            return

        if prefix in prefixes:
            await ctx.send('The desired prefix already exists for this guild.')
            return

        prefix = prefix.strip()

        if len(prefix) > 16:
            await ctx.send('The maximum length for a prefix is 16 characters.')
            return

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO PREFIXES (GUILD_ID, PREFIX) VALUES (?, ?)',
                (ctx.guild.id, prefix)
            )
        except aiosqliteError:
            await ctx.send(f'Failed to add `{prefix}`.')
        else:
            if ctx.guild.id in self.bot.cache.prefixes:
                self.bot.cache.prefixes[ctx.guild.id].append(prefix)
            else:
                self.bot.cache.prefixes[ctx.guild.id] = [prefix]

            await ctx.send(f'Added `{prefix}` as a prefix for this guild.')

    @commands.cooldown(1, 2, commands.BucketType.guild)  # type: ignore[arg-type]
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @prefix.command(name='remove', aliases=['delete', 'del'])
    async def remove_prefix(self, ctx: Context, prefix: str) -> None:
        """
        A method to remove a command prefix for the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (2) seconds per (Guild).
            has_permissions(manage_guild): Whether the invoking user can manage the guild.
            guild_only(): Whether the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (Context): The invocation context.
            prefix (str): The prefix to remove.

        Returns:
            None.
        """

        assert ctx.guild is not None  # guild only

        prefixes = self.bot.cache.prefixes.get(ctx.guild.id, None)
        prefix = prefix.strip()

        if prefixes is None:
            await ctx.send(f'This guild has no custom prefixes. Cannot remove `{prefix}`.')
            return

        if prefix not in prefixes:
            await ctx.send(f'`{prefix}` is not one of custom prefixes for this guild.')
            return

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM PREFIXES WHERE GUILD_ID=? AND PREFIX=?',
                (ctx.guild.id, prefix)
            )
        except aiosqliteError:
            await ctx.send(f'Failed to remove `{prefix}`.')
        else:
            self.bot.cache.prefixes[ctx.guild.id].remove(prefix)

            if not self.bot.cache.prefixes[ctx.guild.id]:
                del self.bot.cache.prefixes[ctx.guild.id]

            await ctx.send(f'Removed `{prefix}` as a prefix for this guild.')

    @commands.cooldown(1, 2, commands.BucketType.guild)  # type: ignore[arg-type]
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @prefix.command(name='replace', aliases=['swap', 'switch'])
    async def replace_prefix(self, ctx: Context, old_prefix: str, new_prefix: str) -> None:
        """
        A method to replace an existing command prefix for the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (2) seconds per (Guild).
            has_permissions(manage_guild): Whether the invoking user can manage the guild.
            guild_only(): Whether the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (Context): The invocation context.
            old_prefix (str): The prefix to remove.
            new_prefix (str): The prefix to add.

        Returns:
            None.
        """

        assert ctx.guild is not None  # guild only

        prefixes = self.bot.cache.prefixes.get(ctx.guild.id, None)
        old_prefix, new_prefix = old_prefix.strip(), new_prefix.strip()

        if prefixes is None:
            await ctx.send(f'This guild has no custom prefixes. Cannot replace `{old_prefix}`.')
            return

        if new_prefix == old_prefix:
            await ctx.send(f'The old and new prefix are identical.')
            return

        if old_prefix not in prefixes:
            await ctx.send(f'`{old_prefix} is not one of custom prefixes for this guild.`')
            return

        try:
            await execute_query(
                self.bot.database,
                'UPDATE PREFIXES SET PREFIX=? WHERE GUILD_ID=? AND PREFIX=?',
                (new_prefix, ctx.guild.id, old_prefix)
            )
        except aiosqliteError:
            await ctx.send(f'Failed to replace `{old_prefix}` with `{new_prefix}`.')
        else:
            self.bot.cache.prefixes[ctx.guild.id].remove(old_prefix)
            self.bot.cache.prefixes[ctx.guild.id].append(new_prefix)

            await ctx.send(f'Replaced `{old_prefix}` with `{new_prefix}` as a prefix for this guild.')

    @commands.cooldown(1, 2, commands.BucketType.guild)  # type: ignore[arg-type]
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @prefix.command(name='clear')
    async def clear_prefixes(self, ctx: Context) -> None:
        """
        A method to remove all existing command prefixes for the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (2) seconds per (Guild).
            has_permissions(manage_guild): Whether the invoking user can manage the guild.
            guild_only(): Whether the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert ctx.guild is not None  # guild only

        prefixes = self.bot.cache.prefixes.get(ctx.guild.id, None)

        if prefixes is None:
            await ctx.send(f'This guild has no custom prefixes. Cannot clear prefixes.')
            return

        confirmation = await ctx.confirmation_prompt('Are you sure you wish to clear all prefixes from this guild?')

        if not confirmation:
            await ctx.send('Aborting Clear Prefixes.')
            return

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM PREFIXES WHERE GUILD_ID=?',
                (ctx.guild.id,)
            )
        except aiosqliteError:
            await ctx.send(f'Failed to clear prefixes.')
        else:
            del self.bot.cache.prefixes[ctx.guild.id]

            await ctx.send(f'Cleared all prefixes for the guild.')

    @commands.cooldown(1, 2, commands.BucketType.guild)  # type: ignore[arg-type]
    @prefix.command(name='get')
    async def get_prefix(self, ctx: Context) -> None:
        """
        A method that outputs the current prefixes for the guild.

        Checks:
            guild_only(): Whether the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            Success: The prefix assigned to the guild.
            Failure: An error noting the prefix could not be fetched.

        Returns:
            None.
        """

        assert self.bot.user is not None  # always logged in

        if not ctx.guild:
            await ctx.send(f'Prefix: `{self.bot.default_prefix}`')
            return

        if ctx.guild.id not in self.bot.cache.prefixes:
            await ctx.send(
                f'You can use {self.bot.user.mention} or `{self.bot.default_prefix}` to invoke commands in this guild.'
            )
        else:
            prefixes = [f'`{x}`' for x in self.bot.cache.prefixes[ctx.guild.id]]
            await ctx.send(
                f'You can use {self.bot.user.mention} or {" or ".join(prefixes)} to invoke commands in this guild.'
            )


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Prefixes(bot))
    bot_logger.info('Completed Setup for Cog: Prefixes')
