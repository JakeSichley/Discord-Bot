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

from datetime import datetime, timedelta
from typing import Any, TypedDict, Optional

import aiohttp

from utils.network.return_type import NetworkReturnType
from utils.observability.loggers import bot_logger

Headers = TypedDict(
    'Headers',
    {
        'Authorization': str,
        'Content-Type': str,
        'User-Agent': str,
        'From': str
    },
    total=False
)


async def network_request(
        session: aiohttp.ClientSession,
        url: str,
        /,
        *,
        encoding: str = 'utf-8',
        headers: Optional[Headers] = None,
        raise_errors: Optional[bool] = True,
        ssl: Optional[bool] = None,
        return_type: NetworkReturnType = NetworkReturnType.TEXT
) -> Any:
    """
    A method that downloads an image from an url.

    Parameters:
        session (aiohttp.ClientSession): The bot's current client session.
        url (str): The url of the request.
        encoding (str): The type of encoding to parse the response with, if applicable.
        headers (Optional[Headers]): Any additional headers to attach to the request.
        raise_errors (Optional[bool]): Whether responses with statuses >= 400 should raise an exception.
        ssl (Optional[bool]): Whether ssl should be used for the request.
        return_type (NetworkReturnType): The type of data to coerce the response to.

    Raises:
        aiohttp.ClientResponseError

    Returns:
        (Optional[Union[str, bytes, Dict[Any, Optional[Any]]]]) The request's response.
    """

    try:
        async with session.get(url, headers=headers, ssl=ssl, raise_for_status=raise_errors) as r:
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
    except aiohttp.ClientError as e:
        bot_logger.warning(f'Network Request Client Error. ("{url}"). {type(e)} - {e} - {e.args}')
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

        return min(2 ** (5 + self._count // 2), self._max_backoff_time)  # type: ignore[no-any-return]

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
