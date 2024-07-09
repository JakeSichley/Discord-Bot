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

from contextlib import suppress
from re import findall, sub
from typing import Union, Optional, List

import discord
from aiosqlite import Error as aiosqliteError
from discord.ext import commands

from dreambot import DreamBot
from utils.context import Context
from utils.converters import AggressiveDefaultMemberConverter
from utils.database.helpers import execute_query, typed_retrieve_query
from utils.logging_formatter import bot_logger

from discord import app_commands, Interaction, AllowedMentions, Embed
from discord.app_commands import Range



from utils.checks import app_dynamic_cooldown
from utils.interaction import GuildInteraction

CHANNEL_OBJECT = Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel]
PERMISSIONS_PARENT = Union[discord.Role, discord.Member]
PURGEABLE_INSTANCES = (discord.StageChannel, discord.TextChannel, discord.Thread, discord.VoiceChannel)
PURGEABLE_TYPE = Union[discord.StageChannel, discord.TextChannel, discord.Thread, discord.VoiceChannel]

PURGE_UPPER_BOUND: int = 50  # 1_000


class Moderation(commands.Cog):
    """
    A Cogs class that contains commands for moderating a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    moderation_subgroup = app_commands.Group(
        name='moderation',
        description='Commands for moderation of a guild',
        guild_only=True
    )

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    async def interaction_check(self, interaction: Interaction[DreamBot]) -> bool:  # type: ignore[override]
        """
        A method that registers a cog-wide check for App Commands.
        Requires these commands be used in a guild only.

        Parameters:
            interaction (Interaction): The invoking interaction.

        Returns:
            (bool): Whether the command was invoked in a guild.
        """

        return interaction.guild is not None

    @app_commands.checks.has_permissions(manage_messages=True)  # type: ignore[arg-type]
    @app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True, manage_channels=True)
    @app_commands.describe(
        limit=f'The number of messages to delete (up to {PURGE_UPPER_BOUND})',
        # full_reset='Fully purges the channel. This destroys the current channel and creates a new, identical channel.'
    )
    @moderation_subgroup.command(
        name='purge',
        description=f'Purges up to {PURGE_UPPER_BOUND} messages from the channel. '
                    # 'Use `full_reset` to completely clear the channel'
    )
    async def purge(
            self,
            interaction: GuildInteraction,
            limit: Optional[Range[int, 1, 1_000]] = None,
            # full_reset: Optional[bool] = None
    ) -> None:
        """
        Purges messages from the current channel. Optionally allows you to fully clear the current channel.

        Checks:
            has_permissions(manage_messages): Whether the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether the bot can manage messages
                and read the message history of a channel, both of which are required for the deletion of messages.

        Parameters:
            interaction (GuildInteraction): The invoking interaction.
            limit (Optional[int]): The number of messages to purge.
            # full_reset (Optional[bool]): Whether the fully clear the current channel.

        Returns:
            None.
        """

        full_reset: Optional[bool] = None

        if limit is None and full_reset is None:
            await interaction.response.send_message(f'You must specify either `limit` or `full_reset`.', ephemeral=True)
            return

        if not isinstance(interaction.channel, PURGEABLE_INSTANCES):
            await interaction.response.send_message(f'You cannot purge this channel type.')
            return

        # TODO: Add components for confirmation for >50 or full_reset
        if limit is not None:
            await interaction.response.send_message(f'Attempting to purge {limit:,} messages..', ephemeral=True)
            await interaction.channel.purge(limit=limit)
            await interaction.edit_original_response(content='Purge complete.')
            return

        # remaining cases are for full reset
        #   don't have bot re-create thread, since this has UI implications
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(f'Attempting to purge entire thread..', ephemeral=True)
            await interaction.channel.purge(limit=None)
            await interaction.edit_original_response(content='Purge complete.')
        else:
            await interaction.response.send_message(f'Attempting to purge entire channel..', ephemeral=True)
            position = interaction.channel.position
            new_channel = await interaction.channel.clone(reason=f'Full channel purge by {interaction.user}')
            await interaction.channel.delete(reason=f'Full channel purge by {interaction.user}')
            await new_channel.edit(position=position)

    @app_commands.checks.has_permissions(manage_channels=True, manage_roles=True)  # type: ignore[arg-type]
    @app_commands.checks.bot_has_permissions(manage_channels=True, manage_roles=True)
    @app_commands.describe(
        base_channel='The channel you want to copy permissions from',
        base_permission_owner='The role or member you want to copy permissions from',
        target_channel='The channel you want to copy permissions to',
        target_permission_owner='The role or member you want to copy permissions to',
    )
    @app_dynamic_cooldown()
    @moderation_subgroup.command(
        name='duplicate_permissions',
        description='Allows you duplicate a permissions overwrite to a new target'
    )
    async def duplicate_channel_permissions(
            self,
            interaction: GuildInteraction,
            base_channel: CHANNEL_OBJECT,
            base_permission_owner: PERMISSIONS_PARENT,
            target_channel: CHANNEL_OBJECT,
            target_permission_owner: PERMISSIONS_PARENT
    ) -> None:
        """
        A method to duplicate channel permissions to a different target.

        Checks:
            has_guild_permissions(manage_channels)
            bot_has_guild_permissions(manage_channels)

        Parameters:
            interaction (GuildInteraction): The invoking interaction.
            base_channel (Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel]): The base channel
                to source permissions from.
            base_permission_owner (Union[discord.Role, discord.Member]): The role or member whose permissions should
                be copied.
            target_channel (Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel]): The target
                channel to duplicate permissions to.
            target_permission_owner (Union[discord.Role, discord.Member]): The role or member the permissions should be
                copied to.

        Returns:
            None.
        """

        # no-op check
        if base_channel == target_channel and base_permission_owner == target_permission_owner:
            await interaction.response.send_message('You cannot duplicate a permission to itself!', ephemeral=True)
            return

        # permissions check
        base_highest_role: discord.Role = base_permission_owner \
            if isinstance(base_permission_owner, discord.Role) else base_permission_owner.top_role
        target_highest_role: discord.Role = target_permission_owner \
            if isinstance(target_permission_owner, discord.Role) else target_permission_owner.top_role

        if base_highest_role >= interaction.user.top_role or target_highest_role >= interaction.user.top_role:
            await interaction.response.send_message(
                'You cannot duplicate this permission because one of the roles '
                'or members you specified are higher than your own highest role',
                ephemeral=True
            )
            return

        # bot permissions check
        if base_highest_role >= interaction.guild.me.top_role or target_highest_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                'You cannot duplicate this permission because one of the roles '
                'you specified is higher than my highest role',
                ephemeral=True
            )
            return

        try:
            base_overwrites = base_channel.overwrites[base_permission_owner]
        except KeyError:
            await interaction.response.send_message(
                f'{base_permission_owner.mention} does not have permission overwrites '
                f'in {base_channel.mention}',
                ephemeral=True,
                allowed_mentions=AllowedMentions.none()
            )
            return

        try:
            await target_channel.set_permissions(target_permission_owner, overwrite=base_overwrites)
            await interaction.response.send_message(
                f"{base_permission_owner.mention}'s permissions from {base_channel.mention} were applied to"
                f"{target_permission_owner.mention} in {target_channel.mention}",
                ephemeral=True,
                allowed_mentions=AllowedMentions.none()
            )
        except discord.Forbidden as e:
            await interaction.response.send_message(
                f'You do not have permissions to create this overwrite. Error={e}'
            )
            bot_logger.warning(f'Overwrites Duplication Error. Forbidden={e}')
            self.bot.report_command_failure(interaction)
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f'Failed to create overwrite. Error={e}'
            )
            bot_logger.warning(f'Overwrites Duplication Error. HTTPException={e}')
            self.bot.report_command_failure(interaction)
        # these shouldn't be possible - pre-checks failed us somewhere
        except (discord.NotFound, TypeError) as e:
            await interaction.response.send_message(
                f'Failed to create overwrite. Error={e}'
            )
            bot_logger.error(f'Overwrites Duplication Error. NotFound | TypeError={e}')
            self.bot.report_command_failure(interaction)
            await self.bot.report_exception(e)

    # App Commands don't support lists... deferring this for now.
    # @app_commands.checks.has_permissions(manage_roles=True)
    # @app_commands.checks.bot_has_permissions(manage_roles=True)
    # @app_commands.describe(
    #     base_channel='The channel you want to copy permissions from',
    # )
    # @app_dynamic_cooldown()
    # @moderation_subgroup.command(
    #     name='bulk_add_role'
    # )
    # async def bulk_add_roles(
    #         self, interaction: GuildInteraction, role: discord.Role, members: List[discord.Member]
    # ) -> None:
    #     """
    #     A method to bulk add members to a role.
    #
    #     Checks:
    #         has_permissions(manage_roles): Whether the invoking user can manage roles.
    #         bot_has_permissions(manage_roles): Whether the bot can manage roles.
    #
    #     Parameters:
    #         interaction (GuildInteraction): The invoking interaction.
    #         role (discord.Role): The role to add to the members.
    #         members (List[discord.Member]): A list of members to add to the role.
    #
    #     Returns:
    #         None.
    #     """
    #
    #     if role >= interaction.user.top_role or role >= interaction.guild.me.top_role:
    #         await interaction.response.send_message(
    #             'You specified a role equal to or higher than mine or your top role.',
    #             ephemeral=True
    #         )
    #         return
    #
    #     # number of failures allowed before a command failure is reported
    #     unacceptable_failure_threshold = min(max(len(members) // 5 if len(members) >= 3 else len(members), 1), 5)
    #     succeeded, failed = [], []
    #
    #     for member in members:
    #         if member.top_role >= interaction.guild.me.top_role:
    #             failed.append(member.mention)
    #             continue
    #
    #         try:
    #             await member.add_roles(role, reason=f'Bulk Added by {interaction.user}')
    #         except discord.Forbidden as e:
    #             bot_logger.warning(f'Bulk Add Failure. Forbidden={e}')
    #             failed.append(member.mention)
    #         except discord.HTTPException as e:
    #             bot_logger.warning(f'Overwrites Duplication Error. HTTPException={e}')
    #             failed.append(member.mention)
    #         else:
    #             succeeded.append(member.mention)
    #
    #     embed = Embed(
    #         title=f'Bulk Add Summary',
    #         description=f'{len(succeeded):,} Success(es), {len(failed):,} Failure(s).',
    #     )
    #     embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
    #     embed.set_thumbnail(url=interaction.guild.icon.url)
    #     embed.set_footer(text='Please report any formatting issues to my owner!')
    #
    #     if succeeded:
    #         embed.add_field(name='Succeeded', value='\n'.join(succeeded))
    #     if failed:
    #         embed.add_field(name='Failed', value='\n'.join(failed))
    #
    #     if len(failed) > unacceptable_failure_threshold:
    #         self.bot.report_command_failure(interaction)
    #
    #     await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(manage_roles=True)
    @moderation_subgroup.command(
        name='get_default_role',
        description=f'Retrieves the default role for this guild'
    )
    async def get_default_role(self, interaction: GuildInteraction) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            has_guild_permissions(manage_guild): Whether the invoking user can manage the guild.

        Parameters:
            interaction (GuildInteraction): The invoking interaction.

        Returns:
            None.
        """

        default_role_id = self.bot.cache.default_roles.get(interaction.guild_id, None)

        if default_role_id is None:
            await interaction.response.send_message(f'No default role found', ephemeral=True)
            return

        default_role = interaction.guild.get_role(default_role_id)

        if default_role is None:
            await interaction.response.send_message(
                'A default role exists, but I am unable to fetch it. The role may have been deleted.',
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f'The default role is {default_role.mention}',
                ephemeral=True,
                allowed_mentions=AllowedMentions.none()
            )

    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    @app_commands.checks.has_permissions(manage_guild=True, manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @moderation_subgroup.command(
        name='set_default_role',
        description=f'Sets or clears the default role for this guild'
    )
    async def set_default_role(self, interaction: GuildInteraction, role: Optional[discord.Role] = None) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (10) seconds per (Guild).
            has_guild_permissions(manage_guild, manage_roles):
                Whether the invoking user can manage the guild and roles.

        Parameters:
            interaction (GuildInteraction): The invoking interaction.
            role (discord.Role): The role to set as the default role. Could be None.

        Returns:
            None.
        """

        if role is None:
            try:
                await execute_query(
                    self.bot.database,
                    'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                    (interaction.guild_id,)
                )

                with suppress(KeyError):
                    del self.bot.cache.default_roles[interaction.guild_id]

                await ctx.send('Cleared the default role for the guild.')
            except aiosqliteError:
                await ctx.send('Failed to clear the default role for the guild.')
            finally:
                return


        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not role:
            confirmation = await ctx.confirmation_prompt('Are you sure you want to remove the default role?')
            if not confirmation:
                return



        # ensure all roles are fetched
        if all((role, bot_role, invoker_role)):
            # ensure both the bot and the initializing user have the ability to set the role
            if role >= bot_role or role >= invoker_role:
                await ctx.send('Cannot set a default role higher than or equal to the bot\'s or your highest role.')
            else:
                try:
                    await execute_query(
                        self.bot.database,
                        'INSERT INTO DEFAULT_ROLES (GUILD_ID, ROLE_ID) VALUES (?, ?) ON CONFLICT(GUILD_ID) '
                        'DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID',
                        (ctx.guild.id, role.id)
                    )
                    self.bot.cache.default_roles[ctx.guild.id] = role.id

                    await ctx.send(f'Updated the default role to **{role.name}**')
                except aiosqliteError:
                    await ctx.send('Failed to set the default role for the guild.')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a new user joins a guild.

        Functionality:
            If a default role is set, add the default role to the new member.

        Parameters:
            member (discord.Member): The member that joined the guild.

        Returns:
            None.
        """

        if 'MEMBER_VERIFICATION_GATE_ENABLED' in member.guild.features:
            return

        await add_default_role(self.bot, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a member is updated.

        Functionality:
            If a default role is set, add the default role to the new member after membership screening is complete.

        Parameters:
            before (discord.Member): The initial state of the updated member.
            after (discord.Member): The new state of the updated member.

        Returns:
            None.
        """

        if 'MEMBER_VERIFICATION_GATE_ENABLED' in after.guild.features and before.pending and not after.pending:
            await add_default_role(self.bot, after, True)


async def add_default_role(bot: DreamBot, member: discord.Member, gate: bool = False) -> None:
    """
    Adds the default role (if applicable) to a member.

    Parameters:
        bot (DreamBot): The Discord bot.
        member (discord.Member): The member to add the default role to.
        gate (bool): Whether the invocation guild has the `MEMBER_VERIFICATION_GATE_ENABLED` flag.

    Returns:
        None.
    """

    if (
        member.guild.unavailable or
        member.guild.id not in bot.cache.default_roles or
        not member.guild.me.guild_permissions.manage_roles
    ):
        return

    resolved_role = member.guild.get_role(bot.cache.default_roles[member.guild.id])

    if not resolved_role:
        return

    try:
        await member.add_roles(
            resolved_role,
            reason=f'Default Role{" [Membership Screening] " if gate else " "}Assignment'
        )
    except discord.HTTPException as e:
        bot_logger.error(f'Role Addition Failure. {e.status}. {e.text}')

        if sys_channel := member.guild.system_channel:
            try:
                await sys_channel.send(f'Failed to add the default role to `{str(member)}`.')
            except discord.HTTPException as e:
                bot_logger.error(f'Role Addition Alert Failure. {e.status}. {e.text}')


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Moderation(bot))
    bot_logger.info('Completed Setup for Cog: Moderation')
