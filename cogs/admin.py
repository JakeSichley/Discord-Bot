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

import re
import sys
from asyncio import sleep
from contextlib import redirect_stdout
from contextlib import suppress
from copy import copy
from datetime import datetime, timedelta
from importlib import reload
from io import StringIO
from re import finditer
from textwrap import indent
from traceback import format_exc, format_exception
from typing import Union, List, Sequence, Annotated, Literal, Any

import discord
import pytz
from aiosqlite import Error as aiosqliteError
from discord.abc import Messageable
from discord.ext import commands
from discord.ext import tasks
from discord.utils import format_dt

from dreambot import DreamBot
from utils.checks import ensure_git_credentials
from utils.context import Context
from utils.converters import StringConverter
from utils.database.helpers import execute_query, retrieve_query
from utils.network.exceptions import EmptyResponseError
from utils.network.utils import Headers
from utils.observability.loggers import bot_logger
from utils.utils import pairs, run_in_subprocess, generate_activity, VERSION

ExtensionName = StringConverter(
    mutator=lambda x: x.strip().lower(),
    allow_forbidden_characters=True
)


class Admin(commands.Cog):
    """
    A Cogs class that contains Owner only commands.

    Attributes:
        bot (DreamBot): The Discord bot.
        _last_result (str): The value (if any) of the last exec command.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Admin class.

        Parameters:
            bot (commands.Bot): The Discord bot.

        Returns:
            None.
        """

        self.bot = bot
        self._last_result = None
        self.logging_line_break.start()

    async def cog_check(self, ctx: Context) -> bool:  # type: ignore[override]
        """
        A method that registers a cog-wide check.
        Requires the invoking user to be the bot's owner.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (boolean): Whether the invoking user is the bot's owner.
        """

        return await self.bot.is_owner(ctx.author)

    @commands.command(name='admin_help', aliases=['ahelp', 'adminhelp'], hidden=True)
    async def admin_help_command(self, ctx: Context) -> None:
        """
        A command to generate help information for the Admin cog.
        The native help command will not generate information for the Admin cog, since all commands are hidden.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            Help information for admin-only commands.

        Returns:
            None.
        """

        list_of_commands = list(self.walk_commands())
        longest_command_name = sorted((len(x.qualified_name) for x in list_of_commands), reverse=True)[0]
        help_string = f'```Admin Cog.\n\nCommands:'

        for command in list_of_commands:
            help_string += f'\n  {command.qualified_name:{longest_command_name + 1}} {command.short_doc}'

        help_string += '\n\nType ?help command for more info on a command.\n' \
                       'You can also type ?help category for more info on a category.```'

        await ctx.send(help_string)

    @commands.command(name='reload', aliases=['load'], hidden=True)
    async def reload(self, ctx: Context, module: Annotated[str, ExtensionName]) -> None:
        """
        A command to reload a module.
        If the reload fails, the previous state of module is maintained.
        If the module is not loaded, attempt to load the module.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            module (str): The module to be reloaded.

        Output:
            The status of the reload.

        Returns:
            None.
        """

        try:
            await self.bot.reload_extension('cogs.' + module)
            await ctx.send(f'Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension('cogs.' + module)
            await ctx.send(f'Loaded Module: `{module}`')
        except commands.ExtensionNotFound:
            await ctx.send(f'Module `{module} does not exist.')

    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx: Context, module: Annotated[str, ExtensionName]) -> None:
        """
        A command to unload a module.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            module (str): The module to be unloaded.

        Output:
            The status of the unload.

        Returns:
            None.
        """

        if module == 'admin':
            ctx.command = self.bot.get_command('reload')
            await ctx.reinvoke()
            return

        try:
            await self.bot.unload_extension('cogs.' + module)
            await ctx.send(f'Unloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Unload Module: `{module}`')

    @commands.command(name='sync')
    async def sync_commands(self, ctx: Context, sync_type: Literal['global', 'local', 'guild', 'clear']) -> None:
        """
        Syncs application commands based on the specified sync type.
        Defaults to syncing to the local guild.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            sync_type (str): The type of sync to perform.

        Returns:
            None.
        """

        if ctx.guild is None:
            await ctx.send('`ctx.guild` was None.')
            return

        if sync_type == 'global':
            # tree to global
            synced: List[Any] = await ctx.bot.tree.sync()
        elif sync_type == 'guild':
            # sync guild to guild (guild-specific commands)
            synced = await self.bot.tree.sync(guild=ctx.guild)
        elif sync_type == 'clear':
            # clear guild
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = ctx.bot.tree.get_commands()
        elif sync_type == 'local':
            # tree to local
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        else:
            await ctx.send('No sync type was provided.')
            return

        await ctx.send(f'Synced {len(synced)} commands using sync type: `{sync_type}`.')
        bot_logger.info(f'Synced {len(synced)} commands using sync type: {sync_type}.')

    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx: Context) -> None:
        """
        A command to stop (close/logout) the bot.
        The command must be confirmed to complete the logout.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.

        Output:
           A confirmation message.

        Returns:
            None.
        """

        await ctx.send('Closing Event Loop.')
        bot_logger.info('Closing event loop')
        await self.bot.close()

    @commands.command(name='eval', hidden=True)
    async def _eval(self, ctx: Context, *, _ev: str) -> None:
        """
        A command to evaluate a python statement.
        Should the evaluation encounter an exception, the output will be the exception details.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            _ev (str): The statement to be evaluated.

        Output:
            Success: The result of the eval function.
            Failure: The details of the exception that arose.

        Returns:
            None.
        """

        try:
            output = str(eval(_ev))
        except Exception as e:
            output = str(e)

        await ctx.safe_send(output)

    @commands.command(name='sql', hidden=True)
    async def sql(self, ctx: Context, *, query: str) -> None:
        """
        A command to execute a sqlite3 statement.
        If the statement type is 'SELECT', successful executions will send the result.
        For other statement types, successful executions will send 'Executed'.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            query (str): The statement to be executed.

        Output:
            Success ('SELECT'): The result of the selection statement.
            Success (Not 'SELECT'): 'Executed'.
            Failure (Any): The error that arose during execution.

        Returns:
            None.
        """

        if (query.upper()).startswith('SELECT'):
            try:
                result = await retrieve_query(self.bot.database, query)
                await ctx.safe_send(str(result))
            except aiosqliteError as e:
                await ctx.send(f'Error: {e}')
            finally:
                return

        if self.bot.environment == 'PROD':
            if not await ctx.confirmation_prompt('Confirm potentially mutating statement?'):
                await ctx.send('Discarding.')
                return

        try:
            affected = await execute_query(self.bot.database, query)
            await ctx.send(f'Executed. {affected} rows affected.')
        except aiosqliteError as e:
            formatted_exception = '\n'.join(format_exception(type(e), e, e.__traceback__))
            await ctx.safe_send(f'```\n{formatted_exception}\n```')

    @commands.command(name='refresh', hidden=True)
    async def reload_prefixes(self, ctx: Context) -> None:
        """
        A command to refresh the bot's table caches.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.


        Returns:
            None.
        """

        await self.bot.cache.sync()
        await ctx.send('Refreshed Table Caches.')

    @commands.command(name='resetcooldown', aliases=['rc'], hidden=True)
    async def reset_cooldown(self, ctx: Context, command_name: str) -> None:
        """
        A command to reset the cooldown of a command.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
            command_name (str): The command for which the cooldown will be reset.

        Output:
            'Reset cooldown of Command: (command)'.

        Returns:
            None.
        """

        if command := self.bot.get_command(command_name):
            command.reset_cooldown(ctx)
            await ctx.send(f'Reset cooldown of Command: `{command_name}`')
        else:
            await ctx.send(f'Failed to get Command: `{command_name}`')

    @commands.command(name='exec', aliases=['execute'], hidden=True)
    async def _exec(self, ctx: Context, *, body: str) -> None:
        """
        A command to execute a Python code block and output the result, if any.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (Context): The invocation context.
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
            await ctx.safe_send(f'```py\n{e.__class__.__name__}: {e}\n```')
            return

        func = env['func']

        # noinspection PyBroadException
        try:
            with redirect_stdout(stdout):
                ret = await func()  # type: ignore[operator]

        except Exception:
            value = stdout.getvalue()
            await ctx.safe_send(f'```py\n{value}{format_exc()}\n```')
        else:
            value = stdout.getvalue()

            if ret is None:
                if 'return' in body.lower():
                    value = value if value else "None"
                    await ctx.safe_send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.safe_send(f'```py\n{value}{ret}\n```')

    @ensure_git_credentials()
    @commands.group(name='git', hidden=True)
    async def git(self, ctx: Context) -> None:
        """
        Parent command that handles git related commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('git')

    @git.command(name='pull', aliases=['p'], hidden=True)  # type: ignore[misc]
    async def git_pull(self, ctx: Context) -> None:
        """
        Pulls the latest changes from master.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert self.bot.git is not None  # `@ensure_git_credentials` handles this

        result = await run_in_subprocess('git fetch && git diff --stat HEAD origin/master')
        actual_result = [x for x in result if x]

        if not actual_result:
            await ctx.send('The bot is already up-to-date.')
            return

        output = '\n'.join(x.decode() for x in actual_result)
        await ctx.safe_send(f'**Pulling would modify the following the following files:**\n```\n{output}```')

        confirmation = await ctx.confirmation_prompt('Do you wish to continue?')

        if not confirmation:
            await ctx.send('Aborting Pull.')
            return

        git_message = await ctx.send('Performing `git pull` now.')
        git_result = await run_in_subprocess('git pull -f origin master')
        git_actual = [x.decode() for x in git_result if x]
        if 'Already up to date'.lower() in git_actual[0].lower():
            await git_message.edit(content='`git pull` determined the repository to be up-to-date.')
            return

        await git_message.delete()

        changes = output.replace('\n ', '\n').strip(' ')

        cogs = re.findall(r'(?<=cogs/)([A-z]+)(?=\.py)', changes, re.MULTILINE)
        utils = re.findall(r'(?<=utils/)([A-z]+)(?=\.py)', changes, re.MULTILINE)
        core = [match.group() for match in re.finditer(r'^(?:(?!/).)*[A-z]+(?=\.py)', changes, re.MULTILINE)]
        library = []

        if 'requirements.txt' in changes:
            pip_message = await ctx.send('Performing `pip install` now.')
            core.append('requirements')
            lib_output = await run_in_subprocess('pip install -r requirements.txt')
            lib_actual = '\n'.join(x.decode() for x in lib_output if x)
            packages = re.findall(r'successfully installed (.+)', lib_actual, re.IGNORECASE | re.MULTILINE)
            library = packages[0].split(' ') if packages else []
            await pip_message.delete()

        fields = {
            'Cogs': cogs,
            'Utils': utils,
            'Core': core,
            'Library': library
        }

        embed = discord.Embed(title='Git Pull Changes', color=0x00bbff)
        embed.url = f"https://github.com/{self.bot.git['git_user']}/{self.bot.git['git_repo']}"

        with suppress(AttributeError):
            embed.set_thumbnail(url=self.bot.user.avatar.url)  # type: ignore[union-attr]

        for field, value in fields.items():
            if value:
                embed.add_field(name=field, value='\n'.join(value))
        embed.set_footer(text='Please report any issues to my owner!')

        if core or 'context.py' in changes or 'table_dataclasses.py' in changes or '.sql' in changes:
            bot_logger.warning(f'Git Pull modified core files. Files not reloaded - current version is v{VERSION}.')
            embed.description = 'Core files were modified. No reloads will be performed.' \
                                '\nPlease perform a full restart to apply changes.'
            await ctx.send(embed=embed)
            return
        else:
            embed.description = 'Attempting to perform the following updates now.'
            await ctx.send(embed=embed)

        util_statuses, cog_statuses = [], []

        # -- utils --
        ordered_reloads: List[str] = []

        for file in utils:
            if file in ['utils', 'network_utils']:
                ordered_reloads.insert(0, f'utils.{file}')
            else:
                ordered_reloads.append(f'utils.{file}')

        for file in ordered_reloads:
            try:
                module = sys.modules[file]
            except KeyError:
                util_statuses.append(f'{file} - Imported')
            else:
                # noinspection PyBroadException
                try:
                    reload(module)
                except Exception as e:
                    util_statuses.append(f'{file} - Error: {e}')
                else:
                    util_statuses.append(f'{file} - Reloaded')

        # -- cogs --
        for cog in cogs:
            try:
                try:
                    await self.bot.reload_extension(f'cogs.{cog}')
                except commands.ExtensionNotLoaded:
                    try:
                        await self.bot.load_extension(f'cogs.{cog}')
                    except commands.ExtensionFailed:
                        raise
                    else:
                        cog_statuses.append(f'{cog} - Loaded')
                else:
                    cog_statuses.append(f'{cog} - Reloaded')
            except commands.ExtensionFailed:
                cog_statuses.append(f'{cog} - Failed')

        # -- summary --
        output = '**Update Summary**\n```'

        if util_statuses:
            output += '----- Utils -----\n'
            output += '\n'.join(util_statuses)

        if cog_statuses:
            output += '\n\n----- Cogs -----\n' if util_statuses else '----- Cogs -----\n'
            output += '\n'.join(cog_statuses)

        output += '\n```'

        # -- finalize --
        bot_logger.critical(f'Git Pull completed - bot is now running v{VERSION}.')
        if self.bot._status_text is not None and self.bot._status_type is not None:
            await self.bot.change_presence(
                activity=await generate_activity(self.bot._status_text, self.bot._status_type)
            )
        await ctx.safe_send(output)

    @git.command(name='dry_run', aliases=['dry', 'd'], hidden=True)  # type: ignore[misc]
    async def dry_run(self, ctx: Context) -> None:
        """
        Performs a dry run of git pull. Equivalent to git fetch && git diff --stat HEAD origin/master.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        result = await run_in_subprocess('git fetch && git diff --stat HEAD origin/master')
        actual_result = [x for x in result if x]

        if not actual_result:
            await ctx.send('The bot is already up-to-date.')
            return

        output = '\n'.join(x.decode() for x in actual_result)
        await ctx.send(f'**The following files would be updated:**\n```\n{output}```')

    @git.command(name='branches', aliases=['branch', 'b'], hidden=True)  # type: ignore[misc]
    async def git_branches(self, ctx: Context) -> None:
        """
        Fetches a list of branches from the bot's repository.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert self.bot.git is not None  # `@ensure_git_credentials` handles this

        headers: Headers = {
            'User-Agent': f"{self.bot.git['git_user']}-{self.bot.git['git_repo']}",
            'Authorization': f"Bearer {self.bot.git['git_token']}"
        }

        branches_url = f"https://api.github.com/repos/{self.bot.git['git_user']}/{self.bot.git['git_repo']}/branches"
        users_url = f"https://api.github.com/users/{self.bot.git['git_user']}"
        commits_url = f"https://api.github.com/repos/{self.bot.git['git_user']}/{self.bot.git['git_repo']}/commits/"

        try:
            branch_data = await self.bot.network_client.fetch_json(
                branches_url, headers=headers, raise_for_empty_response=True
            )
            user_data = await self.bot.network_client.fetch_json(
                users_url, headers=headers, raise_for_empty_response=True
            )
            latest_commit_data = {
                branch['name']:
                    await self.bot.network_client.fetch_json(
                        commits_url + branch['commit']['sha'], headers=headers,
                        raise_for_empty_response=True
                    ) for branch in branch_data[-5:]
            }
        except EmptyResponseError:
            await ctx.send('Failed to fetch branch information.')
            return

        try:
            thumbnail = user_data['avatar_url']
        except (KeyError, TypeError):
            thumbnail = 'https://pbs.twimg.com/profile_images/1414990564408262661/r6YemvF9_400x400.jpg'

        embed = discord.Embed(
            title=f"Overview of **{self.bot.git['git_repo']}**",
            colour=0x58a6ff,
            url=f"https://github.com/{self.bot.git['git_user']}/{self.bot.git['git_repo']}"
        )
        embed.set_thumbnail(url=thumbnail)
        for branch, commit in latest_commit_data.items():
            date = datetime.strptime(commit['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
            embed.add_field(
                name=branch,
                value=f"{commit['commit']['author']['name']} - {format_dt(date, 'R')}",
                inline=False
            )
        embed.set_footer(text="Please report any issues to my owner!")

        await ctx.send(embed=embed)

    @tasks.loop(hours=24)
    async def logging_line_break(self) -> None:
        """
        Inserts a logging line break at the start of each day.

        While `tasks.loop` does support a specific time parameter (ie: time=time(tzinfo=timezone('US/Pacific')), this is
        vulnerable to clock drifting. This is not a time-sensitive task and the library prints an absurd amount of
        'Clock drift detected' warnings. Consequently, we manually sleep until the next day and then repeat every 24
        hours, per the hours parameter.

        Parameters:
            None.

        Returns:
            None.
        """

        bot_logger.info(f'----- Line Break Inserted for Readability -----')

    @logging_line_break.before_loop
    async def before_logging_line_break(self) -> None:
        """
        A pre-task method to ensure the bot is ready before executing.
        Additionally sleeps until the start of the next day before inserting the first line break.

        Returns:
            None.
        """

        await self.bot.wait_until_ready()
        today, now = datetime.today(), datetime.now()
        time_until_tomorrow = (datetime(year=today.year, month=today.month, day=today.day) + timedelta(days=1)) - now
        await sleep(time_until_tomorrow.total_seconds())

    @commands.command(name='as', hidden=True)
    async def execute_command_as(
            self, ctx: Context, invoker: Union[discord.Member, discord.User], *, command: str
    ) -> None:
        """
        Executes a command as the specified user.

        Parameters:
            ctx (Context): The invocation context.
            invoker (Union[discord.Member, discord.User]): The user to perform the command as.
            command (str): The name of the command to execute.

        Returns:
            None.
        """

        message = copy(ctx.message)
        message.author = invoker
        message.content = (ctx.prefix or ctx.bot.default_prefix) + command
        context = await self.bot.get_context(message)
        await self.bot.invoke(context)

    @commands.guild_only()
    @commands.command(name='archive', hidden=True)
    async def archive(self, ctx: Context, target: int) -> None:
        """
        Archives a channel as efficiently as possible. Places messages without attachments, files, or embeds into a
        buffer and sends the buffer when the message character limit is exceeded.

        Parameters:
            ctx (Context): The invocation context.
            target (int): The beginning channel id (archive this channel).

        Returns:
            None.
        """

        assert ctx.guild is not None  # `@guild_only` handles this

        target_channel = self.bot.get_channel(target)

        if target_channel is None or not isinstance(target_channel, (discord.TextChannel, discord.CategoryChannel)):
            await ctx.send("Couldn't fetch target channel.")
            return

        # try to create the new archive channel
        category = await ctx.guild.create_category(name=target_channel.name)

        if isinstance(target_channel, discord.TextChannel):
            channel_list: Sequence[discord.abc.GuildChannel] = [target_channel]
        else:
            channel_list = target_channel.channels

        # if the original or the new destination is unavailable, stop the process
        if target_channel is None or category is None:
            await ctx.send('Could not fetch one or more channels.')

        # otherwise, begin the archive process
        else:
            for base_channel in [channel for channel in channel_list if isinstance(channel, discord.TextChannel)]:
                # reset buffer after each channel
                buffer = ''
                channel = await category.create_text_channel(name=base_channel.name)
                async with channel.typing():
                    async for message in base_channel.history(limit=None, oldest_first=True):
                        # for each message, check to see if there's attachments or embeds
                        attachments = None
                        embeds = None

                        # check for attachments and if any, try to convert them to files for sending
                        if len(message.attachments) > 0:
                            with suppress(discord.HTTPException):
                                attachments = [
                                    await attachment.to_file()
                                    for attachment in message.attachments
                                    if attachment.size <= 8000000
                                ]
                                bad_attachments = [f'`<Bad File: {attachment.filename} | File Size: {attachment.size}>`'
                                                   for attachment in message.attachments if attachment.size > 8000000]

                                if bad_attachments:
                                    if message.content:
                                        message.content += '\n'
                                    message.content += '\n'.join(bad_attachments)

                        # check for embeds and if any, save the first one (shouldn't have multiple embeds)
                        if len(message.embeds) > 0:
                            with suppress(discord.HTTPException):
                                embeds = ([embed for embed in message.embeds])[0]

                        # case 1: attachments or embeds with a non-empty buffer
                        if (attachments or embeds) and buffer != '':
                            # forcible send the existing buffer
                            await try_to_send_buffer(channel, buffer, True)

                            # new buffer contents are the contents of the current message
                            buffer = f'\n\n**{message.author} - {format_dt(message.created_at, "F")}**\n'
                            buffer += message.content

                            # if the current message contents exceed the limit, send the maximum first portion
                            #   and save the remaining portion
                            if len(buffer) > 2000:
                                buffer = await try_to_send_buffer(channel, buffer)

                            # send the remaining portion of the buffer, attachments or embeds, and clear the buffer
                            # mypy incorrectly identifies send kwargs as non-optional
                            await channel.send(
                                content=buffer, embed=embeds, files=attachments,  # type: ignore[arg-type]
                                allowed_mentions=discord.AllowedMentions.none()
                            )
                            buffer = ''

                        # case 2: attachments or embeds with an empty buffer
                        elif attachments or embeds:
                            # since the buffer is empty, new buffer contents are the contents of the current message
                            buffer = f'\n\n**{message.author} - {format_dt(message.created_at, "F")}**\n'
                            buffer += message.content

                            # if the current message contents don't exceed the limit, send everything
                            if len(buffer) <= 2000:
                                await channel.send(
                                    content=buffer, embed=embeds, files=attachments,  # type: ignore[arg-type]
                                    allowed_mentions=discord.AllowedMentions.none()
                                )
                            # otherwise, break up the buffer where appropriate, then send everything
                            else:
                                buffer = await try_to_send_buffer(channel, buffer)
                                await channel.send(
                                    content=buffer, embed=embeds, files=attachments,  # type: ignore[arg-type]
                                    allowed_mentions=discord.AllowedMentions.none()
                                )

                            # reset the buffer
                            buffer = ''

                        # case 3: no attachments or embeds and a non-empty buffer
                        else:
                            # add the current message contents to the buffer
                            buffer += f'\n\n**{message.author} - {format_dt(message.created_at, "F")}**\n'
                            buffer += message.content

                            # if the buffer exceeds the maximum length, try to send the buffer (and preserve the extra)
                            if len(buffer) > 2000:
                                buffer = await try_to_send_buffer(channel, buffer)

                    # once finished processing all messages, forcibly send the entire buffer
                    if buffer != '':
                        await try_to_send_buffer(channel, buffer, True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Adds all members of the forum to newly created threads.

        Parameters:
            message (discord.Message): The newly created message.

        Returns:
            None.
        """

        if not message.guild or message.guild.id != 1084581614878728305:
            return

        if not isinstance(message.channel, discord.Thread) or message.id != message.channel.id:
            return

        members_to_add = [
            member for member in message.guild.members if
            not member.bot and member.id not in [146517998205796352, message.author.id]
        ]

        await message.channel.send(
            f'_Tagging Members for Notifications: {", ".join([member.mention for member in members_to_add])}_'
        )

    async def cog_unload(self) -> None:
        """
        A method detailing custom extension unloading procedures.
        Clears internal caches and immediately and forcefully exits any discord.ext.tasks.

        Parameters:
            None.

        Returns:
            None.
        """

        self.logging_line_break.cancel()

        bot_logger.info('Completed Unload for Cog: Admin')


async def try_to_send_buffer(messagable: Messageable, buffer: str, force: bool = False) -> str:
    """
    Parses a string buffer and either sends or returns the buffer in an optimal break point.

    Parameters:
        messagable (discord.abc.Messageable): The channel to send the buffer to.
        buffer (str): The contents of the buffer.
        force (bool): Whether to forcibly send the remaining buffer contents or return them. Default: False.

    Returns:
        (Union[Message, str]): Returns a discord.Message object if the entire buffer was sent. Returns a str if
            the second half of the buffer was not sent.
    """

    # if the buffer is within our limit, no special calculations are needed
    if len(buffer) <= 2000:
        await messagable.send(buffer, allowed_mentions=discord.AllowedMentions.none())
        return ''

    # default break index to 1800
    break_index = 1800

    # starting from the last character in the maximum buffer length, look for a nice character to break on
    for index, character in reversed(list(enumerate(buffer[:2000]))):
        if character in ('\n', '.', '!', '?'):
            break_index = index + 1
            break

    # check for code blocks
    if code_backticks := [m.start() for m in finditer('```', buffer)]:
        # generate pairs of code blocks to check
        # this prevents breaking a code block and causing weird formatting
        for start, end in pairs(code_backticks):
            if start < break_index < end:
                break_index = start
                break

    # once all checks are performed, send the first portion of the buffer
    await messagable.send(str(buffer[:break_index]), allowed_mentions=discord.AllowedMentions.none())

    # depending on parameters, either send or return the remaining portion of the buffer
    if force:
        await messagable.send(str(buffer[break_index:]), allowed_mentions=discord.AllowedMentions.none())
        return ''
    else:
        return str(buffer[break_index:])


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Admin(bot))
    bot_logger.info('Completed Setup for Cog: Admin')
