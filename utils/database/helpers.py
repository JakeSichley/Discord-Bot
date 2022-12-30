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
from typing import List, Tuple, Any, Optional, Iterable, Type, TypeVar

import aiosqlite
from typing_extensions import TypeGuard

from utils.logging_formatter import bot_logger

T = TypeVar('T')


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


async def execute_query(
        database: str, query: str, values: Optional[Tuple[Any, ...]] = None
) -> Optional[int]:
    """
    A method that executes a sqlite3 statement.
    Note: Use retrieve_query() for 'SELECT' statements.

    Parameters:
        database (str): The name of the bot's database.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Raises:
        aiosqlite.Error.

    Returns:
        (Optional[int]): The number of affect rows.
    """

    values = values or tuple()

    try:
        async with aiosqlite.connect(database) as connection:
            affected = await connection.execute(query, values)
            await connection.commit()
            return affected.rowcount

    except aiosqlite.Error as error:
        bot_logger.error(f'Execute Query ("{query}"). {error}.')
        raise error


async def retrieve_query(
        database: str, query: str, values: Optional[Tuple[Any, ...]] = None
) -> Iterable[Tuple[Any, ...]]:
    """
    A method that returns the result of a sqlite3 'SELECT' statement.
    Note: Use execute_query() for non-'SELECT' statements.

    Parameters:
        database (str): The name of the bot's database.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Raises:
        aiosqlite.Error.

    Returns:
        (List[Tuple[Any, ...]]): A list of sqlite3 row objects. Can be empty.
    """

    values = values or tuple()

    try:
        async with aiosqlite.connect(database) as connection:
            async with connection.execute(query, values) as cursor:
                rows = await cursor.fetchall()
                assert (Sqlite3Typing.fetchall(rows))

                return rows

    except aiosqlite.Error as error:
        bot_logger.error(f'Retrieve Query ("{query}"). {error}.')
        raise error


async def typed_retrieve_query(
        database: str, data_type: Type[T], query: str, values: Optional[Tuple[Any, ...]] = None,
) -> List[T]:
    """
    A typed SQLite 'SELECT' query. Attempts to coerced retrieved rows to the specified data type.

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
        database (str): The name of the bot's database.
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
        async with aiosqlite.connect(database) as connection:
            async with connection.execute(query, values) as cursor:
                data = await cursor.fetchall()
    except aiosqlite.Error as error:
        bot_logger.error(f'Retrieve Query ("{query}"). {error}.')
        raise error

    transformed_entries = []

    for entry in data:
        try:
            transformed_entries.append(data_type(*entry))
        except (TypeError, ValueError) as e:  # data couldn't be coerced to T
            bot_logger.error(
                f'Bad Entry for type {data_type} - {e}.\n'
                f'Data: {entry}\n'
                f'Query: {query}\n'
                f'Params: {values}'
            )
            pass

    return transformed_entries


class Sqlite3Typing:
    """
    Static methods to assist with mypy typing for Sqlite3 cursor methods that return rows.
    """

    @staticmethod
    def fetchall(val: Iterable[object]) -> TypeGuard[Iterable[Tuple[Any, ...]]]:
        """
        A TypeGuard for mypy to assert that `fetchall() -> Iterable[sqlite3.Row]` == Iterable[Tuple[Any, ...]].

        Parameters:
            val (Iterable[object]): The sqlite3.Rows to typeguard.

        Returns:
            (TypeGuard[Iterable[Tuple[Any, ...]]]): The narrowed type.
        """

        return all(isinstance(x, tuple) for x in val)

    @staticmethod
    def fetchone(val: object) -> TypeGuard[Optional[Tuple[Any, ...]]]:
        """
        A TypeGuard for mypy to assert that `fetchone() -> Optional[sqlite3.Row]` == Optional[Tuple[Any, ...]].

        Parameters:
            val (object): The sqlite3.Row to typeguard.

        Returns:
            (TypeGuard[Optional[Tuple[Any, ...]]]): The narrowed type.
        """

        return isinstance(val, tuple) or val is None
