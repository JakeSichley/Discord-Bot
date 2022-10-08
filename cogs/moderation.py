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

from discord.ext import commands
from utils.database.helpers import execute_query, retrieve_query
from typing import Union
from dreambot import DreamBot
from utils.converters import AggressiveDefaultMemberConverter
from aiosqlite import Error as aiosqliteError
from utils.context import Context
from re import findall, sub
from utils.logging_formatter import bot_logger
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
    async def purge(self, ctx: Context, limit: int = 0, user: discord.Member = None):
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether the bot can manage messages
                and read the message history of a channel, both of which are required for the deletion of messages.

        Parameters:
            ctx (Context): The invocation context.
            limit (int): The number of messages to purge. Default: 0.
            user (discord.User): The User to delete messages from. Default: None.

        Output:
            None.

        Returns:
            None.
        """

        if limit > 10:
            if not await ctx.confirmation_prompt(f'Are you sure you want to delete {limit} messages?'):
                return

        if user is None:
            await ctx.channel.purge(limit=limit + 1)
        else:
            await ctx.channel.purge(limit=limit + 1, check=lambda m: m.author == user)

    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.command(name='duplicate_permissions', aliases=['dp'])
    async def duplicate_channel_permissions(
            self, ctx: Context, base_channel: CHANNEL_OBJECT, base_permission_owner: PERMISSIONS_PARENT,
            target_channel: CHANNEL_OBJECT, target_permission_owner: PERMISSIONS_PARENT
    ) -> None:
        """
        A method to duplicate channel permissions to a different target.

        Checks:
            has_guild_permissions(manage_channels)
            bot_has_guild_permissions(manage_channels)

        Parameters:
            ctx (Context): The invocation context.
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
            bot_logger.error(f'Overwrites Duplication Error. {e}')
            await ctx.send(f"Failed to duplicate overwrites ({e})")

    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='bulkadd')
    async def bulk_add_roles(self, ctx: Context, role: discord.Role, *, members: str) -> None:
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
            role (discord.Role): The role to add to the members.
            members (str): A variadic argument representing the members to add the role to.

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

        async with ctx.typing():
            matches = findall(r'(?<=<@!)?(?<=<@)?[0-9]{15,19}(?=>)?|\S.{1,31}?#[0-9]{4}', members)
            remaining = sub(r'(<@!)?(<@)?[0-9]{15,19}>?|\S.{1,31}?#[0-9]{4}', '', members)
            potential_members = matches + [x for x in remaining.split('\n') if x and x.strip()]
            converted = [await AggressiveDefaultMemberConverter().convert(ctx, member) for member in potential_members]

            success, failed = [], []

            for member in converted:
                if isinstance(member, discord.Member):
                    try:
                        await member.add_roles(role, reason=f'Bulk Added by {str(ctx.author)}')
                    except discord.HTTPException:
                        failed.append(str(member))
                    else:
                        success.append(str(member))
                else:
                    failed.append(str(member))

            summary = f'Successfully added {role.mention} to the following members:\n'\
                      f'```{", ".join(success) if success else "None"}```\n'

            if failed:
                summary += f'Failed to add {role.mention} to the following members:\n```{", ".join(failed)}```'

            await ctx.send(summary, allowed_mentions=discord.AllowedMentions.none())

    @commands.has_guild_permissions(manage_roles=True)
    @commands.command(name='getdefaultrole', aliases=['gdr'],
                      help='Displays the role (if any) users are auto-granted on joining the guild.')
    async def get_default_role(self, ctx: Context) -> None:
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

        if role := (await retrieve_query(self.bot.connection, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
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
    async def set_default_role(self, ctx: Context, role: discord.Role = None) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (10) seconds per (Guild).
            has_guild_permissions(manage_guild, manage_roles):
                Whether the invoking user can manage the guild and roles.

        Parameters:
            ctx (Context): The invocation context.
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
                await execute_query(self.bot.connection, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?', (ctx.guild.id,))
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
                        self.bot.connection,
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

        if role := (await retrieve_query(self.bot.connection, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (member.guild.id,))):
            role = member.guild.get_role(role[0][0])

            try:
                await member.add_roles(role, reason='Default Role Assignment')
            except discord.HTTPException as e:
                bot_logger.error(f'Role Addition Failure. {e.status}. {e.text}')
                await execute_query(self.bot.connection, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?',
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
            if role := (await retrieve_query(self.bot.connection, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                             (after.guild.id,))):
                role = after.guild.get_role(role[0][0])

                try:
                    await after.add_roles(role, reason='Default Role [Membership Screening] Assignment')
                except discord.HTTPException as e:
                    bot_logger.error(f'Role Addition Failure. {e.status}. {e.text}')
                    try:
                        await after.guild.system_channel.send(f'Failed to add the default role to `{str(after)}`.')
                    except discord.HTTPException:
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
