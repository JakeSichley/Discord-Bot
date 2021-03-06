import aiosqlite
import discord
import datetime
import pytz
from typing import List, Sequence, Any, Iterator, Tuple
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


async def cleanup(messages: List[discord.Message], channel: discord.TextChannel) -> None:
    """
    Cleans up all prompt messages sent by the bot a command's setup.
    Attempts to bulk delete messages if permissions allow; otherwise messages are deleted individually.

    Parameters:
        messages (list[discord.Message]): The list of messages to delete.
        channel (discord.TextChannel): The channel to delete the messages from.

    Returns:
        None.
    """

    try:
        await channel.delete_messages(messages)
    except discord.Forbidden:
        while messages:
            await messages.pop().delete()
    except discord.DiscordException:
        pass


def localize_time(time: datetime.datetime) -> str:
    """
    Localizes datetime objects to Pacific time and converts the format to a readable string.

    Parameters:
        time (datetime.datetime): The datetime object to localize.

    Returns:
        (str): The readable and localized date and time.
    """

    pacific = datetime.datetime.now(pytz.timezone('US/Pacific'))
    offset_time = time + datetime.timedelta(seconds=pacific.utcoffset().total_seconds())
    return offset_time.strftime('%I:%M %p on %A, %B %d, %Y')


class GuildConverter(IDConverter):
    """
    Converts to a discord.Guild

    All lookups are via the local guild.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    4. Lookup by name
    """

    async def convert(self, ctx, argument):
        """
        Attempts to convert the argument into a discord.Guild object.

        Parameters:
            ctx (commands.Context): The invocation context.
            argument (str): The arg to be converted.

        Returns:
            result (discord.Guild): The resulting discord.Guild. Could be None if conversion failed without exceptions.
        """

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


def pairs(sequence: Sequence[Any]) -> Iterator[Tuple[Any, Any]]:
    """
    Generator that yields pairs of items in a sequence

    Parameters:
        sequence (Sequence[Any]): A sequence of items.

    Returns:
        None.

    Yields:
        (Iterator[(Any, Any)]): The next pair of items from the sequence.
    """

    i = iter(sequence)
    prev = next(i)
    for item in i:
        yield prev, item
        prev = next(i)
