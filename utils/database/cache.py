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

from typing import Dict, List, Tuple
from utils.database.helpers import typed_retrieve_query
from utils.database import table_dataclasses as TableDC
from copy import deepcopy
from utils.logging_formatter import bot_logger
from aiosqlite import Error as aiosqliteError


class TableCache:
    """
    -

    Attributes:
    """

    def __init__(self, database: str) -> None:
        self.database = database
        self.prefixes: Dict[int, List[str]] = {}
        self.reaction_roles: Dict[Tuple[int, str], int] = {}

    async def refresh(self):
        await self.retrieve_prefixes()
        await self.retrieve_reaction_roles()

    async def retrieve_prefixes(self) -> None:
        """
        A method that creates a quick-reference dict for guilds and their respective prefixes.

        Parameters:
            None.

        Returns:
            None.
        """

        current_prefixes = deepcopy(self.prefixes)

        try:
            self.prefixes.clear()
            prefix_rows = await typed_retrieve_query(self.database, TableDC.Prefix, 'SELECT * FROM PREFIXES')

            for row in prefix_rows:
                if row.guild_id in self.prefixes:
                    self.prefixes[row.guild_id].append(row.prefix)
                else:
                    self.prefixes[row.guild_id] = [row.prefix]

        except aiosqliteError as e:
            bot_logger.error(f'Failed prefix retrieval. {e}')
            self.prefixes = current_prefixes
        else:
            bot_logger.info('Completed prefix retrieval')

    async def retrieve_reaction_roles(self) -> None:
        """
        A method that creates a quick-reference dict for reaction roles.

        Parameters:
            None.

        Returns:
            None.
        """

        current_reaction_roles = deepcopy(self.reaction_roles)

        try:
            self.reaction_roles.clear()
            reaction_rows = await typed_retrieve_query(
                self.database, TableDC.ReactionRole, 'SELECT * FROM REACTION_ROLES'
            )

            self.reaction_roles = {row.primary_key: row.role_id for row in reaction_rows}

        except aiosqliteError as e:
            bot_logger.error(f'Failed reaction role retrieval. {e}')
            self.reaction_roles = current_reaction_roles
        else:
            bot_logger.info('Completed reaction role retrieval')
