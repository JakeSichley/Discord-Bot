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

from asyncio import sleep
from typing import List, Optional

import discord
from aiosqlite import Error as aiosqliteError
from cache import ExpiringCache  # type: ignore
from discord.ext import commands

from dreambot import DreamBot
from utils.context import Context
from utils.database.helpers import execute_query, typed_retrieve_query
from utils.database.table_dataclasses import VoiceRole
from utils.logging_formatter import bot_logger
from utils.prompts import prompt_user_for_voice_channel, prompt_user_for_role
from utils.utils import cleanup


class VoiceRoles(commands.Cog):
    """
    A Cogs class that implements voice roles.

    Constants:
        CACHE_TTL (int): The expiring cache's time to live (in seconds).

    Attributes:
        bot (DreamBot): The Discord bot.
        cache (ExpiringCache): An expiring cache of member id's that have recently had their voice state modified.
    """

    CACHE_TTL = 3

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the ReactionRoles class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.cache = ExpiringCache(self.CACHE_TTL)

    @commands.guild_only()
    @commands.group(name='voicerole', aliases=['vr', 'voiceroles'])
    async def voice_role(self, ctx: Context) -> None:
        """
        Parent command that handles the reaction role commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('voicerole')

    @commands.bot_has_permissions(manage_roles=True)  # type: ignore[arg-type]
    @commands.has_permissions(manage_roles=True)
    @voice_role.command(name='add', help='Begins the process of setting up a Voice Role.\nYou can invoke this command '
                                         'without any arguments to go through the entire setup process.\nAlternatively,'
                                         ' you can pass just a voice channel ID, or both a voice channel ID and a role'
                                         ' name or role ID. If you choose to pass a role name, you need to quote the'
                                         ' role name in order for it to be properly parsed ("my role").\nYou can also'
                                         ' use this method to change the role of an existing voice role channel.'
                                         ' Specify the same channel and simply supply a new role!')
    async def add_voice_role(
            self, ctx: Context, channel: Optional[discord.VoiceChannel] = None, role: Optional[discord.Role] = None
    ) -> None:
        """
        Adds a voice role to a specified channel.

        Parameters:
            ctx (Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.
            role: (discord.Role): The role to grant/remove when a user joins/leaves the channel. Could be None.

        Returns:
            None.
        """

        assert isinstance(ctx.me, discord.Member)  # guild only
        assert isinstance(ctx.author, discord.Member)  # guild only
        assert ctx.guild is not None

        cleanup_messages: List[discord.Message] = []

        # check these properties early to try to avoid wasting the user's time
        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not all((bot_role, invoker_role)):
            await ctx.send("Couldn't retrieve top roles for myself or you. Please try the command again.")
            return

        if not channel:
            initial_message = 'Please specify the channel you want to add a Voice Role for!\nYou can right click ' \
                              'on a channel and send either the Channel ID or you can also send the quoted name ' \
                              '("My Voice Channel")!'
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx, initial_message)

            if not channel:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif channel.guild.id != ctx.guild.id:
                await ctx.send("That channel doesn't belong to this guild.")
                return

        # voice role setup should have the base channel. Check role properties now.
        # if the user passed in a role at the start, check the hierarchy
        if role and (role >= bot_role or role >= invoker_role):
            cleanup_messages.append(await ctx.send("You specified a role equal to or higher than mine or your top role."
                                                   " Please select a role we both have permission to add!"))
            role = None

        if not role:
            initial_message = 'Please specify the role you want to set up Reaction Roles for!' \
                              '\nYou can send the Role Name, Role ID, or even mention the Role!'
            messages, role = await prompt_user_for_role(self.bot, ctx, bot_role, invoker_role, initial_message)
            cleanup_messages.extend(messages)

            if not role:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif role.guild.id != role.guild.id:
                await ctx.send("That role doesn't belong to this guild.")
                return

        # we should have all pieces for a reaction role now
        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO VOICE_ROLES (GUILD_ID, CHANNEL_ID, ROLE_ID) VALUES (?, ?, ?) '
                'ON CONFLICT(CHANNEL_ID) DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID',
                (channel.guild.id, channel.id, role.id)
            )
            self.bot.cache.voice_roles[channel.guild.id].append(VoiceRole(channel.guild.id, channel.id, role.id))

            await ctx.send(
                f"Awesome! Whenever a user joins **{channel.name}**, I'll assign them the **{role.name}** role!"
            )

        except aiosqliteError:
            await ctx.send('Failed to create/update the specified voice role.')

        finally:
            await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)  # type: ignore[arg-type]
    @commands.has_permissions(manage_roles=True)
    @voice_role.command(name='remove', help='Begins the process of removing an existing Voice Role.\nIf you invoke this'
                                            ' command without a supplying a channel, you will be prompted for one.\nIf'
                                            ' you wish to change the role associated with a specific channel, consider'
                                            ' using "add" instead!')
    async def remove_voice_role(self, ctx: Context, channel: Optional[discord.VoiceChannel] = None) -> None:
        """
        Removes a voice role from a specified channel.

        Parameters:
            ctx (Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.

        Returns:
            None.
        """

        assert ctx.guild is not None

        if not channel:
            initial_message = 'Please specify the channel you want to remove a Voice Role for!\nYou can right click ' \
                              'on a channel and send either the Channel ID or you can also send the quoted name ' \
                              '("My Voice Channel")!'
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx, initial_message)

            if not channel:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif channel.guild.id != ctx.guild.id:
                await ctx.send("That channel doesn't belong to this guild.")
                return

        # once we have a channel id, proceed with deletion confirmation
        if role := await typed_retrieve_query(
                self.bot.database,
                int,
                'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                (channel.id,)
        ):
            fetched_role = ctx.guild.get_role(role[0])

            if not fetched_role:
                await ctx.send('Channel or Role data could not be fetched. Deleting invalid voice role.')
            else:
                await ctx.send(f'Deleted the voice role **{fetched_role.name}** from channel **{channel.name}**.')

            try:
                await execute_query(
                    self.bot.database,
                    'DELETE FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                    (channel.id,)
                )

                existing_roles = self.bot.cache.voice_roles[ctx.guild.id]
                self.bot.cache.voice_roles[ctx.guild.id] = [x for x in existing_roles if x.channel_id != channel.id]

            except aiosqliteError:
                pass

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

    @commands.has_permissions(manage_roles=True)  # type: ignore[arg-type]
    @voice_role.command(name='check', help='Checks a channel for an existing voice role.')
    async def check_voice_role(self, ctx: Context, channel: Optional[discord.VoiceChannel] = None) -> None:
        """
        Checks for a voice role for a specified channel.

        Parameters:
            ctx (Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.

        Returns:
            None.
        """

        assert ctx.guild is not None

        if not channel:
            initial_message = 'Please specify the channel you want to check a Voice Role for!\nYou can right click ' \
                              'on a channel and send either the Channel ID or you can also send the quoted name ' \
                              '("My Voice Channel")!'
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx, initial_message)

            if not channel:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif channel.guild.id != ctx.guild.id:
                await ctx.send("That channel doesn't belong to this guild.")
                return

        # once we have a channel id, check to see if a role exists
        if role := await typed_retrieve_query(
                self.bot.database,
                int,
                'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                (channel.id,)
        ):
            fetched_role = ctx.guild.get_role(role[0])

            if not fetched_role:
                await ctx.send(f'There is currently an invalid role associated with the channel **{channel.name}**.')
            else:
                await ctx.send(f'**{fetched_role.name}** will be assigned to members who join **{channel.name}**.')

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """
        A listener method that is called whenever a VoiceState is modified.

        Parameters:
            member (discord.Member): The member whose voice state was updated.
            before (discord.VoiceState): Not used.
            after (discord.VoiceState): The updated voice state for the member.

        Returns:
            None.
        """

        # todo: guild / role unavailability checks

        # insert the guild, member key into our expiring cache
        # after our cache ttl, if the key is still valid, the user is still moving channels
        # otherwise, we can proceed
        self.cache[member.guild.id, member.id] = None  # value is irrelevant for our purposes

        await sleep(self.CACHE_TTL + 0.1)

        if (member.guild.id, member.id) in self.cache:
            return

        # compile a list of valid VoiceRole::Role ID's for the current guild
        local_roles = [x.role_id for x in self.bot.cache.voice_roles[member.guild.id]]

        # keep every role that isn't a VoiceRole
        updated_roles = [x for x in member.roles if x.id not in local_roles]
        if not after.channel:
            # if the user does not have a voice state, updated_roles is already finished
            reason = f'Voice Roles - Disconnect'
        else:
            # otherwise, resolve the relevant VoiceRole
            add_role = [
                member.guild.get_role(x.role_id)
                for x in self.bot.cache.voice_roles[member.guild.id]
                if x.channel_id == after.channel.id
            ]

            # both add_role and this list comprehensive should have len == 1 which don't require lists, but using lists
            # prevents a double-nested if
            updated_roles.extend([x for x in add_role if x])
            reason = f'Voice Roles - Join [Channel ID: {after.channel.id} ("{after.channel.name}")]'

        try:
            await member.edit(roles=updated_roles, reason=reason)
        except discord.HTTPException as e:
            bot_logger.error(f'Voice Role - Role Edit Error. {e.status}. {e.text}')


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(VoiceRoles(bot))
    bot_logger.info('Completed Setup for Cog: VoiceRoles')
