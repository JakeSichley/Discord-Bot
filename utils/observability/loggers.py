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

import logging
from typing import Callable, Any

bot_logger: logging.Logger = logging.getLogger('DreamBot')


class OptionalLogger:
    """
    A logger that allows for runtime enabling or disabling of a logging section.

    Attributes:
        _logger (logging.Logger): The primary (enabled) logger to use.
        _null_logger (logging.Logger): The null (disabled) logger to use.
        _enabled (bool): Whether to _actually_ log messages.
    """

    class NullLogger(logging.Logger):
        """
        Provides a logging.Logger interface while sending any and all logs to the void.
        """

        def __init__(self) -> None:
            """
            The constructor for the NullLogger class.

            Parameters:
                None.
            """

            super().__init__('NullLogger')

        def __getattribute__(self, name: str) -> Callable[[Any, Any], None]:
            """
            The constructor for the NullLogger class.

            Parameters:
                name (str): The name of the attribute to access.

            Returns:
                (Callable[[Any, Any], None]): A lambda closure that accepts any arguments and returns None.
            """

            return lambda *args, **kwargs: None

    __slots__ = ('_logger', '_null_logger', '_enabled')

    def __init__(self, enabled: bool) -> None:
        """
        The constructor for the OptionalLogger class.

        Parameters:
            enabled (bool) Whether the primary logger is enabled.
        """

        self._logger: logging.Logger = bot_logger
        self._null_logger: logging.Logger = self.NullLogger()
        self._enabled: bool = enabled

    def __call__(self) -> logging.Logger:
        """
        Allows `OptionalLogger` to be called like a function, returning the underlying logger for more fluent chaining.

        Parameters:
            None.

        Returns:
            (logging.Logger): The primary or null logger, depending on whether the primary logger is enabled.
        """

        return self._logger if self._enabled else self._null_logger

    @property
    def enabled(self) -> bool:
        """
        Getter for the underlying `_enabled` attribute.

        Parameters:
            None.

        Returns:
            (bool): Whether the primary logger is enabled.
        """

        return self._enabled

    @enabled.setter
    def enabled(self, is_enabled: bool) -> None:
        """
        Setter for the underlying `_enabled` attribute.

        Parameters:
            is_enabled (bool): Whether to enable or disable the primary logger.

        Returns:
            None.
        """

        self._enabled = is_enabled
