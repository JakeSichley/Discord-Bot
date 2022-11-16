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

from typing import Any
from enum import Enum
from utils.logging_formatter import bot_logger
from datetime import datetime, timedelta
import aiohttp


class NetworkReturnType(Enum):
    """
    An Enum class that represents how a network request's response should be returned.
    """

    TEXT = 1  # str
    JSON = 2  # Union[Dict[Any, Optional[Any]]]
    BYTES = 3  # bytes


async def network_request(session: aiohttp.ClientSession, url: str, **options) -> Any:
    """
    A method that downloads an image from an url.

    Parameters:
        session (aiohttp.ClientSession): The bot's current client session.
        url (str): The url of the request.
        options (**kwargs): Optional, keyword only arguments.
            SUPPORTED:
                'return_type' (NetworkReturnType)
                'header' (Dict)
                'encoding' (str)
                'raise_errors' (bool)
                'ssl' (bool)

    Raises:
        aiohttp.ClientResponseError

    Returns:
        (Optional[Union[str, bytes, Dict[Any, Optional[Any]]]]) The request's response.
    """

    return_type = NetworkReturnType(options.pop('return_type', 1))
    header = options.pop('header', None)
    encoding = options.pop('encoding', 'utf-8')
    raise_errors = options.pop('raise_errors', True)
    ssl = options.pop('ssl', None)

    try:
        async with session.get(url, headers=header, ssl=ssl, raise_for_status=raise_errors) as r:
            if return_type == NetworkReturnType.JSON:
                return await r.json(encoding=encoding)
            elif return_type == NetworkReturnType.BYTES:
                return await r.read()
            else:
                return await r.text(encoding=encoding)
    except aiohttp.ClientResponseError as e:
        bot_logger.warning(f'Network Request Error. ("{url}"). {e.status}. {e.message}')
        if raise_errors:
            raise


class ExponentialBackoff:
    """
    An Exponential Backoff implementation for network requests.

    Attributes:
        _max_backoff_time (int): The maximum amount of time to backoff for, in seconds.
        _count (int): The current number of consecutive backoffs.
        _start_time (datetime): The time the current backoff started.
    """

    def __init__(self, max_backoff_time: int) -> None:
        """
        The constructor for the Exponential Backoff class.

        Parameters:
            max_backoff_time (int): The maximum amount of time to backoff for, in seconds.

        Returns:
            None.
        """

        self._max_backoff_time = max_backoff_time
        self._count = 0
        self._start_time = datetime.now()

    def next_backoff(self) -> None:
        """
        Prepares the next (if applicable) backoff.

        Parameters:
            None.

        Returns:
            None.
        """

        if self._count == 0 or datetime.now() >= self.end_time:
            self._count += 1
            self._start_time = datetime.now()

    def reset(self) -> None:
        """
        Resets the Exponential Backoff.

        Parameters:
            None.

        Returns:
            None.
        """

        self._count = 0

    @property
    def total_backoff_seconds(self) -> int:
        """
        Computes the total amount of seconds this backoff lasts for.

        Parameters:
            None.

        Returns:
            (int): The total amount of time this backoff lasts for.
        """

        return min(2 ** (5 + self._count // 2), self._max_backoff_time)

    @property
    def backoff_count(self) -> int:
        """
        Returns the current backoff count.

        Parameters:
            None.

        Returns:
            (int): The current backoff count.
        """

        return self._count

    @property
    def end_time(self) -> datetime:
        """
        Computes the time the current backoff ends at.

        Parameters:
            None.

        Returns:
            (datetime): The time the current backoff ends at.
        """

        return self._start_time + timedelta(seconds=self.total_backoff_seconds)

    @property
    def remaining_backoff(self) -> int:
        """
        Computes the remaining time, in seconds, for the current backoff.

        Parameters:
            None.

        Returns:
            (int): The time remaining for the current backoff.
        """

        if self.end_time >= datetime.now():
            return 0

        return int((self.end_time - datetime.now()).total_seconds())

    @property
    def str_time(self) -> str:
        """
        Generates a string representation of the total current backoff.

        Parameters:
            None.

        Returns:
            (str) The generated string.
        """

        times = {
            'Hours': self.total_backoff_seconds // 3600,
            'Minutes': self.total_backoff_seconds % 3600 // 60,
            'Seconds': self.total_backoff_seconds % 60
        }

        return ', '.join([f'{time} {label}' for label, time in times.items() if time > 0])
