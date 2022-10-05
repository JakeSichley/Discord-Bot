"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

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

from os import getcwd, listdir, path
from discord.ext.commands import ExtensionError, Bot, when_mentioned
from datetime import datetime
from typing import Optional, List, Any, Dict, Type
from utils.database_utils import retrieve_query
from aiosqlite import Error as aiosqliteError
from utils.context import Context
from utils.utils import generate_activity
from discord.ext import tasks
from copy import deepcopy
import discord
import logging


class DreamBot(Bot):
    """
    A commands.Bot subclass that contains the main bot implementation.

    Attributes:
        prefixes (dict): A quick reference for accessing a guild's specified prefix.
        uptime (datetime.datetime): The time the bot was initialized.
        database (str): The name of the database the bot uses.
        default_prefix (str): The default prefix to use if a guild has not specified one.
        environment (str): Environment string. Disable features (such as firebase logging) when not 'PROD'.
        wavelink (wavelink.Client): The bot's wavelink client. This initialization prevents attr errors in 'Music'.
        disabled_cogs (List[str]): A list of cogs the bot should not load on initialization.
        _status_type (Optional[int]): The discord.ActivityType to set the bot's status to.
        _status_text (Optional[str]): The text of the bot's status.
    """

    def __init__(self, database: str, prefix: str, owner: int, environment: str,
                 options: Optional[Dict[str, Optional[Any]]]) -> None:
        """
        The constructor for the DreamBot class.

        Parameters:
            database (str): The filename of the bot's database.
            prefix (str): The bot's default prefix.
            owner (int): The ID of the bot's owner. Required for most 'Admin' commands.
            environment (str): Environment string. Disable features (such as firebase logging) when not 'PROD'.
            options (Optional[Dict[str, Optional[Any]]]): Additional setup features for the bot.
                _status_type (int): The discord.ActivityType to set the bot's status to.
                _status_text (str): The text of the bot's status.
                git (Dict[str, str]): Username, repository name, and personal access token.


        Returns:
            None.
        """

        intents = discord.Intents(message_content=True, guilds=True, members=True, bans=True, emojis=True,
                                  voice_states=True, messages=True, reactions=True)

        super().__init__(
            command_prefix=get_prefix, case_insensitive=True, owner_id=owner, max_messages=None, intents=intents
        )
        self.wavelink = None
        self.prefixes = {}
        self.uptime = datetime.now()
        self.database = database
        self.default_prefix = prefix
        self.environment = environment

        # optionals
        # noinspection PyTypeChecker
        self._status_type = options.pop('status_type', discord.ActivityType(0))
        self._status_text = options.pop('status_text', None)
        self.disabled_cogs = options.pop('disabled_cogs', [])

        # git optionals
        self.git = options.pop('git', None)

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

        await self.retrieve_prefixes()

        # load our cogs
        for cog in listdir(path.join(getcwd(), 'cogs')):
            # only load python files that we haven't explicitly disabled
            if cog.endswith('.py') and cog[:-3] not in self.disabled_cogs:
                try:
                    await self.load_extension(f'cogs.{cog[:-3]}')
                except ExtensionError as e:
                    logging.error(f'Failed Setup for Cog: {cog[:-3].capitalize()}. {e}')

    @tasks.loop(minutes=30)
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
            logging.error(f"Couldn't get a member instance of bot. Exception type: {type(e)}.")
            return

        if bot_member.activity:
            return

        activity = await generate_activity(self._status_text, self._status_type)
        await self.change_presence(status=discord.Status.online, activity=activity)

        logging_level = logging.info if self.refresh_presence.current_loop == 0 else logging.error
        logging_level(f'Bot presence was empty. Refreshed presence.')

    @refresh_presence.before_loop
    async def before_refresh_presence_loop(self) -> None:
        """
        A pre-task method to ensure the bot is ready before executing.

        Returns:
            None.
        """

        await self.wait_until_ready()

    async def retrieve_prefixes(self) -> None:
        """
        A method that creates a quick-reference dict for guilds and their respective prefixes.

        Parameters:
            None.

        Returns:
            None.
        """

        current_prefixes = deepcopy(self.prefixes)

        try:
            self.prefixes.clear()
            result = await retrieve_query(self.database, 'SELECT * FROM PREFIXES')

            for guild, prefix in result:
                if int(guild) in self.prefixes:
                    self.prefixes[int(guild)].append(prefix)
                else:
                    self.prefixes[int(guild)] = [prefix]

        except aiosqliteError as e:
            logging.error(f'Failed prefix retrieval. {e}')
            self.prefixes = current_prefixes
        else:
            logging.info('Completed prefix retrieval')

    async def get_context(self, message: discord.Message, *, cls: Type[Context] = Context) -> Context:
        """
        Creates a Context instance for the current command invocation.

        Parameters:
            message (discord.Message): The message to generate a context instance for.
            cls (classmethod): The classmethod to generate the context instance with.

        Returns:
            (Context): The custom context instance.
        """

        return await super().get_context(message, cls=cls)


async def get_prefix(bot: DreamBot, message: discord.Message) -> List[str]:
    """
    A method that retrieves the prefix the bot should look for in a specified message.

    Parameters:
        bot (DreamBot): The Discord bot class.
        message (discord.Message): The message to retrieve the prefix for.

    Returns:
        (List[str]): An iterable of valid prefix(es), including when the bot is mentioned.
    """

    guild_id = message.guild.id if message.guild else None
    mentions = when_mentioned(bot, message)
    additional_prefixes = list(bot.prefixes.get(guild_id, bot.default_prefix))

    return mentions + additional_prefixes
