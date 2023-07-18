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

from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Tuple, DefaultDict

from aiosqlite import Error as aiosqliteError

from utils.database import table_dataclasses as TableDC
from utils.database.helpers import typed_retrieve_query
from utils.enums.guild_feature import GuildFeature, has_guild_feature
from utils.logging_formatter import bot_logger


class TableCache:
    """
    Caches frequently accessed tables in the bot's memory.

    Attributes:
        database (str): The name of the bot's database.
        prefixes (Dict[int, List[str]]): A Guild.id: Prefix mapping.
        reaction_roles (Dict[Tuple[int, str], int]): A (Message.id, Reaction): Role.id mapping.
        voice_roles (DefaultDict[int, List[TableDC.VoiceRole]]): A Guild.id: VoiceRole mapping.
        default_roles (Dict[int, int]): A Guild.id: Role.id mapping.
        guild_features (Dict[int: int]): A Guild.id: Feature{IntFlag} mapping.
    """

    def __init__(self, database: str) -> None:
        self.database = database
        self.prefixes: Dict[int, List[str]] = {}
        self.reaction_roles: Dict[Tuple[int, str], int] = {}
        self.voice_roles: DefaultDict[int, List[TableDC.VoiceRole]] = defaultdict(list)
        self.default_roles: Dict[int, int] = {}
        self.guild_features: Dict[int, int] = {}

    async def sync(self) -> None:
        """
        Syncs relevant tables to the bot's cache.

        Parameters:
            None.

        Returns:
            None.
        """

        await self.retrieve_prefixes()
        await self.retrieve_reaction_roles()
        await self.retrieve_voice_roles()
        await self.retrieve_default_roles()
        await self.retrieve_guild_features()

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
            bot_logger.error(f'Failed Prefix retrieval. {e}')
            self.prefixes = current_prefixes
        else:
            bot_logger.info('Completed Prefix retrieval.')

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
            bot_logger.error(f'Failed Reaction Role retrieval. {e}')
            self.reaction_roles = current_reaction_roles
        else:
            bot_logger.info('Completed Reaction Role retrieval.')

    async def retrieve_voice_roles(self) -> None:
        """
        A method that creates a quick-reference dict for voice roles.

        Parameters:
            None.

        Returns:
            None.
        """

        current_voice_roles = deepcopy(self.voice_roles)

        try:
            self.voice_roles.clear()
            voice_roles = await typed_retrieve_query(
                self.database, TableDC.VoiceRole, 'SELECT * FROM VOICE_ROLES'
            )

            for row in voice_roles:
                self.voice_roles[row.guild_id].append(row)

        except aiosqliteError as e:
            bot_logger.error(f'Failed Voice Role retrieval. {e}')
            self.voice_roles = current_voice_roles
        else:
            bot_logger.info('Completed Voice Role retrieval.')

    async def retrieve_default_roles(self) -> None:
        """
        A method that creates a quick-reference dict for default roles.

        Parameters:
            None.

        Returns:
            None.
        """

        current_default_roles = deepcopy(self.default_roles)

        try:
            self.default_roles.clear()
            default_roles = await typed_retrieve_query(
                self.database, TableDC.DefaultRole, 'SELECT * FROM DEFAULT_ROLES'
            )

            self.default_roles = {row.guild_id: row.role_id for row in default_roles}

        except aiosqliteError as e:
            bot_logger.error(f'Failed Default Role retrieval. {e}')
            self.default_roles = current_default_roles
        else:
            bot_logger.info('Completed Default Role retrieval.')

    async def retrieve_guild_features(self) -> None:
        """
        A method that creates a quick-reference dict for guild features.

        Parameters:
            None.

        Returns:
            None.
        """

        current_guild_features = deepcopy(self.guild_features)

        try:
            self.guild_features.clear()
            features = await typed_retrieve_query(
                self.database, TableDC.GuildFeatures, 'SELECT * FROM GUILD_FEATURES'
            )

            self.guild_features = {row.guild_id: row.features for row in features}

        except aiosqliteError as e:
            bot_logger.error(f'Failed Guild Features retrieval. {e}')
            self.guild_features = current_guild_features
        else:
            bot_logger.info('Completed Guild Features retrieval.')

    def guild_feature_enabled(self, guild_id: int, feature: GuildFeature) -> bool:
        """
        Checks the GuildFeatures cache for a feature's status for a specific guild.

        Parameters:
            guild_id (int): The id of the guild.
            feature (GuildFeature): The feature to check.

        Returns:
            (bool).
        """

        features = self.guild_features.get(guild_id, 0)

        return has_guild_feature(features, feature)
