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

import asyncio
from os import getenv
from sys import version

import aiohttp
import discord
from dotenv import load_dotenv

from dreambot import DreamBot, Optionals, GitOptionals
from utils.database.migrations import Migrator
from utils.logging_formatter import format_loggers, bot_logger
from utils.utils import VERSION


async def main() -> None:
    """
    Driver method.
    """

    # logging setup
    format_loggers()

    bot_logger.info(f'Current DreamBot Version: {VERSION}')
    bot_logger.info(f'Current Python Version: {version}')
    bot_logger.info(f'Current Discord Version: {discord.__version__}')

    load_dotenv()

    # required
    token = getenv('DISCORD_TOKEN')
    database = getenv('DATABASE')
    prefix = getenv('PREFIX', '>')
    owner = int(getenv('OWNER_ID', '-1'))
    environment = getenv('ENVIRONMENT', 'DEV')

    assert database is not None
    assert token is not None

    # apply database migrations
    async with Migrator(database) as m:
        await m.apply_migrations()

    # optionals
    # disabled cogs
    try:
        disabled_cogs = getenv('DISABLED_COGS', '').split(',')
    except AttributeError:
        disabled_cogs = []

    # session headers
    if user_agent := getenv('USER_AGENT'):
        headers = {
            'User-Agent': user_agent
        }
    else:
        headers = None

    # git optionals
    git_options: GitOptionals = {
        'git_user': getenv('GITHUB_USER'),
        'git_repo': getenv('GITHUB_REPO'),
        'git_token': getenv('GITHUB_TOKEN')
    }

    # noinspection PyTypeChecker
    options: Optionals = {
        'status_type': discord.ActivityType(int(getenv('STATUS_TYPE', 1))),
        'status_text': getenv('STATUS_TEXT'),
        'firebase_project': getenv('FIREBASE_PROJECT'),
        'disabled_cogs': disabled_cogs,
        'git': git_options
    }

    async with (
        DreamBot(prefix, owner, environment, database, options=options) as bot,
        aiohttp.ClientSession(headers=headers) as session
    ):
        # mypy seems to lose context during multiple async with
        bot.session = session  # type: ignore[attr-defined]
        await bot.start(token)  # type: ignore[attr-defined]


# Run the bot
if __name__ == '__main__':
    asyncio.run(main())
