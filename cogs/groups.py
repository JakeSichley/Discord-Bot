"""
MIT License

Copyright (c) 2019-Present Jake Sichley

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
from contextlib import suppress
from random import choice as random_choice
from typing import Optional, Dict, List, Tuple

import aiosqlite
import discord
from aiosqlite import Error as aiosqliteError, IntegrityError
from discord import app_commands, Interaction
from discord.app_commands import Choice, Range, Transform
from discord.ext import commands
from discord.utils import utcnow

from dreambot import DreamBot
from utils.autocomplete import generate_autocomplete_choices
from utils.checks import InvocationCheckFailure
from utils.database.helpers import execute_query, typed_retrieve_query
from utils.database.table_dataclasses import Group, GroupMember
from utils.intermediate_models.composite_group import CompositeGroup
from utils.logging_formatter import bot_logger
from utils.transformers import StringTransformer
from utils.utils import format_unix_dt

# TODO: Groups v3 -> edit group (max_members); needs components for confirmation when new max_members < current_members

"""
Group Name (& Key)
    Group Name should maintain creator's case. Ex: "mY GrOUP" should show up as "mY GrOUP"
    Group Name searches should be case-insensitive. Ex: "my group" should return the group "mY GrOUP"
"""
GroupName = StringTransformer(
    mutator=lambda x: x.strip(),
    constraint=lambda x: x is not None and 1 <= len(x) <= 100,
)


@app_commands.guild_only
class Groups(commands.GroupCog, group_name='group', group_description='Commands for managing Groups'):
    """
    A Cogs class that contains Groups commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Groups class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        # [guild_id: [key: CompositeGroup]]
        self.groups: Dict[int, Dict[str, CompositeGroup]] = defaultdict(dict)

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
            self.groups[group.guild_id][group.key] = CompositeGroup(group)

        group_members = await typed_retrieve_query(
            self.bot.database,
            GroupMember,
            'SELECT * FROM GROUP_MEMBERS'
        )

        for group_member in group_members:
            self.groups[group_member.guild_id][group_member.group_key].members.add(group_member.member_id)

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='create', description='Creates a new group')
    @app_commands.describe(group_name="The name of the group you'd like to create")
    @app_commands.describe(max_members='Optional: The maximum number of members this group can have')
    @app_commands.describe(
        ephemeral_updates='Optional: Whether updates to this group should be silent. Updates are not silent by default.'
    )
    @app_commands.rename(ephemeral_updates='silent_updates')
    async def create_group(
            self,
            interaction: Interaction[DreamBot],
            group_name: Transform[str, GroupName],
            max_members: Optional[Range[int, 1, 2_500_000]] = None,
            ephemeral_updates: bool = False
    ) -> None:
        """
        Creates a new group for the guild. Name must be unique.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to create.
            max_members (Optional[int]): The maximum number of members that can join this group.
            ephemeral_updates (Bool): Whether updates to this group should be silent (ephemeral).

        Returns:
            None.
        """

        assert interaction.guild_id is not None  # guild_only

        if group_name.casefold() in self.groups[interaction.guild_id]:
            raise InvocationCheckFailure('A group with that name already exists.')

        group = Group(
            interaction.guild_id,
            interaction.user.id,
            int(utcnow().timestamp()),
            group_name,
            max_members,
            0,
            1 if ephemeral_updates else 0
        )

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GROUPS VALUES (?, ?, ?, ?, ?, ?, ?)',
                group.unpack(),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message('A group with that name already exists.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to create a new group.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully created group.', ephemeral=True)
            else:
                max_members_str = f'{group.max_members:,}' if group.max_members is not None else "∞"
                await interaction.response.send_message(
                    f'_{interaction.user.mention} created group "**{group.name}**" ({max_members_str} max members)_',
                    allowed_mentions=discord.AllowedMentions.none()
                )
            self.groups[interaction.guild_id][group.key] = CompositeGroup(group)

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='delete', description='Deletes an existing group')
    @app_commands.describe(group_name="The name of the group you'd like to delete")
    async def delete_group(self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName]) -> None:
        """
        Deletes an existing group from the guild.
        You can only delete your own groups unless you are a moderator (`manage_messages`).

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to delete.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        group = self.get_group(interaction.guild_id, group_name)

        self.privileged_action_check(interaction.user, group.owner_id)

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM GROUPS WHERE GROUP_NAME=? AND GUILD_ID=?',
                (group.name, interaction.guild_id)
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to delete group.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully deleted group.', ephemeral=True)
            else:
                await interaction.response.send_message(
                    f'_{interaction.user.mention} deleted group "**{group.name}**" '
                    f'({group.current_members:,} members)_',
                    allowed_mentions=discord.AllowedMentions.none()
                )

            with suppress(KeyError):
                del self.groups[interaction.guild_id][group.key]

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='join', description='Joins an existing group')
    @app_commands.describe(group_name="The name of the group you'd like to join")
    async def join_group(self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName]) -> None:
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

        group = self.get_group(interaction.guild_id, group_name)

        if interaction.user.id in group.members:
            raise InvocationCheckFailure("You're already a member of this group!")

        if group.is_full:
            raise InvocationCheckFailure('That group is full!')

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GROUP_MEMBERS VALUES (?, ?, ?, ?)',
                (interaction.guild_id, interaction.user.id, int(utcnow().timestamp()), group.name),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message("You're already a member of this group!", ephemeral=True)
            else:
                await interaction.response.send_message('Failed to join group.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully joined group.', ephemeral=True)
            else:
                max_members_str = f'{group.max_members:,}' if group.max_members is not None else "∞"
                await interaction.response.send_message(
                    f'_{interaction.user.mention} joined group "**{group.name}**" '
                    f'({group.current_members + 1:,}/{max_members_str} members)_',
                    allowed_mentions=discord.AllowedMentions.none()
                )

            self.groups[interaction.guild_id][group.key].add_member(interaction.user.id)

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='leave', description="Leaves a group you're an existing member of")
    @app_commands.describe(group_name="The name of the group you'd like to leave")
    async def leave_group(self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName]) -> None:
        """
        Leaves an existing group.
        Must already be a member of the group.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to leave.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        group = self.get_group(interaction.guild_id, group_name)

        if interaction.user.id not in group.members:
            raise InvocationCheckFailure('You are not a member of that group!')

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM GROUP_MEMBERS WHERE GUILD_ID=? AND MEMBER_ID=? AND GROUP_NAME=?',
                (interaction.guild_id, interaction.user.id, group.name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to leave group.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully left group.', ephemeral=True)
            else:
                max_members_str = f'{group.max_members:,}' if group.max_members is not None else "∞"
                await interaction.response.send_message(
                    f'_{interaction.user.mention} left group "**{group.name}**" '
                    f'({group.current_members - 1:,}/{max_members_str} members)_',
                    allowed_mentions=discord.AllowedMentions.none()
                )

            self.groups[interaction.guild_id][group.key].remove_member(interaction.user.id)

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='kick', description="Removes a member from an existing group")
    @app_commands.describe(group_name="The name of the group you'd like to remove a member from")
    @app_commands.describe(member="The member to remove")
    async def kick_from_group(
            self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName], member: discord.Member
    ) -> None:
        """
        Kicks a member from a group.
        You must either own the group or be a moderator to kick members from groups.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to remove a member from.
            member (discord.Member): The member to remove.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only

        if interaction.user.id == member.id:
            responses = [
                "You'll have to try and enter the high-stakes world of self-banishment somewhere else!",
                "My, my, such drastic measures are not necessary here!",
                "Are you staging a coup on yourself? Sounds like a power struggle for the ages... ",
                "Whoa there, do you have a ticket for the self-eviction express?"
            ]
            raise InvocationCheckFailure(random_choice(responses))

        group = self.get_group(interaction.guild_id, group_name)

        self.privileged_action_check(interaction.user, group.owner_id)

        if member.id not in group.members:
            raise InvocationCheckFailure('That member does not belong to that group!')

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM GROUP_MEMBERS WHERE GUILD_ID=? AND MEMBER_ID=? AND GROUP_NAME=?',
                (interaction.guild_id, member.id, group.name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to kick member from group.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully kicked member from group.', ephemeral=True)
            else:
                max_members_str = f'{group.max_members:,}' if group.max_members is not None else "∞"

                await interaction.response.send_message(
                    f'_{interaction.user.mention} removed {member.mention} from group "**{group.name}**" '
                    f'({group.current_members - 1:,}/{max_members_str} members)_',
                    allowed_mentions=discord.AllowedMentions(users=[member])
                )

            self.groups[interaction.guild_id][group.key].remove_member(member.id)

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='transfer', description="Transfers group ownership to a new member")
    @app_commands.describe(group_name="The name of the group you'd like to transfer ownership of")
    @app_commands.describe(member="The member to give ownership to")
    async def transfer_group(
            self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName], member: discord.Member
    ) -> None:
        """
        Transfers group ownership to a new member.
        You must either own the group or be a moderator to transfer group ownership.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to transfer membership from.
            member (discord.Member): The member to give ownership to.

        Returns:
            None.
        """

        assert isinstance(interaction.user, discord.Member)  # guild_only
        assert interaction.guild_id is not None  # guild_only
        assert interaction.guild is not None  # guild_only

        group = self.get_group(interaction.guild_id, group_name)
        owner = interaction.guild.get_member(group.owner_id)

        if member.id == group.owner_id:
            raise InvocationCheckFailure("Ah, yes, the ol' self-transferoo. Bold move, Cotton.")

        self.privileged_action_check(interaction.user, group.owner_id)

        try:
            await execute_query(
                self.bot.database,
                'UPDATE GROUPS SET OWNER_ID=? WHERE GUILD_ID=? AND GROUP_NAME=?',
                (member.id, interaction.guild_id, group.name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to transfer group ownership.', ephemeral=True)
        else:
            if group.ephemeral_updates:
                await interaction.response.send_message('Successfully transferred group ownership.', ephemeral=True)
            else:
                await interaction.response.send_message(
                    f'_{interaction.user.mention} transferred ownership of group "**{group.name}**" to '
                    f'{member.mention} from {owner.mention if owner is not None else "N/A"}_',
                    allowed_mentions=discord.AllowedMentions(users=[member, owner] if owner is not None else [member])
                )

            self.groups[interaction.guild_id][group.key].group.owner_id = member.id

    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.command(name='view', description='View an existing group')
    @app_commands.describe(group_name="The name of the group you'd like to view")
    async def view_group(self, interaction: Interaction[DreamBot], group_name: Transform[str, GroupName]) -> None:
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

        group = self.get_group(interaction.guild_id, group_name).group
        owner = interaction.guild.get_member(group.owner_id)
        max_members_str = f'{group.max_members:,}' if group.max_members is not None else "None"

        try:
            group_members = await typed_retrieve_query(
                self.bot.database,
                GroupMember,
                'SELECT * FROM GROUP_MEMBERS WHERE GUILD_ID=? AND GROUP_NAME=?',
                (interaction.guild_id, group.name),
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to fetch group members.', ephemeral=True)
        else:
            group_members.sort(key=lambda x: x.joined)
            member_list = [
                (fetched_member, member.joined) for member in group_members
                if (fetched_member := interaction.guild.get_member(member.member_id))
            ]

            max_elements = calculate_member_and_joined_max_splice(member_list)

            if not member_list:
                members_field = 'None'
                positions_field = '-'
                joined_field = '-'
            elif max_elements <= 0:
                members_field = 'Error generating members field'
                positions_field = 'N/A'
                joined_field = 'N/A'
            else:
                members_field = '\n'.join(x[0].mention for x in member_list[:max_elements])
                positions_field = '\n'.join(str(x) for x in range(1, max_elements + 1))
                joined_field = '\n'.join(format_unix_dt(x[1], 'R') for x in member_list[:max_elements])

            embed = discord.Embed(title=f'{group.name} Members', color=0x64d1ff)
            embed.set_thumbnail(
                url='https://cdn.discordapp.com/attachments/634530033754570762/1194039472514408479/group_icon.png'
            )
            embed.add_field(name='Owner', value=f'{owner.mention if owner is not None else "N/A"}')
            embed.add_field(name='Created', value=format_unix_dt(group.created, 'R'))
            embed.add_field(name='​', value='​')
            embed.add_field(name='Current Members', value=f'{len(member_list):,}')
            embed.add_field(name='Max Members', value=max_members_str)
            embed.add_field(name='​', value='​')
            embed.add_field(name='Members', value=members_field)
            embed.add_field(name='Position', value=positions_field)
            embed.add_field(name='Joined', value=joined_field)
            embed.set_footer(text='Please report any issues to my owner!')
            await interaction.response.send_message(embed=embed)

    """
    MARK: - Autocomplete Methods
    """

    @delete_group.autocomplete('group_name')
    @join_group.autocomplete('group_name')
    @leave_group.autocomplete('group_name')
    @view_group.autocomplete('group_name')
    @kick_from_group.autocomplete('group_name')
    @transfer_group.autocomplete('group_name')
    async def existing_group_name_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes group names for the current guild.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        assert isinstance(interaction.command, discord.app_commands.Command)  # decorator enforcement
        assert interaction.guild_id is not None  # guild_only
        assert isinstance(interaction.user, discord.Member)  # guild_only

        try:
            groups = self.groups[interaction.guild_id].keys()
        except AttributeError:
            return []

        """
        Autocomplete Logic:
            Create -> None
            Delete/Kick/Transfer ~
                is_moderator -> All
                not_moderator -> User is owner
            Join -> Not full and user not already joined
            Leave -> User Already joined
            View -> All
        """

        if interaction.command.name in {'delete', 'kick', 'transfer'}:
            if not interaction.user.guild_permissions.manage_messages:
                options = [
                    x for x in groups if self.groups[interaction.guild_id][x].group.owner_id == interaction.user.id
                ]
            else:
                options = [x for x in groups]
        elif interaction.command.name == 'join':
            options = [
                x for x in groups
                if not self.groups[interaction.guild_id][x].is_full
                   and interaction.user.id not in self.groups[interaction.guild_id][x].members
            ]
        elif interaction.command.name == 'leave':
            options = [x for x in groups if interaction.user.id in self.groups[interaction.guild_id][x].members]
        elif interaction.command.name == 'view':
            options = [x for x in groups]
        else:
            options = []

        if not current:
            return [
                Choice(
                    name=enhanced_autocomplete_description(self.groups[interaction.guild_id][x], interaction.guild),
                    value=x
                ) for x in options[:25]
            ]

        return generate_autocomplete_choices(
            current,
            [
                (enhanced_autocomplete_description(self.groups[interaction.guild_id][x], interaction.guild), x)
                for x in options
            ],
            minimum_threshold=100
        )

    """
    MARK: - Listener Methods
    """

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a new user joins a guild.

        Parameters:
            member (discord.Member): The member that joined the guild.

        Returns:
            None.
        """

        # restore ownership if any groups remain unclaimed

        with suppress(aiosqliteError):
            await execute_query(
                self.bot.database,
                'UPDATE GROUPS SET OWNER_ID=? WHERE GUILD_ID=? AND OWNER_ID=?',
                (member.id, member.guild.id, -member.id)
            )

            updated_group_names = await typed_retrieve_query(
                self.bot.database,
                str,
                'SELECT GROUP_NAME FROM GROUPS WHERE OWNER_ID=? AND GUILD_ID=?',
                (member.id, member.guild.id)
            )

            for group_name in updated_group_names:
                self.groups[member.guild.id][group_name.casefold()].group.owner_id = member.id

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent) -> None:
        """
        A commands.Cog listener event that is called whenever a member is removed from the guild, regardless of
        the state of the internal cache.

        Parameters:
            payload (discord.RawMemberRemoveEvent): The raw event payload data.

        Returns:
            None.
        """

        # set ownership to a sentinel value of -(user_id) for pseudo-tracking

        # group ownership
        with suppress(aiosqliteError):
            await execute_query(
                self.bot.database,
                'UPDATE GROUPS SET OWNER_ID=? WHERE GUILD_ID=? AND OWNER_ID=?',
                (-payload.user.id, payload.guild_id, payload.user.id)
            )

            updated_group_names = await typed_retrieve_query(
                self.bot.database,
                str,
                'SELECT GROUP_NAME FROM GROUPS WHERE OWNER_ID=? AND GUILD_ID=?',
                (-payload.user.id, payload.guild_id)
            )

            for group_name in updated_group_names:
                self.groups[payload.guild_id][group_name.casefold()].group.owner_id = -payload.user.id

        # group membership
        with suppress(aiosqliteError):
            updated_group_names = await typed_retrieve_query(
                self.bot.database,
                str,
                'SELECT GROUP_NAME FROM GROUP_MEMBERS WHERE GUILD_ID=? AND MEMBER_ID=?',
                (payload.guild_id, payload.user.id)
            )

            await execute_query(
                self.bot.database,
                'DELETE FROM GROUP_MEMBERS WHERE GUILD_ID=? AND MEMBER_ID=?',
                (payload.guild_id, payload.user.id)
            )

            for group_name in updated_group_names:
                self.groups[payload.guild_id][group_name.casefold()].remove_member(payload.user.id)

    """
    MARK: - Checks
    """

    def get_group(self, guild_id: int, group_name: str) -> CompositeGroup:
        """
        Returns the relevant group for the interaction.

        Parameters:
            guild_id (int): The id of the guild.
            group_name (str): The name of the group.

        Raises:
            (InvocationCheckFailure): The group was not found.

        Returns:
            (CompositeGroup): The relevant group for the invocation context.
        """

        group_key = group_name.casefold()

        if group_key not in self.groups[guild_id]:
            raise InvocationCheckFailure('That group does not exist!')

        return self.groups[guild_id][group_key]

    # noinspection PyMethodMayBeStatic
    def privileged_action_check(self, member: discord.Member, group_owner_id: int) -> None:
        """
        Checks whether the member owns the group or has elevated permissions in the guild.

        Parameters:
            member (discord.Member): The member that invoked the command.
            group_owner_id (int): The id of the group owner.

        Raises:
            (InvocationCheckFailure): The member lacks permissions to perform this action.

        Returns:
            None.
        """

        if group_owner_id != member.id and not member.guild_permissions.manage_messages:
            raise InvocationCheckFailure('You do not own that group or do not have permission to manage groups.')


def calculate_member_and_joined_max_splice(group_members: List[Tuple[discord.Member, int]]) -> int:
    """
    Calculates the maximum splice of the member and joined embed fields.

    Parameters:
        group_members (List[GroupMember]): The list of group members to format.

    Returns:
        (int) The maximum splice of fields.
    """

    if not group_members:
        return -1

    last_member_index = find_last_index_under_threshold([x[0].mention for x in group_members])
    last_timestamp_index = find_last_index_under_threshold([str(x[1]) for x in group_members])

    return min(last_member_index, last_timestamp_index)


def find_last_index_under_threshold(collection: List[str]) -> int:
    """
    Finds the last element (index) that would allow the collection to remain under the embed field limit (1024).

    Parameters:
        collection (List[str]): The elements to examine.

    Returns:
        (Optional[int]): The index of the last viable element, if any.
    """

    running_total = 0

    for index, element in enumerate(collection):
        # +1 for future newline
        if running_total + len(element) + 1 <= 1024:
            running_total += len(element) + 1
        else:
            return index - 1

    return len(collection)


def enhanced_autocomplete_description(group: CompositeGroup, guild: Optional[discord.Guild]) -> str:
    """
    Adds additional context information to group name autocomplete descriptions.

    Parameters:
        group (CompositeGroup): The group to generate an autocomplete description for.
        guild (discord.Guild): The guild the group belongs to.

    Returns:
        (str): The enhanced autocomplete description.
    """

    if guild is None:  # should always be a resolved guild
        return group.name

    descriptions: List[str] = []

    if owner := guild.get_member(group.owner_id):
        descriptions.append(f'Owner: {owner.display_name}')

    max_members_str = f'{group.max_members:,}' if group.max_members is not None else "∞"
    descriptions.append(f'{group.current_members:,}/{max_members_str} members')
    formatted_description = f' ({", ".join(descriptions)})'

    if len(formatted_description) + len(group.name) > 100:
        truncated_name_length = 100 - len(formatted_description) - 3
        return f'{group.name[:truncated_name_length]}...{formatted_description}'
    else:
        return f'{group.name}{formatted_description}'


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
