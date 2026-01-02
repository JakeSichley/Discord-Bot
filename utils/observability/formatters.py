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
from typing import Tuple, Set

gray = '\x1b[38;5;15m'
cyan = '\x1b[36m'
yellow = '\x1b[33;20m'
blue = '\x1b[34m'
green = '\x1b[32m'
red = '\x1b[31;20m'
reset = '\x1b[0m'


class ScopedDebugFilter(logging.Filter):
    """
    A filter that allows records if they don't have a scope, or if their scope is explicitly enabled.

    Attributes:
        enabled_scopes (Set[str]): A set of scope names to allow debug logs with.
    """

    def __init__(self) -> None:
        """
        The constructor for the ScopedDebugFilter class.

        Parameters:
            None.

        Returns:
            None.
        """

        super().__init__()
        self.enabled_scopes: Set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the specified record is to be logged.

        Parameters:
            record (logging.LogRecord): The logging record for an event.

        Returns:
            (bool): True if the specified record is to be logged.
        """

        # don't filter non-debug logs
        if record.levelno > logging.DEBUG:
            return True

        if scope := getattr(record, 'debug_scope', None):
            return scope in self.enabled_scopes

        return False


class StreamLoggingFormatter(logging.Formatter):
    """
    A logging.Formatter with custom formatting and coloring based on logging level.
    Handles logging events to the standard stream.

    Attributes:
        basic_format (str): A less-descriptive log format for info related events.
        detailed_format (str): A more-descriptive log format for warnings and errors.
        formats (Dict[int, str]): A dictionary of logging levels and their corresponding formats.

    Attributes:
        None.
    """

    def __init__(self, basic_format: str, detailed_format: str, colors: Tuple[str, str, str, str, str]) -> None:
        """
        The constructor for the Formatter class.

        Parameters:
            basic_format (str): A less-descriptive log format for info related events.
            detailed_format (str): A more-descriptive log format for warnings and errors.
            colors (Tuple[str, str, str, str, str]): The colors to apply to each level.

        Returns:
            None.
        """

        super().__init__(datefmt='%I:%M %p on %A, %B %d, %Y')

        self.basic_format = basic_format
        self.detailed_format = detailed_format
        self.formats = {
            logging.DEBUG: colors[0] + basic_format + reset,
            logging.INFO: colors[1] + basic_format + reset,
            logging.WARNING: colors[2] + detailed_format + reset,
            logging.ERROR: colors[3] + detailed_format + reset,
            logging.CRITICAL: colors[4] + detailed_format + reset
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Returns a formatted logging record.

        Parameters:
            record (logging.LogRecord): The logging record for an event.

        Returns:
            (str): The formatted record.
        """

        log_format = self.formats.get(record.levelno, self.basic_format)
        formatter = logging.Formatter(log_format, datefmt=self.datefmt)
        formatted = formatter.format(record)

        # remove traceback stack from discord.Client reconnect errors
        return formatted.splitlines()[0] if record.name == 'discord.client' else formatted


class FileLoggingFormatter(logging.Formatter):
    """
    A logging.Formatter with custom formatting based on logging level.
    Handles logging events to a file.

    Attributes:
        basic_format (str): A less-descriptive log format for info related events.
        detailed_format (str): A more-descriptive log format for warnings and errors.
        formats (Dict[int, str]): A dictionary of logging levels and their corresponding formats.
    """

    def __init__(self, basic_format: str, detailed_format: str) -> None:
        """
        The constructor for the Formatter class.

        Parameters:
            basic_format (str): A less-descriptive log format for info related events.
            detailed_format (str): A more-descriptive log format for warnings and errors.

        Returns:
            None.
        """

        super().__init__(datefmt='%I:%M %p on %A, %B %d, %Y')

        self.basic_format = basic_format
        self.detailed_format = detailed_format
        self.formats = {
            logging.DEBUG: basic_format,
            logging.INFO: basic_format,
            logging.WARNING: detailed_format,
            logging.ERROR: detailed_format,
            logging.CRITICAL: detailed_format,
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Returns a formatted logging record.

        Parameters:
            record (logging.LogRecord): The logging record for an event.

        Returns:
            (str): The formatted record.
        """

        log_format = self.formats.get(record.levelno, self.basic_format)

        # inject context dump
        if hasattr(record, 'context'):
            log_format += '\n%(context)s'

        formatter = logging.Formatter(log_format, datefmt=self.datefmt)
        return formatter.format(record)


class NoResumeFilter(logging.Filter):
    """
    A logging.Filter that removes "RESUMED" events from discord.py logger.

    Attributes:
        None.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the specified record is to be logged.

        Parameters:
            record (logging.LogRecord): The logging record for an event.

        Returns:
            (bool): True if the specified record is to be logged.
        """

        return 'RESUMED' not in record.getMessage()
