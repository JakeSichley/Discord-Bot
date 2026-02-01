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
from typing import Union, Optional, Literal, TYPE_CHECKING

from aiosqlite import Error as aiosqliteError
from discord import (
    Role, Member, TextChannel, CategoryChannel, VoiceChannel, Thread, StageChannel, HTTPException, AllowedMentions
)
from discord.ext import commands

from utils.converters import AggressiveDefaultMemberConverter
from utils.database.helpers import execute_query, typed_retrieve_query
from utils.observability.loggers import bot_logger

if TYPE_CHECKING:
    from dreambot import DreamBot
    from utils.context import Context

CHANNEL_OBJECT = Union[TextChannel, CategoryChannel, VoiceChannel]
PERMISSIONS_PARENT = Union[Role, Member]
PURGEABLE_INSTANCES = (StageChannel, TextChannel, Thread, VoiceChannel)
PURGEABLE_TYPE = Union[StageChannel, TextChannel, Thread, VoiceChannel]


class Moderation(commands.Cog):
    """
    A Cogs class that contains commands for moderating a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: 'DreamBot') -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    async def cog_check(self, ctx: 'Context') -> bool:  # type: ignore[override]
        """
        A method that registers a cog-wide check.
        Requires these commands be used in a guild only.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the command was invoked in a guild.
        """

        return ctx.guild is not None

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True, manage_channels=True)
    @commands.command(
        name='purge',
        help='Purges n+1 messages from the current channel. Specify `all` to completely clear the channel.'
    )
    async def purge(self, ctx: 'Context', limit: Union[int, Literal['all']]) -> None:
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether the bot can manage messages
                and read the message history of a channel, both of which are required for the deletion of messages.

        Parameters:
            ctx (Context): The invocation context.
            limit (Union[int, Literal['all']]): The number of messages to purge.

        Returns:
            None.
        """

        if not isinstance(ctx.channel, PURGEABLE_INSTANCES):
            return

        if isinstance(limit, int) and limit <= 0:
            return

        prompt = f'Are you sure you want to delete {limit} message(s)?'
        if (limit == 'all' or limit >= 10) and not await ctx.confirmation_prompt(prompt):
            return

        if isinstance(limit, int):
            await ctx.channel.purge(limit=limit + 1)
            return

        if isinstance(ctx.channel, Thread):
            await ctx.channel.purge(limit=ctx.channel.message_count + 1)
        else:
            position = ctx.channel.position
            new_channel = await ctx.channel.clone(reason=f'Full channel purge; executed by {ctx.author}')
            await ctx.channel.delete(reason=f'Full channel purge; executed by {ctx.author}')
            await new_channel.edit(position=position)

    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.command(name='duplicate_permissions', aliases=['dp'])
    async def duplicate_channel_permissions(
            self, ctx: 'Context', base_channel: CHANNEL_OBJECT, base_permission_owner: PERMISSIONS_PARENT,
            target_channel: CHANNEL_OBJECT, target_permission_owner: PERMISSIONS_PARENT
    ) -> None:
        """
        A method to duplicate channel permissions to a different target.

        Checks:
            has_guild_permissions(manage_channels)
            bot_has_guild_permissions(manage_channels)

        Parameters:
            ctx (Context): The invocation context.
            base_channel (Union[TextChannel, CategoryChannel, VoiceChannel]): The base channel
                to source permissions from.
            base_permission_owner (Union[Role, Member]): The role or member whose permissions should
                be copied.
            target_channel (Union[TextChannel, CategoryChannel, VoiceChannel]): The target
                channel to duplicate permissions to.
            target_permission_owner (Union[Role, Member]): The role or member the permissions should be
                copied to.

        Returns:
            None.
        """

        try:
            base_overwrites = base_channel.overwrites[base_permission_owner]
        except KeyError:
            await ctx.send("Overwrites object was not found")
            return

        try:
            await target_channel.set_permissions(target_permission_owner, overwrite=base_overwrites)
            await ctx.send(f"**{base_channel.name}**[`{base_permission_owner}`] --> "
                           f"**{target_channel.name}**[`{target_permission_owner}`]")
        except Exception as e:
            bot_logger.error(f'Overwrites Duplication Error. {e}')
            await ctx.send(f'Failed to duplicate overwrites ({e})')

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='bulkadd', enabled=False)
    async def bulk_add_roles(self, ctx: 'Context', role: Role, *, members: str) -> None:
        """
        Special Note:
            If you are passing strictly IDs or Name#Discriminator arguments, these arguments can be seperated by only
            a space. If you are mixing IDs, Name#Discriminator, and nickname arguments, arguments must be seperated
            by a newline to ensure proper matching.

        A method to bulk add a role to members.
        Uses a special converter that aggressively attempts to match arguments.

        Checks:
            has_permissions(manage_roles): Whether the invoking user can manage roles.
            bot_has_permissions(manage_roles): Whether the bot can manage roles.

        Parameters:
            ctx (Context): The invocation context.
            role (Role): The role to add to the members.
            members (str): A variadic argument representing the members to add the role to.

        Returns:
            None.
        """

        assert isinstance(ctx.me, Member)  # guild only
        assert isinstance(ctx.author, Member)  # guild only

        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not all((bot_role, invoker_role, role)):
            await ctx.send("Couldn't retrieve top roles for myself or you. Please try the command again.")
            return
        if role >= bot_role or role >= invoker_role:
            await ctx.send('You specified a role equal to or higher than mine or your top role.')
            return

        async with ctx.typing():
            matches = findall(r'(?<=<@!)?(?<=<@)?[0-9]{15,19}(?=>)?|\S.{1,31}?#[0-9]{4}', members)
            remaining = sub(r'(<@!)?(<@)?[0-9]{15,19}>?|\S.{1,31}?#[0-9]{4}', '', members)
            potential_members = matches + [x for x in remaining.split('\n') if x and x.strip()]
            converted = [await AggressiveDefaultMemberConverter().convert(ctx, member) for member in potential_members]

            success, failed = [], []

            for member in converted:
                if isinstance(member, Member):
                    try:
                        await member.add_roles(role, reason=f'Bulk Added by {str(ctx.author)}')
                    except HTTPException:
                        failed.append(str(member))
                    else:
                        success.append(str(member))
                else:
                    failed.append(str(member))

            summary = f'Successfully added {role.mention} to the following members:\n' \
                      f'```{", ".join(success) if success else "None"}```\n'

            if failed:
                summary += f'Failed to add {role.mention} to the following members:\n```{", ".join(failed)}```'

            await ctx.send(summary, allowed_mentions=AllowedMentions.none())

    @commands.has_guild_permissions(manage_roles=True)
    @commands.command(name='getdefaultrole', aliases=['gdr'],
                      help='Displays the role (if any) users are auto-granted on joining the guild.')
    async def get_default_role(self, ctx: 'Context') -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            has_guild_permissions(manage_guild): Whether the invoking user can manage the guild.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            A message detailing the default role for the guild.

        Returns:
            None.
        """

        assert ctx.guild is not None  # guild only

        if role := (await typed_retrieve_query(
                self.bot.database,
                int,
                'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                (ctx.guild.id,))
        ):
            if fetched_role := ctx.guild.get_role(role[0]):
                await ctx.send(f'The default role for the server is **{fetched_role.name}**')
            else:
                await ctx.send(f'The default role for the server has id `{role}`, but I was unable to fetch it.')
        else:
            await ctx.send(f'There is no default role set for the server.')

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='setdefaultrole', aliases=['sdr'],
                      help='Sets the role users are auto-granted on joining.'
                           '\nTo remove the default role, simply call this command without passing a role.'
                           '\nNote: The role selected must be lower than the bot\'s role and lower than your role.')
    async def set_default_role(self, ctx: 'Context', role: Optional[Role] = None) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (10) seconds per (Guild).
            has_guild_permissions(manage_guild, manage_roles):
                Whether the invoking user can manage the guild and roles.

        Parameters:
            ctx (Context): The invocation context.
            role (Role): The role to set as the default role. Could be None.

        Output:
            Success: A confirmation message detailing the new default role.
            Failure: An error message detailing why the command failed.

        Returns:
            None.
        """

        assert isinstance(ctx.me, Member)  # guild only
        assert isinstance(ctx.author, Member)  # guild only
        assert ctx.guild is not None  # guild only

        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not role:
            confirmation = await ctx.confirmation_prompt('Are you sure you want to remove the default role?')
            if not confirmation:
                return

            try:
                await execute_query(self.bot.database, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?', (ctx.guild.id,))

                with suppress(KeyError):
                    del self.bot.cache.default_roles[ctx.guild.id]

                await ctx.send('Cleared the default role for the guild.')
            except aiosqliteError:
                await ctx.send('Failed to clear the default role for the guild.')
            finally:
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
    async def on_member_join(self, member: Member) -> None:
        """
        A commands.Cog listener event that is called whenever a new user joins a guild.

        Functionality:
            If a default role is set, add the default role to the new member.

        Parameters:
            member (Member): The member that joined the guild.

        Returns:
            None.
        """

        if 'MEMBER_VERIFICATION_GATE_ENABLED' in member.guild.features:
            return

        await add_default_role(self.bot, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        """
        A commands.Cog listener event that is called whenever a member is updated.

        Functionality:
            If a default role is set, add the default role to the new member after membership screening is complete.

        Parameters:
            before (Member): The initial state of the updated member.
            after (Member): The new state of the updated member.

        Returns:
            None.
        """

        if 'MEMBER_VERIFICATION_GATE_ENABLED' in after.guild.features and before.pending and not after.pending:
            await add_default_role(self.bot, after, True)


async def add_default_role(bot: 'DreamBot', member: Member, gate: bool = False) -> None:
    """
    Adds the default role (if applicable) to a member.

    Parameters:
        bot (DreamBot): The Discord bot.
        member (Member): The member to add the default role to.
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
    except HTTPException as e:
        bot_logger.error(f'Role Addition Failure. {e.status}. {e.text}')

        if sys_channel := member.guild.system_channel:
            try:
                await sys_channel.send(f'Failed to add the default role to `{str(member)}`.')
            except HTTPException as e:
                bot_logger.error(f'Role Addition Alert Failure. {e.status}. {e.text}')


async def setup(bot: 'DreamBot') -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Moderation(bot))
    bot_logger.info('Completed Setup for Cog: Moderation')
