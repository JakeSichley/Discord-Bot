"""
MIT License

Copyright (c) 2021 Jake Sichley

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

from discord.ext import commands
from utils.database_utils import execute_query, retrieve_query
from typing import Union
from dreambot import DreamBot
from utils.converters import DefaultMemberConverter
from aiosqlite import Error as aiosqliteError
import discord

CHANNEL_OBJECT = Union[discord.TextChannel, discord.CategoryChannel, discord.VoiceChannel]
PERMISSIONS_PARENT = Union[discord.Role, discord.Member]


class Moderation(commands.Cog):
    """
    A Cogs class that contains commands for moderating a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command(name='purge', help='Purges n+1 messages from the current channel. If a user is supplied, the bot '
                                         'will purge any message from that user in the last n messages.')
    async def purge(self, ctx: commands.Context, limit: int = 0, user: discord.Member = None):
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether the bot can manage messages
                and read the message history of a channel, both of which are required for the deletion of messages.

        Parameters:
            ctx (commands.Context): The invocation context.
            limit (int): The number of messages to purge. Default: 0.
            user (discord.User): The User to delete messages from. Default: None.

        Output:
            None.

        Returns:
            None.
        """

        if user is None:
            await ctx.channel.purge(limit=limit + 1)
        else:
            # noinspection PyMissingOrEmptyDocstring
            def purge_check(message):
                return message.author.id == user.id

            await ctx.channel.purge(limit=limit + 1, check=purge_check)

    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.command(name='duplicate_permissions', aliases=['dp'])
    async def duplicate_channel_permissions(
            self, ctx: commands.Context, base_channel: CHANNEL_OBJECT, base_permission_owner: PERMISSIONS_PARENT,
            target_channel: CHANNEL_OBJECT, target_permission_owner: PERMISSIONS_PARENT
    ) -> None:
        """
        A method to duplicate channel permissions to a different target.

        Checks:
            has_guild_permissions(manage_channels)
            bot_has_guild_permissions(manage_channels)

        Parameters:
            ctx (commands.Context): The invocation context.
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
            await ctx.send(f"Failed to duplicate overwrites ({e})")

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='bulkadd', help='Adds a specified role to a large number of users at once.')
    async def bulk_add_roles(self, ctx: commands.Context, role: discord.Role, *members: DefaultMemberConverter):
        """
        A method to bulk add a role to members.
        Uses a special converter that attempts to remove whitespace errors and defaults to returning the member's name
            if conversion fails.

        Checks:
            has_permissions(manage_roles): Whether the invoking user can manage roles.
            bot_has_permissions(manage_roles): Whether the bot can manage roles.

        Parameters:
            ctx (commands.Context): The invocation context.
            role (discord.Role): The role to add to the members.
            *members (discord.Member): A variadic argument representing the members to add the role to.

        Returns:
            None.
        """

        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not all((bot_role, invoker_role, role)):
            await ctx.send("Couldn't retrieve top roles for myself or you. Please try the command again.")
            return
        if role >= bot_role or role >= invoker_role:
            await ctx.send('You specified a role equal to or higher than mine or your top role.')
            return

        success, failed = [], []
        for member in members:
            try:
                # noinspection PyUnresolvedReferences
                await member.add_roles(role, reason=f'Bulk Added by {str(ctx.author)}')
                success.append(str(member))
            # since we used a special converter that returns the member's name (as a str) if conversation fails,
            # type 'str' won't have an add_roles method
            except (discord.HTTPException, AttributeError):
                failed.append(str(member))

        await ctx.send(f'Successfully added the role to the following members:\n'
                       f'```{", ".join(success) if success else "None"}```\n'
                       f'Failed to add the role to the following members:\n'
                       f'```{", ".join(failed) if failed else "None"}```')

    @commands.has_guild_permissions(manage_roles=True)
    @commands.command(name='getdefaultrole', aliases=['gdr'],
                      help='Displays the role (if any) users are auto-granted on joining the guild.')
    async def get_default_role(self, ctx: commands.Context) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            has_guild_permissions(manage_guild): Whether the invoking user can manage the guild.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            A message detailing the default role for the guild.

        Returns:
            None.
        """

        if role := (await retrieve_query(self.bot.database, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (ctx.guild.id,))):
            role = ctx.guild.get_role(role[0][0])
            await ctx.send(f'The default role for the server is **{role.name}**')
        else:
            await ctx.send(f'There is no default role set for the server.')

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='setdefaultrole', aliases=['sdr'],
                      help='Sets the role users are auto-granted on joining.'
                           '\nTo remove the default role, simply call this command without passing a role.'
                           '\nNote: The role selected must be lower than the bot\'s role and lower than your role.')
    async def set_default_role(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (10) seconds per (Guild).
            has_guild_permissions(manage_guild, manage_roles):
                Whether the invoking user can manage the guild and roles.

        Parameters:
            ctx (commands.Context): The invocation context.
            role (discord.Role): The role to set as the default role. Could be None.

        Output:
            Success: A confirmation message detailing the new default role.
            Failure: An error message detailing why the command failed.

        Returns:
            None.
        """

        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not role:
            try:
                await execute_query(self.bot.database, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?', (ctx.guild.id,))
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

        if role := (await retrieve_query(self.bot.database, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (member.guild.id,))):
            role = member.guild.get_role(role[0][0])

            try:
                await member.add_roles(role, reason='Default Role Assignment')
            except discord.HTTPException:
                await execute_query(self.bot.database, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                    (member.guild.id,))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
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
            if role := (await retrieve_query(self.bot.database, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                             (after.guild.id,))):
                role = after.guild.get_role(role[0][0])

                try:
                    await after.add_roles(role, reason='Default Role [Membership Screening] Assignment')
                except discord.HTTPException:
                    try:
                        await after.guild.system_channel.send(f'Failed to add the default role to `{str(after)}`.')
                    except discord.HTTPException:
                        pass


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Moderation(bot))
    print('Completed Setup for Cog: Moderation')
