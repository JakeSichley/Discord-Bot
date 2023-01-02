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

import dataclasses


@dataclasses.dataclass
class DatabaseDataclass:
    """
    A `dataclass` used to enforce type-safety for type-specified database retrievals.

    This class no attributes of its own, and is meant to be subclassed.
    """

    def __post_init__(self) -> None:
        """
        A method called after the initialization of a `dataclass`.
        Using the built-in fields attribute, we can check the actual fields vs the intended fields, and raise
        an exception if they don't match.

        Parameters:
            None.

        Raises:
            ValueError.

        Returns:
            None.
        """

        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                raise ValueError(f'Expected {field.name} to be {field.type}, got {type(value)}')


@dataclasses.dataclass
class PartialLoggingAction(DatabaseDataclass):
    """
    A DatabaseDataclass that stores the logging channel_id and bits for a guild.

    Attributes:
        channel_id (int): The logging channel id for the guild.
        bits (int): The logging bits for the guild.
    """

    channel_id: int
    bits: int


@dataclasses.dataclass
class Prefix(DatabaseDataclass):
    """
    A DatabaseDataclass that stores a guild's prefix information.

    Attributes:
        guild_id (int): The id of the guild.
        prefix (str): A prefix of the guild.

    """

    guild_id: int
    prefix: str
