import discord
import logging
import aiosqlite
from os import getenv, getcwd, listdir
from sys import version
from dotenv import load_dotenv
from discord.ext.commands import ExtensionError, Bot, when_mentioned_or
from datetime import datetime
from asyncio import sleep

print(f'Current Python Version: {version}')
print(f'Current Discord Version: {discord.__version__}')
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')
OWNER = int(getenv('OWNER_ID'))
PREFIX = getenv('PREFIX')
DATABASE = getenv('DATABASE')

# explicitly disabled cogs
disabled_cogs = ()

# specify intents (members requires explicit opt-in via dev portal)
intents = discord.Intents(guilds=True, members=True, bans=True, emojis=True, voice_states=True, messages=True,
                          reactions=True)


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
    ALERTS_CHANNEL = 742210950681067540

    def __init__(self):
        """
        The constructor for the DreamBot class.

        Parameters:
            None.
        """

        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_id=OWNER, max_messages=None,
                         intents=intents)
        self.prefixes = {}
        self.initialized = False
        self.uptime = datetime.now()

        # load our cogs
        for cog in listdir(getcwd() + '\cogs'):
            # only load python files that we haven't explicitly disabled
            if cog.endswith('.py') and cog[:-3] not in disabled_cogs:
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
            await self.change_presence(status=discord.Status.online, activity=discord.Activity(name='My Spaghetti Code',
                                       type=discord.ActivityType.watching))
            await self.retrieve_prefixes()
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
            print(f'Direct Message from {message.author}\nContent: {message.clean_content}')

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

    async def alert(self, **kwargs: dict) -> None:
        """
        A bot-wide method that allows alerts to be documented in the alerts channel for immediate notifications.

        Parameters:
            kwargs (dict): A dictionary of kwargs to build the alert with (Expected: {cog, meth, details}).

        Returns:
            None.
        """

        alert_string = f'**Alert Raised in Cog:** {kwargs.pop("cog")}' \
                       f'\n**Method:** {kwargs.pop("meth")}' \
                       f'\n**Time:** {datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")}' \
                       f'\n\n**Details:** {kwargs.pop("details")}\n'
        alert_string += '\n'.join(f'**{key}:** {item}' for key, item in kwargs.items())

        alert_channel: discord.TextChannel = self.get_channel(self.ALERTS_CHANNEL)

        for _ in range(5):
            try:
                await alert_channel.send(alert_string)
                return
            except discord.HTTPException:
                await sleep(15)

        print('FAILED TO SEND ALERT')
        print(alert_string)


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
