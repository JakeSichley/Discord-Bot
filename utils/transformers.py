"""
MIT License

Copyright (c) 2019-2023 Jake Sichley

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
from datetime import datetime
from math import ceil
from typing import Optional, Union, Any

import discord
import parsedatetime  # type: ignore[import]
from discord import app_commands, Interaction
from pytz import utc


# noinspection PyAbstractClass
class SentinelTransformer(app_commands.Transformer):
    """
    Allows users to enter a sentinel value in addition to acceptable value range.
    """

    def __init__(self, *, sentinel_value: Optional[Union[str, int, float]] = None) -> None:
        """
        The constructor for the SentinelTransformer class.

        Parameters:
            sentinel_value (Optional[Union[str, int, float]]): The value of the sentinel.
        """

        self.sentinel_value = sentinel_value

    async def transform(self, interaction: Interaction, value: Any, /) -> Any:
        """
        Transforms the converted option value into another value.

        Parameters:
            interaction (discord.Interaction): The invocation interaction.
            value (Any): The input value.

        Returns:
            (Any): The transformed value.
        """

        raise NotImplementedError


# noinspection PyAbstractClass
class RunescapeNumberTransformer(SentinelTransformer):
    """
    Allows users to enter numbers in Runescape shorthand, if desired.

    Examples:
        100 -> 100
        100k -> 100_000
        100m -> 100_000_000
    """

    async def transform(self, interaction: discord.Interaction, value: str, /) -> int:
        """
        Attempts to transform the input to the desired type.

        Parameters:
            interaction (discord.Interaction): The invocation interaction.
            value (str): The input value.

        Returns:
            (int): The transformed number.
        """

        try:
            # input is a regular number
            parsed = int(value)
        except ValueError:
            # input is a number with 'k' or 'm' as the suffix
            if re.search(r'^\d+[km]?$', value.lower()):
                multiplier = 1_000 if value.lower()[-1] == 'k' else 1_000_000

                try:
                    parsed = int(value[:-1]) * multiplier
                except ValueError:
                    raise app_commands.TransformerError(value, self.type, self)
            else:
                raise app_commands.TransformerError(value, self.type, self)

        if self.sentinel_value is not None and parsed == self.sentinel_value:
            return parsed

        return max(1, min(2_147_483_647, parsed))  # clamp

    @property
    def _error_display_name(self) -> str:
        """
        The name to display during errors.

        Parameters:
            None.

        Returns:
            (str): The error display name.
        """

        return 'Integer from Runescape Number (10, 10k, 10m, etc.)'


# noinspection PyAbstractClass
class HumanDatetimeDuration(SentinelTransformer):
    """
    Allows users to a human-readable datetime duration. Converts the duration to total seconds.

    Examples:
        5m, 5 min, 5 minutes -> 300 seconds
        1d, 1 day -> 86,400 seconds
        1 hour 1 day 5 minutes 3 seconds -> 90,303 seconds
    """

    def __init__(
            self,
            minimum_seconds: Optional[int] = None,
            maximum_seconds: Optional[int] = None,
            *,
            sentinel_value: Optional[Union[str, int, float]] = None
    ) -> None:
        """
        The constructor for the HumanDatetimeDuration class.

        Parameters:
            minimum_seconds (Optional[int]): The minimum duration in seconds, if any.
            maximum_seconds (Optional[int]): The maximum duration in seconds, if any.
            sentinel_value (Optional[Union[str, int, float]]): The value of the sentinel.
        """

        super().__init__(sentinel_value=sentinel_value)

        self.minimum_seconds = minimum_seconds
        self.maximum_seconds = maximum_seconds

    async def transform(self, interaction: discord.Interaction, value: str, /) -> int:
        """
        Attempts to transform the input to the desired type.

        Parameters:
            interaction (discord.Interaction): The invocation interaction.
            value (str): The input value.

        Returns:
            (int): The transformed duration.
        """

        if self.sentinel_value is not None and value == self.sentinel_value:
            return int(self.sentinel_value)  # don't use a sentinel that can't be converted to int without errors

        cal = parsedatetime.Calendar()
        now = datetime.now(tz=utc)
        time_struct, parse_status = cal.parse(value, sourceTime=now)

        if parse_status == 0:
            raise app_commands.TransformerError(value, self.type, self)

        duration = datetime(*time_struct[:6], tzinfo=utc) - now  # type: ignore[misc]
        total_seconds = ceil(duration.total_seconds())

        return self._clamp(total_seconds)

    def _clamp(self, value: int) -> int:
        """
        Clamps the transformed value to the specified range.

        Parameters:
            value (int) The un-clamped transformed value.

        Returns:
            (int): The clamped value.
        """

        if self.minimum_seconds is not None:
            value = max(self.minimum_seconds, value)

        if self.maximum_seconds is not None:
            value = min(self.maximum_seconds, value)

        return value

    @property
    def _error_display_name(self) -> str:
        """
        The name to display during errors.

        Parameters:
            None.

        Returns:
            (str): The error display name.
        """

        return 'Time Duration (30s, 1h, 5 hours, 1d, 1 day 5 seconds, etc.)'


# noinspection PyAbstractClass
class SentinelRange(SentinelTransformer):
    """
    Allows users to enter numbers within a range, including a special sentinel value that is outside of the range.
    """

    def __init__(
            self,
            minimum: Optional[int] = None,
            maximum: Optional[int] = None,
            *,
            sentinel_value: int
    ) -> None:
        """
        The constructor for the SentinelRange class.

        Parameters:
            minimum (Optional[int]): The minimum value, if any.
            maximum (Optional[int]): The maximum value, if any.
            sentinel_value (Optional[Union[str, int, float]]): The value of the sentinel.
        """

        super().__init__(sentinel_value=sentinel_value)

        self.minimum = minimum
        self.maximum = maximum

    async def transform(self, interaction: discord.Interaction, value: str, /) -> int:
        """
        Attempts to transform the input to the desired type.

        Parameters:
            interaction (discord.Interaction): The invocation interaction.
            value (str): The input value.

        Returns:
            (int): The transformed number.
        """

        try:
            return self._clamp(int(value))
        except ValueError:
            raise app_commands.TransformerError(value, self.type, self)

    def _clamp(self, value: int) -> int:
        """
        Clamps the transformed value to the specified range.

        Parameters:
            value (int) The un-clamped transformed value.

        Returns:
            (int): The clamped value.
        """

        if value == self.sentinel_value:
            return value

        if self.minimum is not None:
            value = max(self.minimum, value)

        if self.maximum is not None:
            value = min(self.maximum, value)

        return value

    @property
    def _error_display_name(self) -> str:
        """
        The name to display during errors.

        Parameters:
            None.

        Returns:
            (str): The error display name.
        """

        return 'Integer'
