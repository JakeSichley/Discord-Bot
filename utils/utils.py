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

from typing import List, Sequence, Any, Iterator, Tuple, Callable, Awaitable
from re import search
from utils.logging_formatter import bot_logger
import discord
import datetime
import pytz
import functools
import asyncio
import subprocess

VERSION = '2.1.0'


async def cleanup(messages: List[discord.Message], channel: discord.TextChannel) -> None:
    """
    Cleans up all prompt messages sent by the bot a command's setup.
    Attempts to bulk delete messages if permissions allow; otherwise messages are deleted individually.

    Parameters:
        messages (List[discord.Message]): The list of messages to delete.
        channel (discord.TextChannel): The channel to delete the messages from.

    Returns:
        None.
    """

    try:
        await channel.delete_messages(messages)
    except discord.Forbidden as e:
        bot_logger.warning(f'Message Cleanup Error. {e.status}. {e.text}')
        while messages:
            await messages.pop().delete()
    except discord.HTTPException as e:
        bot_logger.error(f'Message Cleanup Error. {e.status}. {e.text}')


def localize_time(time: datetime.datetime) -> str:
    """
    Localizes datetime objects to Pacific time and converts the format to a readable string.

    Parameters:
        time (datetime.datetime): The datetime object to localize.

    Returns:
        (str): The readable and localized date and time.
    """

    pacific = datetime.datetime.now(pytz.timezone('US/Pacific'))
    offset_time = time + datetime.timedelta(seconds=pacific.utcoffset().total_seconds())
    return offset_time.strftime('%I:%M %p on %A, %B %d, %Y')


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
        process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await process.communicate()
    except NotImplementedError:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await asyncio.get_running_loop().run_in_executor(None, process.communicate)


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
        git_commit = search(r'(?<=commit )([A-z0-9]{7})', git_status).group()
        git_description = search(r'(?<=JakeSichley/)([A-z0-9-]+)', git_status).group()
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

    return content and len(content) <= max_length
