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
from typing import List, Tuple, Any, Optional, TypeVar

import aiosqlite

from utils.logging_formatter import bot_logger

T = TypeVar('T')


@dataclasses.dataclass
class DatabaseDataclass:
    """
    A `dataclass` used to enforce type-safety for type-specified database retrievals.

    This class no attributes of its own, and is meant to subclassed.
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


async def execute_query(connection: aiosqlite.Connection, query: str, values: Tuple[Any, ...] = None) -> Optional[int]:
    """
    A method that executes a sqlite3 statement.
    Note: Use retrieve_query() for 'SELECT' statements.

    Parameters:
        connection (aiosqlite.Connection): The bot's current database connection.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Raises:
        aiosqlite.Error.

    Returns:
        (Optional[int]): The number of affect rows.
    """

    values = values if values else tuple()

    try:
        affected = await connection.execute(query, values)
        await connection.commit()
        return affected.rowcount

    except aiosqlite.Error as error:
        bot_logger.error(f'Execute Query ("{query}"). {error}.')
        raise error


async def retrieve_query(
        connection: aiosqlite.Connection, query: str, values: Tuple[Any, ...] = None
) -> List[Tuple[Any, ...]]:
    """
    A method that returns the result of a sqlite3 'SELECT' statement.
    Note: Use execute_query() for non-'SELECT' statements.

    Parameters:
        connection (aiosqlite.Connection): The bot's current database connection.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Raises:
        aiosqlite.Error.

    Returns:
        (List[Tuple[Any, ...]]): A list of sqlite3 row objects. Can be empty.
    """

    values = values if values else tuple()

    try:
        async with connection.execute(query, values) as cursor:
            return await cursor.fetchall()

    except aiosqlite.Error as error:
        bot_logger.error(f'Retrieve Query ("{query}"). {error}.')
        raise error


async def typed_retrieve_query(
        connection: aiosqlite.Connection, data_type: T, query: str, values: Tuple[Any, ...] = None,
) -> List[T]:
    """
    An advanced SQLite 'SELECT' query. Attempts to coerced retrieved rows to the specified data type.

    Warnings:
        PyCharm incorrectly warns for primitive types. List[Type[int]] instead of List[int].

    Examples:
        There's three primary ways to use `typed_retrieve_query`:
            (1) Primitive types,
            (2) Named Tuples,
            (3) DatabaseDataclass subclasses

        Primitives and NamedTuples are quick and easy ways to work with more structured data, but don't enforce
        type safety. `DatabaseDataclass` subclasses require more work to set up, but enforce type safety.

        (1) Primitive Types
            Useful for selecting a single column from a table.

            typed_retrieve_query(
                ...,
                str,
                'SELECT PREFIX FROM PREFIXES WHERE GUILD_ID=...',
                ...
            )

        (2) NamedTuples
            Useful for selecting multiple (but still partial) data from a table.
            Provides named attribute access to the requested data, but does not force type coercion.

            typed_retrieve_query(
                ...,
                NamedTuple('PartialVoiceRole', [('channel_id', int), ('role_id', int)]),
                'SELECT CHANNEL_ID, ROLE_ID FROM VOICE_ROLES WHERE GUILD_ID=...',
                ...
            )

        (3) `DatabaseDataclass` subclasses
            Useful for selecting full rows from a table.
            Provides named attribute access to the requested data with full type safety.

            Note:
                If this level of type-safety is desirable (or required) for all queries, the data_type parameter
                can be narrowed to TypeVar('T', bound=Type[DatabaseDataclass], covariant=True).

            @dataclass
            class VoiceRole(DatabaseDataclass):
                guild_id: int
                channel_id: int
                role_id: int

            typed_retrieve_query(
                ...,
                VoiceRole,
                'SELECT * FROM VOICE_ROLES WHERE GUILD_ID=...',
                ...
            )

    Parameters:
        connection (aiosqlite.Connection): The bot's current database connection.
        data_type (T): The data type to coerce returned rows to.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Raises:
        aiosqlite.Error.

    Returns:
        (List[Any]): A list of sqlite3 row objects. Can be empty.
    """

    values = values if values else tuple()

    try:
        async with connection.execute(query, values) as cursor:
            data = await cursor.fetchall()
    except aiosqlite.Error as error:
        bot_logger.error(f'Retrieve Query ("{query}"). {error}.')
        raise error

    transformed_entries = []

    for entry in data:
        try:
            transformed_entries.append(data_type(*entry))
        except (TypeError, ValueError):  # data couldn't be coerced to T
            pass

    return transformed_entries
