import aiosqlite
import discord
from typing import List
from discord.ext.commands import IDConverter, BadArgument


async def execute_query(database_name: str, query: str, values: tuple) -> None:
    """
    A method that executes an sqlite3 statement.
    Note: Use retrieve_query() for 'SELECT' statements.

    Parameters:
        database_name (str): The name of the database.
        query (str): The statement to execute.
        values (tuple): The values to insert into the query.

    Returns:
        None.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            await db.execute(query, values)
            await db.commit()

    except aiosqlite.Error as e:
        print(f'{query} Error: {e}')


async def retrieve_query(database_name: str, query: str, values: tuple) -> List[tuple]:
    """
    A method that returns the result of an sqlite3 'SELECT' statement.
    Note: Use execute_query() for non-'SELECT' statements.

    Parameters:
        database_name (str): The name of the database.
        query (str): The statement to execute.
        values (tuple): The values to insert into the query.

    Returns:
        (list[tuple]): A list of sqlite3 row objects. Can be empty.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            async with db.execute(query, values) as cursor:
                return await cursor.fetchall()

    except aiosqlite.Error as e:
        print(f'{query} Error: {e}')


async def exists_query(database_name: str, query: str, values: tuple) -> bool:
    """
    A method that checks whether or not a record exists in the database.

    Parameters:
        database_name (str): The name of the database.
        query (str): The statement to execute.
        values (tuple): The values to insert into the query.

    Returns:
        (bool): Whether or not the user exists in the table.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            async with await db.execute(query, values) as cursor:
                return (await cursor.fetchone())[0] == 1

    except aiosqlite.Error as e:
        print(f'{query} Error: {e}')
        return False


class GuildConverter(IDConverter):
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument)
        result = None
        guild = ctx.guild

        if match is None:
            if argument.casefold() == guild.name.casefold():
                result = ctx.guild
        else:
            guild_id = int(match.group(1))
            if guild and guild.id == guild_id:
                result = ctx.guild

        if not isinstance(result, discord.Guild):
            raise BadArgument('Guild "{}" not found.'.format(argument))

        return result
