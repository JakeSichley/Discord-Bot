from discord.ext import commands
from asyncio import TimeoutError
from utils.database_utils import exists_query, execute_query, retrieve_query
from utils.utils import cleanup
from asyncio import sleep
from typing import List, Tuple, Optional
from dreambot import DreamBot
import discord


class VoiceRoles(commands.Cog):
    """
    A Cogs class that implements voice roles.

    Attributes:
        bot (DreamBot): The Discord bot.
        recently_changed (List[int]): A list of member id's that have recently had their voice state modified.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the ReactionRoles class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.recently_changed = []

    @commands.group(name='voicerole', aliases=['vr', 'voiceroles'])
    async def voice_role(self, ctx: commands.Context) -> None:
        """
        Parent command that handles the reaction role commands.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('voicerole')

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @voice_role.command(name='add', help='Begins the process of setting up a Voice Role.\nYou can invoke this command '
                                         'without any arguments to go through the entire setup process.\nAlternatively,'
                                         ' you can pass just a voice channel ID, or both a voice channel ID and a role'
                                         ' name or role ID. If you choose to pass a role name, you need to quote the'
                                         ' role name in order for it to be properly parsed ("my role").\nYou can also'
                                         ' use this method to change the role of an existing voice role channel.'
                                         ' Specify the same channel and simply supply a new role!')
    async def add_voice_role(self, ctx: commands.Context, channel: discord.VoiceChannel = None,
                             role: discord.Role = None) -> None:
        """
        Adds a voice role to a specified channel.

        Parameters:
            ctx (commands.Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.
            role: (discord.Role): The role to grant/remove when a user joins/leaves the channel. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        # check these properties early to try to avoid wasting the user's time
        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not all((bot_role, invoker_role)):
            await ctx.send("Couldn't retrieve top roles for myself or you. Please try the command again.")
            return

        if not channel:
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx)

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
            messages, role = await prompt_user_for_role(self.bot, ctx, bot_role, invoker_role)
            cleanup_messages.extend(messages)

            if not role:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif role.guild.id != role.guild.id:
                await ctx.send("That role doesn't belong to this guild.")
                return

        # we should have all pieces for a reaction role now
        # perform an EXISTS query first since pi doesn't support ON_CONFLICT
        if (await exists_query(self.bot.database, 'SELECT EXISTS(SELECT 1 FROM VOICE_ROLES WHERE CHANNEL_ID=?)',
                               (channel.id,))):
            await execute_query(self.bot.database, 'UPDATE VOICE_ROLES SET ROLE_ID=? WHERE CHANNEL_ID=?',
                                (role.id, channel.id))
        else:
            await execute_query(self.bot.database, 'INSERT INTO VOICE_ROLES (GUILD_ID, CHANNEL_ID, ROLE_ID) '
                                                   'VALUES (?, ?, ?)',
                                (channel.guild.id, channel.id, role.id))

        await ctx.send(f"Awesome! Whenever a user joins **{channel.name}**, I'll assign them the **{role.name}** role!")
        await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @voice_role.command(name='remove', help='Begins the process of removing an existing Voice Role.\nIf you invoke this'
                                            ' command without a supplying a channel, you will be prompted for one.\nIf'
                                            ' you wish to change the role associated with a specific channel, consider'
                                            ' using "add" instead!')
    async def remove_voice_role(self, ctx: commands.Context, channel: discord.VoiceChannel = None) -> None:
        """
        Removes a voice role from a specified channel.

        Parameters:
            ctx (commands.Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.

        Returns:
            None.
        """

        if not channel:
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx)

            if not channel:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif channel.guild.id != ctx.guild.id:
                await ctx.send("That channel doesn't belong to this guild.")
                return

        # once we have a channel id, proceed with deletion confirmation
        if role := await retrieve_query(self.bot.database,
                                        'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                        (channel.id,)):
            role = ctx.guild.get_role(role[0])

            if not role:
                await ctx.send('Channel or Role data could not be fetched. Deleting invalid voice role.')
            else:
                await ctx.send(f'Deleted the voice role **{role.name}** from channel **{channel.name}**.')

            await execute_query(self.bot.database,
                                'DELETE FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                (channel.id,))

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

    @commands.has_permissions(manage_roles=True)
    @voice_role.command(name='check', help='Checks a channel for an existing voice role.')
    async def check_voice_role(self, ctx: commands.Context, channel: discord.VoiceChannel = None) -> None:
        """
        Checks for a voice role for a specified channel.

        Parameters:
            ctx (commands.Context): The invocation context.
            channel (discord.VoiceChannel): The base channel for the voice role. Could be None.

        Returns:
            None.
        """

        if not channel:
            cleanup_messages, channel = await prompt_user_for_voice_channel(self.bot, ctx)

            if not channel:
                await cleanup(cleanup_messages, ctx.channel)
                return
            elif channel.guild.id != ctx.guild.id:
                await ctx.send("That channel doesn't belong to this guild.")
                return

        # once we have a channel id, check to see if a role exists
        if role := await retrieve_query(self.bot.database,
                                        'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                        (channel.id,)):
            role = ctx.guild.get_role(role[0])

            if not role:
                await ctx.send(f'There is currently an invalid role associated with the channel **{channel.name}**.')
            else:
                await ctx.send(f'**{role.name}** will be assigned to members who join **{channel.name}**.')

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        """
        A listener method that is called whenever a VoiceState is modified.

        Parameters:
            member (discord.Member): The member whose voice state was updated.
            before (discord.VoiceState): Not used.
            after (discord.VoiceState): The updated voice state for the member.

        Output:
            None.

        Returns:
            None.
        """

        if member.bot:
            return

        self.recently_changed.append(member.id)
        await sleep(3)
        if self.recently_changed.count(member.id) > 1:
            self.recently_changed.remove(member.id)
            return
        else:
            self.recently_changed.remove(member.id)

        if data := await retrieve_query(self.bot.database,
                                        'SELECT CHANNEL_ID, ROLE_ID FROM VOICE_ROLES WHERE GUILD_ID=?',
                                        (member.guild.id,)):
            # if there's a roles for the given guild, update according
            if after.channel:
                # if we fetched the guild, begin updating roles
                remove_roles = []
                add_role = None
                for channel_id, role_id in data:
                    if channel_id != after.channel.id:
                        remove_roles.append(member.guild.get_role(role_id))
                    else:
                        add_role = member.guild.get_role(role_id)

                if add_role:
                    try:
                        await member.add_roles(add_role, reason=f'Reaction Roles [CHANNEL ID: {after.channel.id}]')
                    except discord.HTTPException:
                        pass

                if remove_roles:
                    try:
                        await member.remove_roles(*remove_roles,
                                                  reason=f'Reaction Roles [CHANNEL ID: {after.channel.id}]')
                    except discord.HTTPException:
                        pass

            else:
                remove_roles = []
                for channel_id, role_id in data:
                    remove_roles.append(member.guild.get_role(role_id))

                if remove_roles:
                    try:
                        await member.remove_roles(*remove_roles,
                                                  reason=f'Reaction Roles [DISCONNECT]')
                    except discord.HTTPException:
                        pass


async def prompt_user_for_voice_channel(
        bot: DreamBot, ctx: commands.Context
) -> Tuple[List[discord.Message], Optional[discord.VoiceChannel]]:
    """
    A method to fetch a discord.VoiceChannel from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (commands.Context): The invocation context.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.VoiceChannel]]
    """

    sent_messages = [
        await ctx.send('Please specify the channel you want to remove a Voice Role for!\nYou can right click on a '
                       'channel and send either the Channel ID or you can also send the quoted name '
                       '("My Voice Channel")!')
    ]

    # noinspection PyMissingOrEmptyDocstring
    def message_check(m):
        return m.author == ctx.author

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for('message', timeout=30.0, check=message_check)
            # try to convert their response to a VoiceChannel object
            try:
                channel = await commands.VoiceChannelConverter().convert(ctx, response.content)
                return sent_messages, channel
            except (commands.CommandError, commands.BadArgument):
                sent_messages.append(
                    await ctx.send("I wasn't able to extract a channel from your response. Please try again!")
                )
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None


async def prompt_user_for_role(
        bot: DreamBot, ctx: commands.Context, bot_role: discord.Role, author_role: discord.Role
) -> Tuple[List[discord.Message], Optional[discord.Role]]:
    """
    A method to fetch a discord.Role from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (commands.Context): The invocation context.
        bot_role (commands.Role): The bot's role in the invocation server.
        author_role (commands.Role): The author's role in the invocation server.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.Role]]
    """
    sent_messages = [
        await ctx.send('Please specify the role you want to set up Reaction Roles for!'
                       '\nYou can send the Role Name, Role ID, or even mention the Role!')
    ]

    # noinspection PyMissingOrEmptyDocstring
    def message_check(m):
        return m.author == ctx.author

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for('message', timeout=30.0, check=message_check)
            # try to convert their response to a role object
            try:
                role = await commands.RoleConverter().convert(ctx, response.content)
                if role >= bot_role or role >= author_role or role.is_default():
                    raise commands.UserInputError
                else:
                    return sent_messages, role
            except commands.BadArgument:
                sent_messages.append(await ctx.send("I wasn't able to extract a role from your response. "
                                                    "Please try again!"))
            except commands.UserInputError:
                sent_messages.append(await ctx.send("You cannot specify a role higher than or equal to mine "
                                                    "or your top role! Please specify another role!"))
            except commands.CommandError:
                sent_messages.append(await ctx.send("I wasn't able to extract a role from your response. "
                                                    "Please try again!"))
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(VoiceRoles(bot))
    print('Completed Setup for Cog: VoiceRoles')
