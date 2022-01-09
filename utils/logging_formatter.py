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

import logging


class BotLoggingFormatter(logging.Formatter):
    """
    A logging.Formatter with custom formatting and coloring based on logging level.

    Constants:
        blue (str): ansi color code for blue.
        yellow (str): ansi color code for yellow.
        red (str): ansi color code for red.
        reset (str): ansi color code to reset all colors and effects.
        basic_format (str): A less-descriptive log format for info related events.
        detailed_format (str): A more-descriptive log format for warnings and errors.
        formats (Dict[int, str]): A dictionary of logging levels and their corresponding formats.

    Attributes:
        None.
    """

    blue = '\x1b[36m'
    yellow = '\x1b[33;20m'
    red = '\x1b[31;20m'
    reset = '\x1b[0m'

    basic_format = '%(asctime)s: %(levelname)s - %(message)s (%(filename)s)'
    detailed_format = '%(asctime)s: %(levelname)s - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)'

    formats = {
        logging.DEBUG: blue + basic_format + reset,
        logging.INFO: blue + basic_format + reset,
        logging.WARNING: yellow + detailed_format + reset,
        logging.ERROR: red + detailed_format + reset,
        logging.CRITICAL: red + detailed_format + reset
    }

    def __init__(self) -> None:
        """
        The constructor for the Formatter class.

        Parameters:
            None.

        Returns:
            None.
        """

        super().__init__(datefmt='%I:%M %p on %A, %B %d, %Y')

    def format(self, record: logging.LogRecord) -> str:
        """
        Returns a formatted logging record.

        Parameters:
            record (logging.LogRecord): The logging record for an event.

        Returns:
            (str): The formatted record.
        """

        log_format = self.formats.get(record.levelno, logging.DEBUG)
        formatter = logging.Formatter(log_format, datefmt=self.datefmt)
        return formatter.format(record)
