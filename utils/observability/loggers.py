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

import datetime
import logging
import os
from contextlib import suppress
from typing import Dict

import discord

from utils.observability.formatters import (
    StreamLoggingFormatter, FileLoggingFormatter, NoResumeFilter, ScopedDebugFilter as ScopedDebugFilter,
    gray, cyan, yellow, blue, red
)

bot_logger: logging.Logger = logging.getLogger('DreamBot')
debug_filter: ScopedDebugFilter = ScopedDebugFilter()


def make_debug_scope(scope: str) -> Dict[str, str]:
    """
    Make a standardized debug scope for use in `ScopedDebugFilter`.

    Parameters:
        scope (str): The scope to use.

    Returns:
        (Dict[str, str]): The parameterized scope, suitable for use as argument to logging functions (extra=scope).
    """

    return {'debug_scope': scope}


def setup_loggers() -> None:
    """
    Formats loggers for discord.py and DreamBot.

    Parameters:
        None.

    Returns:
        None.
    """

    file_path = os.path.join(os.getcwd(), 'logs')
    file_time_name = f"{str(datetime.datetime.today()).replace(':', '-').replace(' ', '-')}.txt"

    with suppress(FileExistsError):
        os.mkdir(file_path)

    # set up bot handlers
    logger = logging.getLogger('DreamBot')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.addFilter(debug_filter)
    handler.setFormatter(
        StreamLoggingFormatter(
            '%(asctime)s: %(levelname)s [DreamBot] - %(message)s (%(filename)s)',
            '%(asctime)s: %(levelname)s [DreamBot] - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)',
            (gray, cyan, yellow, red, red)
        )
    )
    logger.addHandler(handler)

    bot_file_handler = logging.FileHandler(os.path.join(file_path, file_time_name))
    bot_file_handler.setLevel(logging.DEBUG)
    handler.addFilter(debug_filter)
    bot_file_handler.setFormatter(
        FileLoggingFormatter(
            '%(asctime)s: %(levelname)s [DreamBot] - %(message)s (%(filename)s)',
            '%(asctime)s: %(levelname)s [DreamBot] - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'
        )
    )
    logger.addHandler(bot_file_handler)

    # set up discord handlers
    discord_handler = logging.StreamHandler()
    discord_handler.setLevel(logging.INFO)
    discord_handler.addFilter(NoResumeFilter())
    discord.utils.setup_logging(
        formatter=StreamLoggingFormatter(
            '%(asctime)s: %(levelname)s [discord.py] - %(message)s (%(filename)s)',
            '%(asctime)s: %(levelname)s [discord.py] - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)',
            (gray, blue, yellow, red, red)
        ),
        handler=discord_handler,
        root=False
    )
    discord_logger = logging.getLogger('discord')

    discord_file_handler = logging.FileHandler(os.path.join(file_path, file_time_name))
    discord_file_handler.setLevel(logging.INFO)
    discord_file_handler.setFormatter(
        FileLoggingFormatter(
            '%(asctime)s: %(levelname)s [discord.py] - %(message)s (%(filename)s)',
            '%(asctime)s: %(levelname)s [discord.py] - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'
        )
    )

    discord_logger.addHandler(discord_file_handler)
