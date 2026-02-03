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

import re
from typing import Optional
from datetime import datetime, timedelta


class ExponentialBackoff:
    """
    An Exponential Backoff implementation for network requests.

    Attributes:
        _max_backoff_time (int): The maximum amount of time to backoff for, in seconds.
        _count (int): The current number of consecutive backoffs.
        _start_time (Optional[datetime]): The time the current backoff started.
    """

    __slots__ = ('_count', '_max_backoff_time', '_start_time')

    def __init__(self, max_backoff_time: int) -> None:
        """
        The constructor for the Exponential Backoff class.

        Parameters:
            max_backoff_time (int): The maximum amount of time to backoff for, in seconds.

        Returns:
            None.
        """

        self._max_backoff_time: int = max_backoff_time
        self._count: int = 0
        self._start_time: Optional[datetime] = None

    def record_failure(self) -> None:
        """
        Records a failure, incrementing the Exponential Backoff and resetting the offset start time.

        Warnings:
            The caller is responsible for checking whether a backoff currently exists.

        Parameters:
            None.

        Returns:
            None.
        """

        self._start_time = datetime.now()
        self._count += 1

    def reset(self) -> None:
        """
        Resets the Exponential Backoff.

        Parameters:
            None.

        Returns:
            None.
        """

        self._start_time = None
        self._count = 0

    @property
    def total_backoff_seconds(self) -> int:
        """
        Computes the total number of seconds this backoff lasts for.

        Parameters:
            None.

        Returns:
            (int): The total amount of time this backoff lasts for.
        """

        return min(int(2 ** (5 + self._count // 2)), self._max_backoff_time)

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

        if self._start_time is None:
            return datetime.now()

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

        if self.end_time <= datetime.now():
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
            'Seconds': self.total_backoff_seconds % 60,
        }

        return ', '.join([f'{time} {label}' for label, time in times.items() if time > 0])

    @property
    def remaining_str_time(self) -> str:
        """
        Generates a string representation of the total remaining backoff.

        Parameters:
            None.

        Returns:
            (str) The generated string.
        """

        remaining_backoff = self.remaining_backoff

        if remaining_backoff <= 0:
            return 'None'

        times = {
            'Hours': remaining_backoff // 3600,
            'Minutes': remaining_backoff % 3600 // 60,
            'Seconds': remaining_backoff % 60,
        }

        formatted = ', '.join([f'{time} {label}' for label, time in times.items() if time > 0])

        return formatted if formatted else 'None'


class BackoffRule:
    """
    A class that combines a url pattern and an ExponentialBackoff to create a usable rule.

    Attributes:
        pattern (str): A regular expression pattern to use to match urls against.
        backoff (BackoffRule): The ExponentialBackoff associated with this rule.
    """

    __slots__ = ('backoff', 'pattern')

    def __init__(self, pattern: str, max_backoff_time: int) -> None:
        """
        The constructor for the ExponentialBackoffException class.

        Parameters:
            pattern (str): A regular expression pattern to use to match urls against.
            max_backoff_time (int): The maximum amount of time to backoff for, in seconds.

        Returns:
            None.
        """

        self.pattern: re.Pattern[str] = re.compile(pattern)
        self.backoff: ExponentialBackoff = ExponentialBackoff(max_backoff_time)

    @classmethod
    def from_url(cls, url: str, max_backoff_time: int) -> 'BackoffRule':
        """
        Class method to help with the construction of BackoffRules from raw URLs.

        Parameters:
            url (str): A raw URL that will be escaped to create a backoff rule.
            max_backoff_time (int): The maximum amount of time to backoff for, in seconds.

        Returns:
            (BackoffRule).
        """

        return cls(re.escape(url), max_backoff_time)

    def matches_url(self, url: str) -> bool:
        """
        Helper method to check if the given url matches the pattern.

        Parameters:
            url (str): The url to check against.

        Returns:
            (bool): Whether the url matches the pattern.
        """

        return re.search(self.pattern, url) is not None


class ExponentialBackoffError(Exception):
    """
    An exception raised when a network call is made for a url with an active exponential backoff.

    Attributes:
        url (str): The url that triggered the backoff.
        backoff_rule (BackoffRule): The backoff rule responsible for the exception.
    """

    def __init__(self, url: str, backoff_rule: BackoffRule) -> None:
        """
        The constructor for the ExponentialBackoffException class.

        Parameters:
            url (str): The url that triggered the backoff.
            backoff_rule (BackoffRule): The backoff rule responsible for the exception.

        Returns:
            None.
        """

        self.url: str = url
        self.backoff_rule: BackoffRule = backoff_rule
        super().__init__(
            f'`{url}` (matching pattern `{backoff_rule.pattern.pattern}`) was used in a new network request while on '
            f'cooldown. Backoff count: {backoff_rule.backoff.backoff_count}. '
            f'Remaining backoff time: {backoff_rule.backoff.remaining_str_time}'
        )
