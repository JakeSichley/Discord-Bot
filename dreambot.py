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

from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from os import getcwd, listdir, path
from sys import stderr, exc_info
from traceback import print_exception, format_exception
from typing import Optional, List, Dict, Type, DefaultDict, TypedDict, Union, Any

import discord
from aiohttp import ClientSession
from discord.ext import tasks
from discord.ext.commands import ExtensionError, Bot, when_mentioned
from google.cloud import errorreporting_v1beta1 as error_reporting

from utils.context import Context
from utils.cooldowns import CooldownMapping
from utils.database.cache import TableCache
from utils.logging_formatter import bot_logger
from utils.utils import generate_activity

GitOptionals = TypedDict(
    'GitOptionals',
    {
        'git_user': Optional[str],
        'git_repo': Optional[str],
        'git_token': Optional[str]
    }
)

Optionals = TypedDict(
    'Optionals',
    {
        'status_type': discord.ActivityType,
        'status_text': Optional[str],
        'disabled_cogs': List[str],
        'firebase_project': Optional[str],
        'git': Optional[GitOptionals]
    },
    total=False
)


class DreamBot(Bot):
    """
    A commands.Bot subclass that contains the main bot implementation.

    Attributes:
        cache (TableCache): A cache for quick access to frequently accessed table information.
        uptime (datetime.datetime): The time the bot was initialized.
        database (str): The name of the bot's database.
        session (aiohttp.ClientSession): The bot's current client session.
        default_prefix (str): The default prefix to use if a guild has not specified one.
        environment (str): Environment string. Disable features (such as firebase logging) when not 'PROD'.
        wavelink (wavelink.Client): The bot's wavelink client. This initialization prevents attr errors in 'Music'.
        dynamic_cooldowns (Dict[str, DefaultDict[int, CooldownMapping]]): Dynamic Cooldown mapping for commands.
        _disabled_cogs (List[str]): A list of cogs the bot should not load on initialization.
        _status_type (Optional[int]): The discord.ActivityType to set the bot's status to.
        _status_text (Optional[str]): The text of the bot's status.
        _firebase_project (Optional[str]): The name of the bot's Firebase project.
        _reporting_client (Optional[ReportErrorsServiceAsyncClient]): The Firebase reporting client.
    """

    def __init__(self, prefix: str, owner: int, environment: str, database: str, options: Optionals) -> None:
        """
        The constructor for the DreamBot class.

        Parameters:
            prefix (str): The bot's default prefix.
            owner (int): The ID of the bot's owner. Required for most 'Admin' commands.
            environment (str): Environment string. Disable features (such as firebase logging) when not 'PROD'.
            options (Optional[Dict[str, Optional[Any]]]): Additional setup features for the bot.
                status_type (int): The discord.ActivityType to set the bot's status to.
                status_text (str): The text of the bot's status.
                firebase_project (str): The name of the bot's Firebase project.
                git (Dict[str, str]): Username, repository name, and personal access token.

        Returns:
            None.
        """

        intents = discord.Intents(message_content=True, guilds=True, members=True, bans=True, emojis=True,
                                  voice_states=True, messages=True, reactions=True)

        super().__init__(
            command_prefix=get_prefix, case_insensitive=True, owner_id=owner, max_messages=None, intents=intents
        )

        # connection, session will always be set as part of async initialization with context managers
        self.database = database
        self.session: ClientSession = None  # type: ignore[assignment]
        self.wavelink = None
        self.cache = TableCache(database)
        self.uptime = datetime.now()
        self.default_prefix = prefix
        self.environment = environment
        self.dynamic_cooldowns: Dict[str, DefaultDict[int, CooldownMapping]] = {
            'raw_yoink': defaultdict(CooldownMapping),
            'yoink': defaultdict(CooldownMapping),
            'invert': defaultdict(CooldownMapping)
        }

        # optionals
        options = options or dict()
        # noinspection PyTypeChecker
        self._status_type = options.pop('status_type', discord.ActivityType(0))
        self._status_text = options.pop('status_text', None)
        self._disabled_cogs: List[str] = options.pop('disabled_cogs')
        self._firebase_project = options.pop('firebase_project', None)
        self._reporting_client = None

        if environment == 'PROD':
            self._reporting_client = error_reporting.ReportErrorsServiceAsyncClient.from_service_account_file(
                r'firebase-auth.json'
            )

        # git optionals
        self.git: Optional[GitOptionals] = options.pop('git', None)

        # tasks
        self.refresh_presence.start()

    async def setup_hook(self) -> None:
        """
        A coroutine to be called to set up the bot.

        Parameters:
            None.

        Returns:
            None.
        """

        await self.cache.sync()

        # load our cogs
        for cog in listdir(path.join(getcwd(), 'cogs')):
            # only load python files that we haven't explicitly disabled
            if cog.endswith('.py') and cog[:-3] not in self._disabled_cogs:
                try:
                    await self.load_extension(f'cogs.{cog[:-3]}')
                except ExtensionError as error:
                    bot_logger.error(f'Failed Setup for Cog: {cog[:-3].capitalize()}. {error}')
                    print_exception(type(error), error, error.__traceback__, file=stderr)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        """
        The default error handler provided by the client.
        Maintains default logging behavior, but also reports the exception to the bot's dashboard as well.

        Parameters:
            event_method (str): The exception source method's name.
            *args (Any): Any arguments associated with the exception.
            **kwargs (Any): Any keyword-arguments associated with the exception.

        Returns:
            None.
        """

        _, exception, _ = exc_info()

        if exception and isinstance(exception, Exception):
            bot_logger.error(
                f"Encountered exception in '{event_method}'",
                exc_info=(type(exception), exception, exception.__traceback__),
            )

            await self.report_exception(exception)
        else:
            await super().on_error(event_method, *args, **kwargs)

    def report_command_failure(self, ctx: Context) -> None:
        """
        Used to report a failure in the provided context, for the purpose of dynamic cooldowns.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.command is None:
            return

        # use try -> except rather .get chaining, since .get would require creating unnecessary objects
        with suppress(KeyError):
            self.dynamic_cooldowns[ctx.command.qualified_name][ctx.author.id].increment_failure_count()

    def reset_dynamic_cooldown(self, ctx: Context) -> None:
        """
        Used to reset command failures in the provided context, for the purpose of dynamic cooldowns.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.command is None:
            return

        # .get chaining is acceptable since we're only removing entries
        self.dynamic_cooldowns.get(
            ctx.command.qualified_name, {}
        ).pop(ctx.author.id, None)  # type: ignore[call-overload]

    @tasks.loop(minutes=5)
    async def refresh_presence(self) -> None:
        """
        A task to refresh the bot's presence if the existing presence is dropped.

        Parameters:
            None.

        Returns:
            None.
        """

        # presence is a member-only attribute, need any guild to get a member instance of Bot
        try:
            bot_member: discord.Member = self.guilds[0].me
        except (IndexError, AttributeError) as e:
            bot_logger.error(f"Couldn't get a member instance of bot. Exception type: {type(e)}.")
            return

        if bot_member.activity or self._status_text is None:
            return

        activity = await generate_activity(self._status_text, self._status_type)
        await self.change_presence(status=discord.Status.online, activity=activity)

        logging_level = bot_logger.info if self.refresh_presence.current_loop == 0 else bot_logger.error
        logging_level(f'Bot presence was empty. Refreshed presence.')

    @refresh_presence.before_loop
    async def before_refresh_presence_loop(self) -> None:
        """
        A pre-task method to ensure the bot is ready before executing.

        Returns:
            None.
        """

        await self.wait_until_ready()

    async def get_context(  # type: ignore[override]
            self, origin: Union[discord.Message, discord.Interaction['DreamBot']], /, *, cls: Type[Context] = Context
    ) -> Context:
        """
        Creates a Context instance for the current command invocation.

        Parameters:
            origin: (Union[discord.Message, discord.Interaction]): The message/interaction to generate a context for.
            cls (Type[Context]): The classmethod to generate the context instance with.

        Returns:
            (Context): The custom context instance.
        """

        # noinspection PyTypeChecker
        return await super().get_context(origin, cls=cls)

    async def report_exception(self, exception: Exception) -> None:
        """
        Reports an exception to the bot's Firebase Error Reporting dashboard.

        Parameters:
            exception (Exception): The encountered exception.

        Returns:
            None.
        """

        if self._reporting_client and self._firebase_project:
            payload = generate_error_event(exception, self._firebase_project)
            await self._reporting_client.report_error_event(payload)


async def get_prefix(bot: DreamBot, message: discord.Message) -> List[str]:
    """
    A method that retrieves the prefix the bot should look for in a specified message.

    Parameters:
        bot (DreamBot): The Discord bot class.
        message (discord.Message): The message to retrieve the prefix for.

    Returns:
        (List[str]): An iterable of valid prefix(es), including when the bot is mentioned.
    """

    guild_id = message.guild.id if message.guild else -1
    mentions = when_mentioned(bot, message)
    additional_prefixes = list(bot.cache.prefixes.get(guild_id, bot.default_prefix))

    return mentions + additional_prefixes


def generate_error_event(exception: Exception, project_name: str) -> error_reporting.ReportErrorEventRequest:
    """
    Transforms an exception into a Google Cloud ReportErrorEventRequest.

    Parameters:
        exception (Exception): The encountered error.
        project_name (str): The name of the Firebase project.

    Returns:
        (errorreporting_v1beta1.ReportErrorEventRequest): The request payload.
    """

    event = error_reporting.ReportedErrorEvent()
    event.message = ''.join(format_exception(type(exception), exception, exception.__traceback__))

    # noinspection PyTypeChecker
    return error_reporting.ReportErrorEventRequest(
        project_name=project_name,
        event=event
    )
