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

from os import getenv
from sys import version
from dotenv import load_dotenv
from dreambot import DreamBot
from utils.logging_formatter import format_loggers, bot_logger
import discord
import asyncio
import aiosqlite
import aiohttp


async def main() -> None:
    """
    Driver method.
    """

    # logging setup
    format_loggers()

    bot_logger.info(f'Current Python Version: {version}')
    bot_logger.info(f'Current Discord Version: {discord.__version__}')

    load_dotenv()

    # required
    token = getenv('DISCORD_TOKEN')
    owner = int(getenv('OWNER_ID'))
    prefix = getenv('PREFIX', '>')
    database = getenv('DATABASE')
    environment = getenv('ENVIRONMENT', 'DEV')

    # optional
    # noinspection PyTypeChecker
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

    async with (
        DreamBot(prefix, owner, environment, options=options) as bot,
        aiosqlite.connect(database) as connection,
        aiohttp.ClientSession() as session
    ):
        bot.connection = connection
        bot.session = session
        await bot.start(token)


# Run the bot
if __name__ == '__main__':
    asyncio.run(main())
