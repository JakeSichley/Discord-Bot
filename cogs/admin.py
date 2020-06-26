from discord.ext import commands
import aiosqlite
from asyncio import TimeoutError


class Admin(commands.Cog):
    """
    A Cogs class that contains Owner only commands.

    Attributes:
        bot (commands.Bot): The Discord bot.
    """

    def __init__(self, bot):
        """
        The constructor for the Admin class.

        Parameters:
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot

    @commands.is_owner()
    @commands.command(name='reload', aliases=['load'], hidden=True)
    async def reload(self, ctx, module):
        """
        A method to reload a module.
        If the reload fails, the previous state of module is maintained.
        If the module is not loaded, attempt to load the module.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            module (str): The module to be reloaded.

        Output:
            The status of the reload.

        Returns:
            None.
        """

        try:
            self.bot.reload_extension('cogs.' + module)
            await ctx.send(f'Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            self.bot.load_extension('cogs.' + module)
            await ctx.send(f'Loaded Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx, module):
        """
        A method to unload a module.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            module (str): The module to be unloaded.

        Output:
            The status of the unload.

        Returns:
            None.
        """

        try:
            self.bot.unload_extension('cogs.' + module)
            await ctx.send(f'Unloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Unload Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='mreload', hidden=True)
    async def mreload(self, ctx, module):
        """
        A method to 'manually' reload a module. Explicity unloads then reloads a module.
        If the reload fails, the previous state of module is maintained.
        If the module is not loaded, attempt to load the module.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            module (str): The module to be reloaded.

        Output:
            The status of the 'manual' reload.

        Returns:
            None.
        """

        try:
            self.bot.unload_extension('cogs.' + module)
            self.bot.load_extension('cogs.' + module)
            await ctx.send(f'Manually Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Manually Reloaded Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx):
        """
        A method to stop (close/logout) the bot.
        The command must be confirmed to complete the logout.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            First: A confirmation message.
            Second. The status of the logout method.

        Returns:
            None.
        """

        await ctx.send('Confirm Logout?')

        def check(message):
            return message.content.lower() == 'confirm' and message.author.id == self.bot.owner_id

        try:
            await self.bot.wait_for('message', timeout=10.0, check=check)
        except TimeoutError:
            await ctx.send('Logout Aborted.')
        else:
            await ctx.send('Logout Confirmed.')
            await self.bot.logout()

    @commands.is_owner()
    @commands.command(name='eval', hidden=True)
    async def eval(self, ctx, _ev: str):
        """
        A method to evaluate a python statement.
        Should the evaluation encounter an exception, the output will be the exception details.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            _ev (str): The statement to be evaluated.

        Output:
            Success: The result of the eval function.
            Failure: The details of the exception that arose.

        Returns:
            None.
        """

        try:
            output = eval(_ev)
        except Exception as e:
            output = e

        await ctx.send(output)

    @commands.is_owner()
    @commands.command(name='execute', hidden=True)
    async def execute(self, ctx, *, _ev: str):
        """
        A method to execute a sqlite3 statement.
        If the statement type is 'SELECT', successful executions will send the result.
        For other statement types, successful executions will send 'Executed'.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            _ev (str): The statement to be executed..

        Output:
            Success ('SELECT'): The result of the selection statement.
            Success (Not 'SELECT'): 'Executed'.
            Failure (Any): The error that arose during execution.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                if 'SELECT' in _ev:
                    async with db.execute(_ev) as cursor:
                        await ctx.send(await cursor.fetchall())
                else:
                    await db.execute(_ev)
                    await db.commit()
                    await ctx.send('Executed.')

        except aiosqlite.Error as e:
            await ctx.send(f'Error: {e}')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.is_owner()
    @commands.command(name='reloadprefixes', hidden=True)
    async def reload_prefixes(self, ctx):
        """
        A method to reload the bot's store prefixes.
        Prefixes are normally reloaded when explicitly changed.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Success: 'Reloaded Prefixes'.
            Failure: The error that arose during execution.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                async with db.execute("SELECT * FROM Prefixes") as cursor:
                    rows = await cursor.fetchall()
                    if not rows:
                        self.bot.prefixes.clear()
                    else:
                        async for guild, prefix in cursor:
                            self.bot.prefixes[int(guild)] = prefix
                    await ctx.send('Reloaded Prefixes.')

        except aiosqlite.Error as e:
            await ctx.send(f'Error: {e}')
            print(f'Reload Prefixes Error: {e}')

    @commands.is_owner()
    @commands.command(name='resetcooldown', hidden=True)
    async def reset_cooldown(self, ctx, command):
        """
        A method to reset the cooldown of a command.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            command (str): The command for which the cooldown will be reset.

        Output:
            'Reset cooldown of Command: (command)'.

        Returns:
            None.
        """
        self.bot.get_command(command).reset_cooldown(ctx)
        await ctx.send(f'Reset cooldown of Command: `{command}`')


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Admin(bot))
    print('Completed Setup for Cog: Admin')
