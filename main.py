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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s:%(name)s: %(message)s', datefmt='%I:%M %p on %A, %B %d, %Y')

    load_dotenv()

    # required
    token = getenv('DISCORD_TOKEN')
    owner = int(getenv('OWNER_ID'))
    prefix = getenv('PREFIX', '!')
    database = getenv('DATABASE')

    # optional
    options = {
        'status_type': discord.ActivityType(int(getenv('STATUS_TYPE', 1))),
        'status_text': getenv('STATUS_TEXT')
    }

    # explicitly disabled cogs
    try:
        options['disabled_cogs'] = getenv('DISABLED_COGS').split(',')
    except AttributeError:
        pass

    # git optionals
    git_options = {
        'git_user': getenv('GITHUB_USER'),
        'git_repo': getenv('GITHUB_REPO'),
        'git_token': getenv('GITHUB_TOKEN')
    }

    if all(git_options.values()):
        options['git'] = git_options

    # specify intents (members requires explicit opt-in via dev portal)
    intents = discord.Intents(guilds=True, members=True, bans=True, emojis=True, voice_states=True, messages=True,
                              reactions=True)

    dream_bot = DreamBot(intents, database, prefix, owner, options=options)
    dream_bot.run(token)


# Run the bot
if __name__ == '__main__':
    main()
