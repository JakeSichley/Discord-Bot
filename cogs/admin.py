from discord.ext import commands
from asyncio import TimeoutError
from io import StringIO
from contextlib import redirect_stdout
from textwrap import indent
from traceback import format_exc
import aiosqlite
from typing import List


class Admin(commands.Cog):
    """
    A Cogs class that contains Owner only commands.

    Attributes:
        bot (commands.Bot): The Discord bot.
        _last_result (str): The value (if any) of the last exec command.
    """

    def __init__(self, bot):
        """
        The constructor for the Admin class.

        Parameters:
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        """
        A method that registers a cog-wide check.
        Requires the invoking user to be the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            (boolean): Whether or not the invoking user is the bot's owner.
        """

        return await self.bot.is_owner(ctx.author)

    @commands.command(name='admin help', aliases=['ahelp'], hidden=True)
    async def admin_help_command(self, ctx):
        """
        A command to generate help information for the Admin cog.
        The native help command will not generate information for the Admin cog, since all commands are hidden.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Help information for admin-only commands.

        Returns:
            None.
        """

        list_of_commands = self.get_commands()
        longest_command_name = sorted((len(x.name) for x in list_of_commands), reverse=True)[0]
        help_string = f'```Admin Cog.\n\nCommands:'

        for command in list_of_commands:
            help_string += f'\n  {command.name} {" " * (longest_command_name - len(command.name))} {command.short_doc}'

        help_string += '\n\nType ?help command for more info on a command.\n' \
                       'You can also type ?help category for more info on a category.```'

        await ctx.send(help_string)

    @commands.command(name='reload', aliases=['load'], hidden=True)
    async def reload(self, ctx, module):
        """
        A command to reload a module.
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

    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx, module):
        """
        A command to unload a module.

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

    @commands.command(name='mreload', hidden=True)
    async def mreload(self, ctx, module):
        """
        A command to 'manually' reload a module. Explicitly unloads then reloads a module.
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

    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx):
        """
        A command to stop (close/logout) the bot.
        The command must be confirmed to complete the logout.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            First: A confirmation message.
            Second: The status of the logout method.

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

    @commands.command(name='eval', hidden=True)
    async def _eval(self, ctx, _ev: str):
        """
        A command to evaluate a python statement.
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

    @commands.command(name='sql', hidden=True)
    async def sql(self, ctx, *, query: str):
        """
        A command to execute a sqlite3 statement.
        If the statement type is 'SELECT', successful executions will send the result.
        For other statement types, successful executions will send 'Executed'.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            query (str): The statement to be executed.

        Output:
            Success ('SELECT'): The result of the selection statement.
            Success (Not 'SELECT'): 'Executed'.
            Failure (Any): The error that arose during execution.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                if (query.upper()).startswith('SELECT'):
                    async with db.execute(query) as cursor:
                        await ctx.send(await cursor.fetchall())
                else:
                    affected = await db.execute(query)
                    await db.commit()
                    await ctx.send(f'Executed. {affected.rowcount} rows affected.')

        except aiosqlite.Error as e:
            await ctx.send(f'Error: {e}')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.command(name='reloadprefixes', aliases=['rp'], hidden=True)
    async def reload_prefixes(self, ctx):
        """
        A command to reload the bot's store prefixes.
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

    @commands.command(name='resetcooldown', aliases=['rc'], hidden=True)
    async def reset_cooldown(self, ctx, command):
        """
        A command to reset the cooldown of a command.

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

    @commands.command(name='exec', aliases=['execute'], pass_context=True, hidden=True)
    async def _exec(self, ctx, *, body: str):
        """
        A command to execute a Python code block and output the result, if any.

        Checks:
            is_owner(): Whether or not the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
            body (str): The block of code to be executed.

        Output:
            The result of the execution, if any.

        Returns:
            None.
        """

        # additional context to pass to exec; will be combined with globals()
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        # strip discord code block formatting from body
        if body.startswith('```') and body.endswith('```'):
            body = '\n'.join(body.split('\n')[1:-1])
        else:
            body = body.strip('` \n')

        # redirect output of the execution
        stdout = StringIO()
        # wrap code block in async declaration
        to_compile = f'async def func():\n{indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            return

        func = env['func']

        # noinspection PyBroadException
        try:
            with redirect_stdout(stdout):
                ret = await func()

        except Exception:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{format_exc()}\n```')
        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')


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
