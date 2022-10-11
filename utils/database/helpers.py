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

from typing import List, Tuple, Any, Optional
from utils.logging_formatter import bot_logger
import aiosqlite


async def execute_query(connection: aiosqlite.Connection, query: str, values: Tuple[Any, ...] = None) -> Optional[int]:
    """
    A method that executes a sqlite3 statement.
    Note: Use retrieve_query() for 'SELECT' statements.

    Parameters:
        connection (aiosqlite.Connection): The bot's current database connection.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

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


async def retrieve_query(connection: aiosqlite.Connection, query: str, values: Tuple[Any, ...] = None) -> List[Any]:
    """
    A method that returns the result of a sqlite3 'SELECT' statement.
    Note: Use execute_query() for non-'SELECT' statements.

    Parameters:
        connection (aiosqlite.Connection): The bot's current database connection.
        query (str): The statement to execute.
        values (Tuple[Any, ...]): The values to insert into the query.

    Returns:
        (List[Any]): A list of sqlite3 row objects. Can be empty.
    """

    values = values if values else tuple()

    try:
        async with connection.execute(query, values) as cursor:
            return await cursor.fetchall()

    except aiosqlite.Error as error:
        bot_logger.error(f'Retrieve Query ("{query}"). {error}.')
        raise error