from os import getcwd, listdir
from discord.ext.commands import ExtensionError, Bot, when_mentioned_or
from datetime import datetime
from typing import Optional, List, Any, Dict
import discord
import aiosqlite
import logging


class DreamBot(Bot):
    """
    A commands.Bot subclass that contains the main bot implementation.

    Attributes:
        prefixes (dict): A quick reference for accessing a guild's specified prefix.
        initialized (boolean): Whether or not the bot has performed initialization steps.
        uptime (datetime.datetime): The time the bot was initialized.
        database (str): The name of the database the bot uses.
        default_prefix (str): The default prefix to use if a guild has not specified one.
    """

    def __init__(self, intents: discord.Intents, database: str, prefix: str, owner: int,
                 options: Optional[Dict[str, Optional[Any]]]) -> None:
        """
        The constructor for the DreamBot class.

        Parameters:
            None.

        Returns:
            None.
        """

        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_id=owner, max_messages=None,
                         intents=intents)
        self.wavelink = None
        self.prefixes = {}
        self.initialized = False
        self.uptime = datetime.now()
        self.database = database
        self.default_prefix = prefix

        # optionals
        self._status_type = options.pop('status_type', discord.ActivityType(1))
        self._status_text = options.pop('status_text', None)
        self.disabled_cogs = options.pop('disabled_cogs', [])

        # git optionals
        self.git = options.pop('git', None)

        # load our cogs
        for cog in listdir(getcwd() + '\\cogs'):
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

    async def on_message(self, message: discord.Message) -> None:
        """
        A Client.event() method that is called when a discord.Message is created and sent.

        Parameters:
            message (discord.Message): The message that was sent.

        Returns:
            None.
        """

        if message.author == self.user:
            return

        if message.guild is None:
            print(f'Direct Message from {message.author}\nContent: {message.clean_content}')

        await self.process_commands(message)

    async def retrieve_prefixes(self) -> None:
        """
        A method that creates a quick-reference dict for guilds and their respective prefixes.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.database) as db:
                async with db.execute("SELECT * FROM Prefixes") as cursor:
                    async for guild, prefix in cursor:
                        self.prefixes[int(guild)] = prefix

        except aiosqlite.Error as e:
            print(f'Retrieve Prefixes Error: {e}')

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


async def get_prefix(bot: DreamBot, message: discord.Message) -> List[str]:
    """
    A method that retrieves the prefix the bot should look for in a specified message.

    Parameters:
        bot (DreamBot): The Discord bot class.
        message (discord.Message): The message to retrieve the prefix for.

    Returns:
        (List[str]): An iterable of valid prefix(es), including when the bot is mentioned.
    """

    if message.guild is not None and message.guild.id in bot.prefixes:
        return when_mentioned_or(bot.prefixes[message.guild.id])(bot, message)
    return when_mentioned_or(bot.default_prefix)(bot, message)
