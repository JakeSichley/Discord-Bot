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
from discord import TextChannel, HTTPException, Message, Embed
from io import StringIO
from contextlib import redirect_stdout
from textwrap import indent
from traceback import format_exc
from utils.utils import localize_time, pairs
from re import finditer
from typing import Union, Optional
from dreambot import DreamBot
from utils.checks import ensure_git_credentials
from utils.network_utils import network_request, NetworkReturnType
from utils.database_utils import execute_query, retrieve_query
from aiosqlite import Error as aiosqliteError
from datetime import datetime


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
        """

        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        """
        A method that registers a cog-wide check.
        Requires the invoking user to be the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            (boolean): Whether the invoking user is the bot's owner.
        """

        return await self.bot.is_owner(ctx.author)

    @commands.command(name='adminhelp', aliases=['ahelp'], hidden=True)
    async def admin_help_command(self, ctx: commands.Context) -> None:
        """
        A command to generate help information for the Admin cog.
        The native help command will not generate information for the Admin cog, since all commands are hidden.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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
            help_string += f'\n  {command.name:{longest_command_name + 1}} {command.short_doc}'

        help_string += '\n\nType ?help command for more info on a command.\n' \
                       'You can also type ?help category for more info on a category.```'

        await ctx.send(help_string)

    @commands.command(name='reload', aliases=['load'], hidden=True)
    async def reload(self, ctx: commands.Context, module: str) -> None:
        """
        A command to reload a module.
        If the reload fails, the previous state of module is maintained.
        If the module is not loaded, attempt to load the module.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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
    async def unload(self, ctx: commands.Context, module: str) -> None:
        """
        A command to unload a module.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.
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
            self.bot.unload_extension('cogs.' + module)
            await ctx.send(f'Unloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Unload Module: `{module}`')

    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx: commands.Context) -> None:
        """
        A command to stop (close/logout) the bot.
        The command must be confirmed to complete the logout.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            First: A confirmation message.
            Second: The status of the logout method.

        Returns:
            None.
        """

        await ctx.send('Closing Event Loop.')
        await self.bot.close()

    @commands.command(name='eval', hidden=True)
    async def _eval(self, ctx: commands.Context, _ev: str) -> None:
        """
        A command to evaluate a python statement.
        Should the evaluation encounter an exception, the output will be the exception details.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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
    async def sql(self, ctx: commands.Context, *, query: str) -> None:
        """
        A command to execute a sqlite3 statement.
        If the statement type is 'SELECT', successful executions will send the result.
        For other statement types, successful executions will send 'Executed'.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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
            if (query.upper()).startswith('SELECT'):
                result = await retrieve_query(self.bot.database, query)
                await ctx.send(str(result))
            else:
                affected = await execute_query(self.bot.database, query)
                await ctx.send(f'Executed. {affected} rows affected.')
        except aiosqliteError as e:
            await ctx.send(f'Error: {e}')

    @commands.command(name='reloadprefixes', aliases=['rp'], hidden=True)
    async def reload_prefixes(self, ctx: commands.Context) -> None:
        """
        A command to reload the bot's store prefixes.
        Prefixes are normally reloaded when explicitly changed.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Success: 'Reloaded Prefixes'.
            Failure: The error that arose during execution.

        Returns:
            None.
        """

        await self.bot.retrieve_prefixes()
        await ctx.send('Reloaded Prefixes.')

    @commands.command(name='resetcooldown', aliases=['rc'], hidden=True)
    async def reset_cooldown(self, ctx: commands.Context, command: str) -> None:
        """
        A command to reset the cooldown of a command.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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
    async def _exec(self, ctx: commands.Context, *, body: str) -> None:
        """
        A command to execute a Python code block and output the result, if any.

        Checks:
            is_owner(): Whether the invoking user is the bot's owner.

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

    @ensure_git_credentials()
    @commands.group(name='git', hidden=True)
    async def git(self, ctx: commands.Context) -> None:
        """
        Parent command that handles git related commands.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('git')

    @git.command(name='pull', aliases=['p'], hidden=True)
    async def git_pull(self, ctx: commands.Context, branch: Optional[str]):
        """
        Pulls the latest commit from the specified branch.

        Parameters:
            ctx (commands.Context): The invocation context.
            branch (str): The name of the target branch.

        Returns:
            None.
        """

        # r'(?:Successfully installed )(.+ ?)+'
        pass

    @git.command(name='branches', aliases=['branch', 'b'], hidden=True)
    async def git_branches(self, ctx: commands.Context) -> None:
        """
        Fetches a list of branches from the bot's repository.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        headers = {
            'User-Agent': f"{self.bot.git['git_user']}-{self.bot.git['git_repo']}",
            'authorization': f"token {self.bot.git['git_token']}"
        }

        branches_url = f"https://api.github.com/repos/{self.bot.git['git_user']}/{self.bot.git['git_repo']}/branches"
        users_url = f"https://api.github.com/users/{self.bot.git['git_user']}"
        commits_url = f"https://api.github.com/repos/{self.bot.git['git_user']}/{self.bot.git['git_repo']}/commits/"

        branch_data = await network_request(branches_url, headers=headers, return_type=NetworkReturnType.JSON)
        user_data = await network_request(
            users_url, headers=headers, return_type=NetworkReturnType.JSON, raise_errors=False
        )
        latest_commit_data = {
            branch['name']:
                await network_request(
                    commits_url + branch['commit']['sha'], headers=headers, return_type=NetworkReturnType.JSON
                ) for branch in branch_data[-5:]
        }

        try:
            thumbnail = user_data['avatar_url']
        except (KeyError, TypeError):
            thumbnail = 'https://pbs.twimg.com/profile_images/1414990564408262661/r6YemvF9_400x400.jpg'

        embed = Embed(
            title=f"Branches for **{self.bot.git['git_repo']}**",
            colour=0x58a6ff,
            url=f"https://github.com/{self.bot.git['git_user']}/{self.bot.git['git_repo']}"
        )
        embed.set_thumbnail(url=thumbnail)
        for branch, commit in latest_commit_data.items():
            embed.add_field(
                name=branch,
                value=f"{commit['commit']['author']['name']} - "
                      f"{localize_time(datetime.strptime(commit['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ'))}",
                inline=False
            )
        embed.set_footer(text="Please report any issues to my owner!")

        await ctx.send(embed=embed)

    @commands.command(name='archive', hidden=True)
    async def archive(self, ctx: commands.Context, target: int) -> None:
        """
        Archives a channel as efficiently as possible. Places messages without attachments, files, or embeds into a
        buffer and sends the buffer when the message character limit is exceeded.

        Parameters:
            ctx (commands.Context): The invocation context.
            target (int): The beginning channel id (archive this channel).

        Returns:
            None.
        """

        target = self.bot.get_channel(target)

        # try to create the new archive channel
        category = await ctx.guild.create_category(name=target.name)

        if isinstance(target, TextChannel):
            channel_list = [target]
        else:
            channel_list = target.channels

        # if the original or the new destination is unavailable, stop the process
        if target is None or category is None:
            await ctx.send('Could not fetch one or more channels.')

        # otherwise, begin the archive process
        else:
            for base_channel in [channel for channel in channel_list if isinstance(channel, TextChannel)]:
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
                            try:
                                attachments = [await attachment.to_file() for attachment in message.attachments
                                               if attachment.size <= 8000000]
                                bad_attachments = [f'`<Bad File: {attachment.filename} | File Size: {attachment.size}>`'
                                                   for attachment in message.attachments if attachment.size > 8000000]

                                if bad_attachments:
                                    if message.content:
                                        message.content += '\n'
                                    message.content += '\n'.join(bad_attachments)

                            except HTTPException:
                                pass

                        # check for embeds and if any, save the first one (shouldn't have multiple embeds)
                        if len(message.embeds) > 0:
                            try:
                                embeds = ([embed for embed in message.embeds])[0]
                            except HTTPException:
                                pass

                        # case 1: attachments or embeds with a non-empty buffer
                        if (attachments or embeds) and buffer != '':
                            # forcible send the existing buffer
                            await try_to_send_buffer(channel, buffer, True)

                            # new buffer contents are the contents of the current message
                            buffer = f'\n\n**{message.author} - {localize_time(message.created_at)}**\n'
                            buffer += message.content

                            # if the current message contents exceed the limit, send the maximum first portion
                            #   and save the remaining portion
                            if len(buffer) > 2000:
                                buffer = await try_to_send_buffer(channel, buffer)

                            # send the remaining portion of the buffer, attachments or embeds, and clear the buffer
                            await channel.send(content=buffer, embed=embeds, files=attachments)
                            buffer = ''

                        # case 2: attachments or embeds with an empty buffer
                        elif attachments or embeds:
                            # since the buffer is empty, new buffer contents are the contents of the current message
                            buffer = f'\n\n**{message.author} - {localize_time(message.created_at)}**\n'
                            buffer += message.content

                            # if the current message contents don't exceed the limit, send everything
                            if len(buffer) <= 2000:
                                await channel.send(content=buffer, embed=embeds, files=attachments)
                            # otherwise, break up the buffer where appropriate, then send everything
                            else:
                                buffer = await try_to_send_buffer(channel, buffer)
                                await channel.send(content=buffer, embed=embeds, files=attachments)

                            # reset the buffer
                            buffer = ''

                        # case 3: no attachments or embeds and a non-empty buffer
                        else:
                            # add the current message contents to the buffer
                            buffer += f'\n\n**{message.author} - {localize_time(message.created_at)}**\n'
                            buffer += message.content

                            # if the buffer exceeds the maximum length, try to send the buffer (and preserve the extra)
                            if len(buffer) > 2000:
                                buffer = await try_to_send_buffer(channel, buffer)

                    # once finished processing all messages, forcibly send the entire buffer
                    if buffer != '':
                        await try_to_send_buffer(channel, buffer, True)


async def try_to_send_buffer(channel: TextChannel, buffer: str, force: bool = False) -> Union[Message, str]:
    """
    Parses a string buffer and either sends or returns the buffer in an optimal break point.

    Parameters:
        channel (discord.TextChannel): The channel to send the buffer to.
        buffer (str): The contents of the buffer.
        force (bool): Whether to forcibly send the remaining buffer contents or return them. Default: False.

    Returns:
        (Union[Message, str]): Returns a discord.Message object if the entire buffer was sent. Returns a str if
            the second half of the buffer was not sent.
    """

    # if the buffer is within our limit, no special calculations are needed
    if len(buffer) <= 2000:
        return await channel.send(buffer)

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
    await channel.send(str(buffer[:break_index]))

    # depending on parameters, either send or return the remaining portion of the buffer
    if force:
        return await channel.send(str(buffer[break_index:]))
    else:
        return str(buffer[break_index:])


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Admin(bot))
    print('Completed Setup for Cog: Admin')
