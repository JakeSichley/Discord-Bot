"""
MIT License

Copyright (c) 2021 Jake Sichley

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
import discord
import datetime
import pytz
import functools
import asyncio


async def cleanup(messages: List[discord.Message], channel: discord.TextChannel) -> None:
    """
    Cleans up all prompt messages sent by the bot a command's setup.
    Attempts to bulk delete messages if permissions allow; otherwise messages are deleted individually.

    Parameters:
        messages (list[discord.Message]): The list of messages to delete.
        channel (discord.TextChannel): The channel to delete the messages from.

    Returns:
        None.
    """

    try:
        await channel.delete_messages(messages)
    except discord.Forbidden:
        while messages:
            await messages.pop().delete()
    except discord.DiscordException:
        pass


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
