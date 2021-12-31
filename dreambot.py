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

from os import getcwd, listdir, path
from discord.ext.commands import ExtensionError, Bot, when_mentioned_or
from datetime import datetime
from typing import Optional, List, Any, Dict
from utils.database_utils import retrieve_query
from aiosqlite import Error as aiosqliteError
from utils.context import Context
import discord
import logging


class DreamBot(Bot):
    """
    A commands.Bot subclass that contains the main bot implementation.

    Attributes:
        prefixes (dict): A quick reference for accessing a guild's specified prefix.
        initialized (boolean): Whether the bot has performed initialization steps.
        uptime (datetime.datetime): The time the bot was initialized.
        database (str): The name of the database the bot uses.
        default_prefix (str): The default prefix to use if a guild has not specified one.
        environment (str): Environment string. Disable features (such as firebase logging) when not 'PROD'.
        wavelink (wavelink.Client): The bot's wavelink client. This initialization prevents attr errors in 'Music'.
        disabled_cogs (List[str]): A list of cogs the bot should not load on initialization.
        _status_type (Optional[int]): The discord.ActivityType to set the bot's status to.
        _status_text (Optional[str]): The text of the bot's status.
    """

    def __init__(self, intents: discord.Intents, database: str, prefix: str, owner: int, environment: str,
                 options: Optional[Dict[str, Optional[Any]]]) -> None:
        """
        The constructor for the DreamBot class.

        Parameters:
            intents (discord.Intents): Which gateway features to enable for the bot.
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

        super().__init__(
            command_prefix=get_prefix, case_insensitive=True, owner_id=owner, max_messages=None, intents=intents
        )
        self.wavelink = None
        self.prefixes = {}
        self.initialized = False
        self.uptime = datetime.now()
        self.database = database
        self.default_prefix = prefix
        self.environment = environment

        # optionals
        self._status_type = options.pop('status_type', discord.ActivityType(1))
        self._status_text = options.pop('status_text', None)
        self.disabled_cogs = options.pop('disabled_cogs', [])

        # git optionals
        self.git = options.pop('git', None)

        # load our cogs
        for cog in listdir(path.join(getcwd(), 'cogs')):
            # only load python files that we haven't explicitly disabled
            if cog.endswith('.py') and cog[:-3] not in self.disabled_cogs:
                try:
                    self.load_extension(f'cogs.{cog[:-3]}')
                except ExtensionError as e:
                    print(e)

    async def on_ready(self):
        """
        A Client.event() method that is called when the client is done preparing the data received from Discord.
        Note: Event does not guarantee position and may be called multiple times.
        'initialized' is used to ensure bot setup only happens once. Some setup cannot be performed in __init__ because
            __init__ is not asynchronous.

        Parameters:
            None.

        Returns:
            None.
        """

        if not self.initialized:
            await self.change_presence(status=discord.Status.online, activity=discord.Activity(name=self._status_text,
                                       type=self._status_type))
            await self.retrieve_prefixes()
            self.initialized = True

            logging.log(logging.INFO, 'DreamBot Ready: Prefixes and Presence initialized')

    async def retrieve_prefixes(self) -> None:
        """
        A method that creates a quick-reference dict for guilds and their respective prefixes.

        Parameters:
            None.

        Returns:
            None.
        """

        current_prefixes = self.prefixes

        try:
            self.prefixes.clear()
            result = await retrieve_query(self.database, 'SELECT * FROM PREFIXES')

            if result:
                self.prefixes = {int(guild): prefix for guild, prefix in result}

        except aiosqliteError:
            self.prefixes = current_prefixes

    def run(self, token: str) -> None:
        """
        A blocking method that handles event loop initialization.
        Note: Must be the last method called.

        Parameters:
            None.

        Returns:
            None.
        """

        super().run(token)

    async def get_context(self, message: discord.Message, *, cls: classmethod = Context) -> Context:
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

    return when_mentioned_or(bot.prefixes.get(guild_id, bot.default_prefix))(bot, message)
