from os import getenv
from sys import version
from dotenv import load_dotenv
from dreambot import DreamBot
import logging
import discord


def main() -> None:
    """
    Driver method.
    """

    print(f'Current Python Version: {version}')
    print(f'Current Discord Version: {discord.__version__}')
    logging.basicConfig(level=logging.INFO)

    load_dotenv()
    token = getenv('DISCORD_TOKEN')
    owner = int(getenv('OWNER_ID'))
    prefix = getenv('PREFIX')
    database = getenv('DATABASE')

    # explicitly disabled cogs
    disabled_cogs = ('memecoin', 'test', 'music', 'twitch', 'firestore',)

    # specify intents (members requires explicit opt-in via dev portal)
    intents = discord.Intents(guilds=True, members=True, bans=True, emojis=True, voice_states=True, messages=True,
                              reactions=True)

    dream_bot = DreamBot(intents, database, prefix, owner, disabled_cogs)
    dream_bot.run(token)


# Run the bot
if __name__ == '__main__':
    main()
