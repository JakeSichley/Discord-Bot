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

import asyncio
import functools
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from re import search
from typing import (
    List, Sequence, Any, Iterator, Tuple, Callable, Awaitable, Optional, Literal, TypeVar, Union, Generic, Iterable
)

import discord
import pytz
from discord.app_commands import Choice
from discord.utils import format_dt
from fuzzywuzzy import fuzz  # type: ignore

from utils.logging_formatter import bot_logger

VERSION = '2.18.0'

ChoiceT = TypeVar('ChoiceT', str, int, float, Union[str, int, float])
T = TypeVar('T')


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


def run_in_executor(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """
    A decorator that runs a blocking method in an executor.

    Parameters:
        func (Callable): The blocking method.

    Returns:
        (Callable): The wrapped method.
    """

    @functools.wraps(func)
    def inner(*args: Any, **kwargs: Any) -> Awaitable[Any]:
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


@dataclass
class AutocompleteModel(Generic[ChoiceT]):
    """
    A Dataclass that encapsulates `app_commands.Choice` and a fuzzy search ratio.

    Attributes:
        name (str): The name of the choice.
        value (ChoiceT): The value of the choice.
        current (str): The current input.
        ratio (int): The similarity ratio between this model's name and the current input.
    """

    current: str
    name: str
    value: ChoiceT
    ratio: int = field(init=False)

    def __post_init__(self) -> None:
        """
        Calculates the similarity ratio after initialization.

        Parameters:
            None.

        Returns:
            None.
        """

        name = self.name.casefold()
        current = self.current.casefold()

        partial_ratio = fuzz.partial_ratio(name, current)
        set_ratio = fuzz.token_set_ratio(name, current)

        self.ratio = partial_ratio + set_ratio

    def to_choice(self) -> Choice[ChoiceT]:
        """
        Returns this model as an `app_commands.Choice` model.

        Parameters:
            None.

        Returns:
            (Choice): The `app_commands.Choice` model.
        """

        return Choice(name=self.name, value=self.value)

    def __lt__(self, other: 'AutocompleteModel[ChoiceT]') -> bool:
        """
        Returns whether this model is less-than (<) another model.

        Parameters:
            other (AutocompleteModel): The other model.

        Returns:
            (bool): self < other.
        """

        return self.ratio < other.ratio

    def __le__(self, other: 'AutocompleteModel[ChoiceT]') -> bool:
        """
        Returns whether this model is less-than-or-equal-to (<=) another model.

        Parameters:
            other (AutocompleteModel): The other model.

        Returns:
            (bool): self <= other.
        """

        return self.ratio <= other.ratio


def generate_autocomplete_choices(
        current: str,
        items: Iterable[Tuple[str, ChoiceT]],
        *,
        limit: int = 25,
        minimum_threshold: int = 0
) -> List[Choice[ChoiceT]]:
    """
    Generator that yields pairs of items in a sequence

    Parameters:
        current (str): The current autocomplete input.
        items (Iterable[T]): An iterable of objects to convert to AutocompleteModels.
        limit (int): The maximum number of Choices to return.
        minimum_threshold (int): The minimum ratio for a Choice to be valid.

    Returns:
        (List[Choice]): A list of converted and sorted Choices.
    """

    limit = max(1, min(25, limit))  # clamp to [1, 25]
    minimum_threshold = max(0, min(200, minimum_threshold))  # clamp to [0, 200]

    autocomplete_models = [AutocompleteModel(current, *x) for x in items]
    valid_models = [x for x in autocomplete_models if x.ratio >= minimum_threshold]
    ratios = sorted(valid_models, reverse=True)

    return [x.to_choice() for x in ratios[:limit]]


def calculate_padding(objects: List[T], attribute: str) -> int:
    """
    Given a list of objects and an attribute, calculates the longest instance of the attribute.

    Parameters:
        objects (List[T]): The list of objects.
        attribute (str): The name of the attribute to assess.

    Returns:
        (int).
    """

    return max(len(x.__getattribute__(attribute)) for x in objects)
