"""
MIT License

Copyright (c) 2019-2024 Jake Sichley

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
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from dreambot import DreamBot
from utils.logging_formatter import bot_logger

from utils.database.helpers import execute_query, typed_retrieve_query, typed_retrieve_one_query
import aiosqlite
from discord.utils import utcnow
from aiosqlite import Error as aiosqliteError, IntegrityError
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

from utils.database.table_dataclasses import Group, GroupMember
from contextlib import suppress

from utils.utils import format_unix_dt

# TODO: Autocomplete group names; cache group names -> group members not cached, viewable with CD [fetch from DB]


class Groups(commands.Cog):
    """
    A Cogs class that contains Groups commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    group_subgroup = app_commands.Group(name='group', description='Commands for managing groups', guild_only=True)

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Groups class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.groups: Dict[int, Dict[str, Group]] = defaultdict(dict)  # [guild_id: [group_name: Group]]

    async def cog_load(self) -> None:
        """
        A special method that acts as a cog local post-invoke hook.

        Parameters:
            None.

        Returns:
            None.
        """

        groups = await typed_retrieve_query(
            self.bot.database,
            Group,
            'SELECT * FROM GROUPS'
        )

        for group in groups:
            self.groups[group.guild_id][group.group_name] = group

    @group_subgroup.command(  # type: ignore[arg-type]
        name='create', description='Creates a new group for this guild'
    )
    @app_commands.describe(group_name='The name of the group')
    @app_commands.describe(max_members='The maximum number of members this group can have [1, 32769]')
    async def create_group(
            self,
            interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
            max_members: Optional[app_commands.Range[int, 1, None]] = None
    ) -> None:
        """
        Creates a new group for the guild. Name must be unique.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to create.
            max_members (Optional[int]): The maximum number of members that can join this group.

        Returns:
            None.
        """

        assert interaction.guild_id is not None  # guild_only

        if group_name in self.groups[interaction.guild_id]:
            await interaction.response.send_message('A group with that name already exists.', ephemeral=True)
            return

        group = Group(interaction.guild_id, interaction.user.id, int(utcnow().timestamp()), group_name, max_members)

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GROUPS VALUES (?, ?, ?, ?, ?, ?)',
                group.unpack(),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message('A group with that name already exists.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to create a new group.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully created group.', ephemeral=True)
            self.groups[interaction.guild_id][group_name] = group


    @group_subgroup.command(  # type: ignore[arg-type]
        name='delete', description='Deletes an existing group from the guild'
    )
    @app_commands.describe(group_name='The name of the group')
    async def delete_group(
            self,
            interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
    ) -> None:
        """
        Deletes an existing group from the guild.
        You can only delete your own groups, unless you are a moderator (`manage_messages`).

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to delete.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        if group_name not in self.groups[interaction.guild_id]:
            await interaction.response.send_message('That group does not exist!', ephemeral=True)
            return

        group = self.groups[interaction.guild_id][group_name]

        if group.owner_id != interaction.user.id and interaction.user.guild_permissions.manage_messages is False:
            await interaction.response.send_message(
                'You do not own that group or do not have permission to manage groups.', ephemeral=True
            )
            return

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM GROUPS WHERE GROUP_NAME=?',
                (group_name,)
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to delete the group.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully deleted the group.', ephemeral=True)
            with suppress(KeyError):
                del self.groups[interaction.guild_id][group_name]

    # todo: autocomplete
    @group_subgroup.command(  # type: ignore[arg-type]
        name='join', description='Joins a group'
    )
    @app_commands.describe(group_name="The name of the group you'd like to join")
    async def join_group(
            self,
            interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
    ) -> None:
        """
        Joins an existing group.
        Must not already be a member of the group and the group must not be at maximum capacity.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to join.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        if group_name not in self.groups[interaction.guild_id]:
            await interaction.response.send_message('That group does not exist!', ephemeral=True)
            return

        group = self.groups[interaction.guild_id][group_name]

        if group.max_members is not None and group.current_members >= group.max_members:
            await interaction.response.send_message('That group is full!', ephemeral=True)
            return

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GROUP_MEMBERS VALUES (?, ?, ?, ?)',
                (interaction.guild_id, interaction.user.id, int(utcnow().timestamp()), group_name),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message("You're already a member of this group!", ephemeral=True)
            else:
                await interaction.response.send_message('Failed to join the group.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully joined the group.', ephemeral=True)
            self.groups[interaction.guild_id][group_name].current_members += 1

    # todo: autocomplete
    @group_subgroup.command(  # type: ignore[arg-type]
        name='leave', description='Leaves a group'
    )
    @app_commands.describe(group_name="The name of the group you'd like to join")
    async def leave_group(
            self,
            interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
    ) -> None:
        """
        Leaves an existing group.
        Must already be a member of the group.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to join.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        if group_name not in self.groups[interaction.guild_id]:
            await interaction.response.send_message('That group does not exist!', ephemeral=True)
            return

        group = self.groups[interaction.guild_id][group_name]

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM GROUP_MEMBERS WHERE GUILD_ID=? AND MEMBER_ID=? AND GROUP_NAME=?',
                (interaction.guild_id, interaction.user.id, group_name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to leave the group.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully left the group.', ephemeral=True)
            self.groups[interaction.guild_id][group_name].current_members -= 1

    # todo: autocomplete
    @group_subgroup.command(  # type: ignore[arg-type]
        name='view', description='Views a group'
    )
    @app_commands.describe(group_name="The name of the group you'd like to view")
    async def view_group(
            self,
            interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
    ) -> None:
        """
        Views an existing group.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to view.

        Returns:
            None.
        """

        assert interaction.guild is not None  # guild_only
        assert interaction.guild_id is not None  # guild_only

        if group_name not in self.groups[interaction.guild_id]:
            await interaction.response.send_message('That group does not exist!', ephemeral=True)
            return

        group = self.groups[interaction.guild_id][group_name]

        owner = interaction.guild.get_member(group.owner_id)
        max_members_str = f'{group.max_members:,}' if group.max_members is not None else "None"

        try:
            group_members = await typed_retrieve_query(
                self.bot.database,
                GroupMember,
                'SELECT * FROM GROUP_MEMBERS WHERE GUILD_ID=? AND GROUP_NAME=?',
                (interaction.guild_id, group_name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to fetch group members.', ephemeral=True)
        else:
            member_list = generate_member_description(group_members, interaction.guild) if group_members else 'None'

            embed = discord.Embed(title=f'{group.group_name} Members', color=0x72fb72)
            embed.set_thumbnail(
                url='https://media.discordapp.net/attachments/634530033754570762/1193835224665165886/groups_icon.png'
            )
            embed.add_field(name='Owner', value=f'{owner.name if owner is not None else "N/A"}')
            embed.add_field(name='Created', value=format_unix_dt(group.created, 'R'))
            embed.add_field(name='​', value='​')
            embed.add_field(name='Current Members', value=f'{group.current_members:,}')
            embed.add_field(name='Max Members', value=max_members_str)
            embed.add_field(name='​', value='​')
            embed.add_field(name='Members', value=member_list, inline=False)
            embed.set_footer(text='Please report any issues to my owner!')
            await interaction.response.send_message(embed=embed)


def generate_member_description(group_members: List[GroupMember], guild: discord.Guild) -> str:
    """
    Generates a list of group members suitable for an embed field.

    Parameters:
        group_members (List[GroupMember]): The list of group members to format.
        guild (discord.Guild): The guild the group members belong to.

    Returns:
        (str): The formatted list.
    """

    members = [
        (fetched_member, member.joined) for member in group_members
        if (fetched_member := guild.get_member(member.member_id))
    ]

    if not members:
        return "Error while generating member list"

    max_name_length = max(len(x[0].name) for x in members)

    formatted = '\n'.join([f'{x[0].name:{max_name_length + 1}}    {format_unix_dt(x[1], "R")}' for x in members])

    try:
        return formatted[:formatted.rindex('\n', 0, 1024)]
    except ValueError:
        return formatted


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Groups(bot))
    bot_logger.info('Completed Setup for Cog: Groups')