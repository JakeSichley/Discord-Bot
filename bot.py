import os
import discord
import logging
import aiosqlite
from dotenv import load_dotenv
from discord.ext.commands import ExtensionError, Bot, when_mentioned_or
import datetime

print(f'Current Discord Version: {discord.__version__}')
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = int(os.getenv('OWNER_ID'))
PREFIX = os.getenv('PREFIX')
DATABASE = os.getenv('DATABASE')

# load extensions (filename)
initial_extensions = ('admin', 'ddo', 'memecoin', 'utility', 'exceptions', 'moderation')
# unused extensions: None

# define cogs with tasks for reconnection behavior
task_extensions = ('DDO',)


class DreamBot(Bot):
    """
    A commands.Bot subclass that contains the main bot implementation.

    Constants:
        DATABASE_NAME (str): The name of the database the bot uses.
        DEFAULT_PREFIX (str): The default prefix to use if a guild has not specified one.

    Attributes:
        prefixes (dict): A quick reference for accessing a guild's specified prefix.
        initialized (boolean): Whether or not the bot has performed initialization steps.
        uptime (datetime.datetime): The time the bot was initialized.
    """

    DATABASE_NAME = DATABASE
    DEFAULT_PREFIX = PREFIX

    def __init__(self):
        """
        The constructor for the DreamBot class.

        Parameters:
            None.
        """

        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_id=OWNER, max_messages=None)
        self.prefixes = {}
        self.initialized = False
        self.uptime = 0

        # load our default cogs
        for cog in initial_extensions:
            try:
                self.load_extension('cogs.' + cog)
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
            await self.change_presence(status=discord.Status.online, activity=discord.Activity(name='My Spaghetti Code',
                                       type=discord.ActivityType.watching))
            await self.retrieve_prefixes()
            self.uptime = datetime.datetime.now()
            self.initialized = True

        print('READY')

    async def on_message(self, message):
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
            print(f'Direct Message from {message.author}\nContent: {message.content}')

        await self.process_commands(message)

    async def retrieve_prefixes(self):
        """
        A method that creates a quick-reference dict for guilds and their respective prefixes.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.DATABASE_NAME) as db:
                async with db.execute("SELECT * FROM Prefixes") as cursor:
                    async for guild, prefix in cursor:
                        self.prefixes[int(guild)] = prefix

        except aiosqlite.Error as e:
            print(f'Retrieve Prefixes Error: {e}')

    def run(self):
        """
        A blocking method that handles event loop initialization.
        Note: Must be the last method called.

        Parameters:
            None.

        Returns:
            None.
        """

        super().run(TOKEN)


async def get_prefix(bot, message):
    """
    A method that retrieves the prefix the bot should look for in a specified message.

    Parameters:
        bot (DreamBot): The Discord bot class.
        message (discord.Message): The message to retrieve the prefix for.

    Returns:
        (iterable): An iterable of valid prefix(es), including when the bot is mentioned.
    """

    if message.guild is not None and message.guild.id in bot.prefixes:
        return when_mentioned_or(bot.prefixes[message.guild.id])(bot, message)
    return when_mentioned_or(PREFIX)(bot, message)


# Run the bot
dream_bot = DreamBot()
dream_bot.run()
