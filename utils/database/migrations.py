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

import asyncio
import os
from types import TracebackType
from typing import Type, List

import aiofiles
import aiosqlite

from utils.logging_formatter import bot_logger


class MigrationVersionMismatch(Exception):
    """
    Error raised when the next migration is not sequential relative to the current version.
    """

    pass


class DatabaseVersionMissing(Exception):
    """
    Error raised when the database's version couldn't be fetched.
    """

    pass


class Migration:
    """
    A class that holding information related to a SQL migration file.

    Attributes:
        script (str): The (raw) SQL script to be executed.
        _version (str): The version associated with this script.
        name (str): The name of this migration.
    """

    def __init__(self, script: str, version: str, name: str) -> None:
        """
        The constructor for the Migration class.

        Parameters:
            script (str): The (raw) SQL script to be executed.
            version (str): The version associated with this script.
            name (str): The name of this migration.

        Returns:
            None.
        """

        self.script = script
        self._version = version
        self.name = name

    def __repr__(self) -> str:
        """
        Produces a printable representation of this class.

        Parameters:
            None.

        Returns:
            (str).
        """

        return f'{self._version}-{self.name}'

    @property
    def version(self) -> int:
        """
        Provides integer access to this migration's version.

        Parameters:
            None.

        Returns:
            (int).
        """

        return int(self._version)

    @classmethod
    async def from_file(cls, path: str, file: str) -> 'Migration':
        """
        Creates a Migration from the respective filepath.

        Parameters:
            path (str): The 'migrations' directory filepath.
            file (str): The name of the migration file.

        Returns:
            (Migration).
        """

        version, name = file.split('-', 1)

        async with aiofiles.open(os.path.join(path, file), mode='r') as f:
            script = await f.read()

        return cls(script, version, name)


class Migrator:
    """
    A class that manages SQL migration storage, preparation, and execution.

    Attributes:
        database (str): The name of the database file.
        version (int): The current database version.
        _migrations (List[Migration]): A list of all successfully-parsed migration files.
    """

    def __init__(self, database: str) -> None:
        """
        The constructor for the Migrator class.

        Parameters:
            database (str): The name of the database file.

        Returns:
            None.
        """

        self.database = database
        self.version = 0
        self._migrations: List[Migration] = []

    async def __aenter__(self) -> 'Migrator':
        """
        Asynchronous entry point logic.

        Prepares the internal list of Migrations when executed.

        Parameters:
            None.

        Returns:
            (Migrator).
        """

        await self._prepare_migrations()

        return self

    async def __aexit__(self, exc_type: Type, exc_val: Exception, exc_tb: TracebackType) -> None:
        """
        Asynchronous exit point logic.

        Parameters:
            exc_type (Type): The type of exception raised.
            exc_val (Exception): The exception raised.
            exc_tb (TracebackType): The traceback of the exception raised.

        Returns:
            None.
        """

        if exc_type:
            bot_logger.error(f'Encountered {exc_type}: {exc_val} while applying migrations.')
        if exc_tb:
            bot_logger.error(f'Traceback: {exc_tb}')

    @property
    def _available_migrations(self) -> List[Migration]:
        """
        Returns a filtered list of available migrations.
        An available migration is a migration with a version greater than the current database version.

        Parameters:
            None.

        Returns:
            (List[Migration]).
        """

        return sorted([x for x in self._migrations if x.version > self.version], key=lambda x: x.version)

    async def apply_migrations(self) -> None:
        """
        Applies all available migrations to the database.

        There's an implicit first migration of creating (if necessary) the database and fetching the current version.
        Afterwards, if there are still available migrations, a 10 second 'abort' period starts.
        If the script is still active after 10 seconds, migrations are applied atomically.

        Parameters:
            None.

        Returns:
            None.
        """

        await self._get_version()

        migration_count = len(self._available_migrations)

        if migration_count == 0:
            bot_logger.info(f'No migrations available - Database (Version {self.version:03d}) is up-to-date.')
            return

        bot_logger.critical(f'{migration_count} migration(s) are available for Database Version {self.version:03d}.')
        bot_logger.critical('Migration(s) will be automatically applied in 10 seconds.')
        await asyncio.sleep(10)

        for migration in self._available_migrations:
            try:
                bot_logger.warning(f'Attempting to apply {migration}.')
                await self._migrate(migration)
            except aiosqlite.Error as error:
                bot_logger.critical(f'{migration} failed with error: {error}.')
                raise
            else:
                bot_logger.info(f'Migration {migration} successful.')

        bot_logger.info(f'Successfully applied all migrations.')

    async def _get_version(self) -> None:
        """
        Connects to (and implicitly creates if necessary) and fetches the current database version.

        Raises:
            DatabaseVersionMissing.

        Parameters:
            None.

        Returns:
            None.
        """

        async with aiosqlite.connect(self.database) as connection:
            async with connection.execute('PRAGMA user_version') as cursor:
                result = await cursor.fetchone()

                if result and len(result) == 1:
                    self.version = result[0]
                else:
                    raise DatabaseVersionMissing

    async def _migrate(self, migration: Migration) -> None:
        """
        Applies a given migration.

        If the current migration is not strictly sequential relative to the current version, the migration fails.

        Raises:
            MigrationVersionMismatch.
            DatabaseVersionMissing.

        Parameters:
            migration (Migration): The migration to apply.

        Returns:
            None.
        """

        if self.version != migration.version - 1:
            raise MigrationVersionMismatch(f'{migration} [{self.version} -> {migration.version}]')

        async with aiosqlite.connect(self.database) as connection:
            await connection.executescript(migration.script)
            async with connection.execute('PRAGMA user_version') as cursor:
                result = await cursor.fetchone()

                if result and len(result) == 1:
                    self.version = result[0]
                else:
                    raise DatabaseVersionMissing

    async def _prepare_migrations(self) -> None:
        """
        Generates a list of Migrations from the bot's 'migrations' directory.

        Parameters:
            None.

        Returns:
            None.
        """

        path = os.path.join(os.getcwd(), 'migrations')
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        self._migrations = [await Migration.from_file(path, file) for file in files]
