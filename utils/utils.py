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
import functools
import subprocess
from datetime import datetime
from re import search
from typing import List, Sequence, Any, Iterator, Tuple, Callable, Awaitable, Optional, Literal

import discord
import pytz
from discord.utils import format_dt

from utils.logging_formatter import bot_logger

VERSION = '2.8.1'


async def cleanup(messages: List[discord.Message], channel: discord.abc.Messageable) -> None:
    """
    Cleans up all prompt messages sent by the bot a command's setup.
    Attempts to bulk delete messages if permissions allow; otherwise messages are deleted individually.

    Parameters:
        messages (List[discord.Message]): The list of messages to delete.
        channel (discord.TextChannel): The channel to delete the messages from.

    Returns:
        None.
    """

    if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):  # attr: delete_messages
        return

    try:
        await channel.delete_messages(messages)
    except discord.Forbidden as e:
        bot_logger.warning(f'Message Cleanup Error. {e.status}. {e.text}')
        while messages:
            await messages.pop().delete()
    except discord.HTTPException as e:
        bot_logger.error(f'Message Cleanup Error. {e.status}. {e.text}')


def pairs(sequence: Sequence[Any]) -> Iterator[Tuple[Any, Any]]:
    """
    Generator that yields pairs of items in a sequence

    Parameters:
        sequence (Sequence[Any]): A sequence of items.

    Returns:
        None.

    Yields:
        (Iterator[(Any, Any)]): The next pair of items from the sequence.
    """

    i = iter(sequence)
    for item in i:
        yield item, next(i)


def readable_flags(flags: discord.PublicUserFlags) -> str:
    """
    A method that converts PublicUserFlag enums to usable strings.

    Parameters:
        flags (PublicUserFlags): The public user flags for a given user.

    Returns:
        (str): An embed-ready string detailing the user's flags.
    """

    flag_strings = [' '.join(x.capitalize() for x in flag[0].split('_')) for flag in flags if flag[1]]

    if flag_strings:
        return ', '.join(flag_strings)
    else:
        return 'None'


def run_in_executor(func: Callable) -> Callable:
    """
    A decorator that runs a blocking method in an executor.

    Parameters:
        func (Callable): The blocking method.

    Returns:
        (Callable): The wrapped method.
    """

    @functools.wraps(func)
    def inner(*args: Any, **kwargs: Any) -> Awaitable:
        """
        A decorator that runs a blocking method in an executor.

        Parameters:
            args (Any): The args that should be passed to the inner function.
            kwargs (Any): The kwargs that should be passed to the inner function.

        Returns:
            (Any): The result of the wrapped method.
        """

        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    return inner


async def run_in_subprocess(command: str) -> Tuple[bytes, bytes]:
    """
    A method that runs the specified command in a subprocess shell and returns the communicated result.

    Parameters:
        command (str): The command that should be run the subprocess shell.

    Returns:
        (Tuple[bytes, bytes]): The result of the command.
    """

    try:
        process_shell = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await process_shell.communicate()
    except NotImplementedError:
        process_program = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await asyncio.get_running_loop().run_in_executor(None, process_program.communicate)


async def generate_activity(status_text: str, status_type: discord.ActivityType) -> discord.Activity:
    """
    Generates a custom activity. Attempts to add the latest git version information to the status text.

    Parameters:
        status_text (str): The default/base activity text.
        status_type (discord.ActivityType): The type of activity.

    Returns:
        (discord.Activity): The custom generated activity.
    """

    result = await run_in_subprocess('git show')

    try:
        git_status = result[0].decode()
        # type ignores are handled by except AttributeError
        git_commit = search(r'(?<=commit )([A-z0-9]{7})', git_status).group()  # type: ignore
        git_description = search(r'(?<=JakeSichley/)([A-z0-9-.]+)', git_status).group()  # type: ignore
    except AttributeError:
        return discord.Activity(name=status_text, type=status_type)
    else:
        git_text = f'Version {VERSION} ({git_commit}) - {git_description}'
        padding = "\u3000" * (126 - len(status_text) - len(git_text))
        return discord.Activity(name=f'{status_text}\n{padding}{git_text}', type=status_type)


def valid_content(content: str, *, max_length: int = 2000) -> bool:
    """
    Checks whether a piece of content is send-able via `send`.

    Parameters:
        content (str): The proposed content.
        max_length (int): The maximum length of the content.

    Returns:
        (bool): Whether the content is valid.
    """

    return content is not None and len(content) <= max_length


def format_unix_dt(timestamp: int, style: Optional[Literal['f', 'F', 'd', 'D', 't', 'T', 'R']] = None) -> str:
    """
    Helper method to convert a unix timestamp to a datetime object for further formatting.

    Parameters:
        timestamp (int): The unix timestamp.
        style (Optional[str]): The style to format the datetime with.

    Returns:
        (str): The formatted timestamp.
    """

    dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    return format_dt(dt, style)
