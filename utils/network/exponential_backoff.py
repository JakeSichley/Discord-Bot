from datetime import datetime, timedelta
import re


class ExponentialBackoff:
    """
    An Exponential Backoff implementation for network requests.

    Attributes:
        _max_backoff_time (int): The maximum amount of time to backoff for, in seconds.
        _count (int): The current number of consecutive backoffs.
        _start_time (datetime): The time the current backoff started.
    """

    __slots__ = ('_max_backoff_time', '_count', '_start_time')

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

    def record_failure(self) -> None:
        """

        Returns:

        """

        # TODO: this can probably be cleaned up to improve readability (maybe a start func or something)

        # if we're currently in a backoff period, do nothing
        if datetime.now() < self.end_time and self._count > 0:
            return

        # if we're not in a backoff period, reset before backing off (if applicable)
        if self.remaining_backoff <= 0:
            self.reset()

        # if this is our first backoff, set our start time
        if self._count == 0:
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


class BackoffRule:
    """
    pass
    """

    __slots__ = ('pattern', 'backoff')

    def __init__(self, pattern: str, max_backoff_time: int) -> None:
        self.pattern: re.Pattern[str] = re.compile(pattern)
        self.backoff: ExponentialBackoff = ExponentialBackoff(max_backoff_time)

    def matches_url(self, url: str) -> bool:
        return re.search(self.pattern, url) is not None

