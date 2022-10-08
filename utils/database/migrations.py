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

from utils.logging_formatter import bot_logger
import aiosqlite
import aiofiles
import asyncio
import os


class MigrationVersionMismatch(Exception):
    pass

class Migration:

    def __init__(self, script: str, version: str, name: str) -> None:
        self.script = script
        self._version = version
        self.name = name

    def __repr__(self):
        return f'{self._version}-{self.name}'

    @property
    def version(self) -> int:
        return int(self._version)

    @classmethod
    async def from_file(cls, path: str, file: str):
        version, name = file.split('-', 1)

        async with aiofiles.open(os.path.join(path, file), mode='r') as f:
            script = await f.read()

        return cls(script, version, name)


class Migrator:

    def __init__(self, database):
        self.database = database
        self.version = 0
        self._migrations = []

    async def __aenter__(self):
        await self._prepare_migrations()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            exc_val = exc_val or 'N/A'
            bot_logger.error(f'Encountered {exc_type}: {exc_val} while applying migrations.')
        if exc_tb:
            bot_logger.error(f'Traceback: {exc_tb}')

    @property
    def _available_migrations(self) -> [Migration]:
        return sorted([x for x in self._migrations if x.version > self.version], key=lambda x: x.version)

    async def apply_migrations(self) -> None:
        await self._create_database()

        migration_count = len(self._available_migrations)

        if migration_count == 0:
            bot_logger.info(f'No migrations available - Database (Version {self.version:03d}) is up-to-date.')
            return

        bot_logger.critical(f'{migration_count} migrations are available for Database Version {self.version:03d}.')
        bot_logger.critical('Migrations will be automatically applied in 10 seconds.')
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

    async def _create_database(self) -> None:
        async with aiosqlite.connect(self.database) as connection:
            async with connection.execute('PRAGMA user_version') as cursor:
                self.version = (await cursor.fetchone())[0]

    async def _migrate(self, migration: Migration) -> None:
        if self.version != migration.version - 1:
            raise MigrationVersionMismatch(f'{migration}')

        async with aiosqlite.connect(self.database) as connection:
            await connection.executescript(migration.script)
            async with connection.execute('PRAGMA user_version') as cursor:
                self.version = (await cursor.fetchone())[0]

    async def _prepare_migrations(self) -> None:
        path = os.path.join(os.getcwd(), 'migrations')
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        self._migrations = [await Migration.from_file(path, file) for file in files]
