from discord.ext import commands
from asyncio import TimeoutError
from utils import exists_query, execute_query, retrieve_query, cleanup
from asyncio import sleep
from typing import List
import discord


class UserInputReceived(Exception):
    """
    Error raised when a user supplies valid input. Used as a double break.
    """

    pass


class VoiceRoles(commands.Cog):
    """
    A Cogs class that implements voice roles.

    Attributes:
        bot (commands.Bot): The Discord bot.
        recently_changed (List[int]): A list of member id's that have recently had their voice state modified.
    """

    def __init__(self, bot):
        """
        The constructor for the ReactionRoles class.

        Parameters:
            bot (commands.Bot): The Discord bot.
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
            cleanup_messages.append(await ctx.send('Please specify the voice channel you want to set up Voice Roles for'
                                                   '!\nYou can right click on a channel and send either the Channel ID '
                                                   'or you can also send the quoted name ("My Voice Channel")!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a VoiceChannel object
                    try:
                        channel = await commands.VoiceChannelConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a channel from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the channel is from this guild (convert should fail, but just to be safe)
        if channel.guild.id != ctx.guild.id:
            await ctx.send("That channel doesn't belong to this guild.")
            raise commands.UserInputError

        # voice role setup should have the base channel. Check role properties now.
        # if the user passed in a role at the start, check the hierarchy
        if role and (role >= bot_role or role >= invoker_role):
            cleanup_messages.append(await ctx.send("You specified a role equal to or higher than mine or your top role."
                                                   " Please select a role we both have permission to add!"))
            role = None

        if not role:
            cleanup_messages.append(await ctx.send('Please specify the role you want to set up Reaction Roles for!'
                                                   '\nYou can send the Role Name, Role ID, or even mention the Role!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a role object
                    try:
                        role = await commands.RoleConverter().convert(ctx, response.content)
                        if role >= bot_role or role >= invoker_role or role.is_default():
                            raise commands.UserInputError
                        else:
                            raise UserInputReceived
                    except commands.BadArgument:
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a role from your response."
                                                               " Please try again!"))
                    except commands.UserInputError:
                        cleanup_messages.append(await ctx.send("You cannot specify a role higher than or equal to mine"
                                                               " or your top role! Please specify another role!"))
                    except commands.CommandError:
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a role from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # we should have all pieces for a reaction role now
        # perform an EXISTS query first since pi doesn't support ON_CONFLICT
        if (await exists_query(self.bot.DATABASE_NAME, 'SELECT EXISTS(SELECT 1 FROM VOICE_ROLES WHERE CHANNEL_ID=?)',
                               (channel.id,))):
            await execute_query(self.bot.DATABASE_NAME, 'UPDATE VOICE_ROLES SET ROLE_ID=? WHERE CHANNEL_ID=?',
                                (role.id, channel.id))
        else:
            await execute_query(self.bot.DATABASE_NAME, 'INSERT INTO VOICE_ROLES (GUILD_ID, CHANNEL_ID, ROLE_ID) '
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

        cleanup_messages = []

        if not channel:
            cleanup_messages.append(await ctx.send('Please specify the channel you want to remove a Voice Role for'
                                                   '!\nYou can right click on a channel and send either the Channel ID '
                                                   'or you can also send the quoted name ("My Voice Channel")!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a VoiceChannel object
                    try:
                        channel = await commands.VoiceChannelConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a channel from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the channel is from this guild (convert should fail, but just to be safe)
        if channel.guild.id != ctx.guild.id:
            await ctx.send("That channel doesn't belong to this guild.")
            raise commands.UserInputError

        # once we have a channel id, proceed with deletion confirmation
        if role := await retrieve_query(self.bot.DATABASE_NAME,
                                        'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                        (channel.id,)):
            role = ctx.guild.get_role(role[0])

            if not role:
                await ctx.send('Channel or Role data could not be fetched. Deleting invalid voice role.')
            else:
                await ctx.send(f'Deleted the voice role **{role.name}** from channel **{channel.name}**.')

            await execute_query(self.bot.DATABASE_NAME,
                                'DELETE FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                (channel.id,))

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

        await cleanup(cleanup_messages, ctx.channel)

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

        cleanup_messages = []

        if not channel:
            cleanup_messages.append(await ctx.send('Please specify the channel you want to remove a Voice Role for'
                                                   '!\nYou can right click on a channel and send either the Channel ID '
                                                   'or you can also send the quoted name ("My Voice Channel")!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a VoiceChannel object
                    try:
                        channel = await commands.VoiceChannelConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a channel from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the channel is from this guild (convert should fail, but just to be safe)
        if channel.guild.id != ctx.guild.id:
            await ctx.send("That channel doesn't belong to this guild.")
            raise commands.UserInputError

        # once we have a channel id, check to see if a role exists
        if role := await retrieve_query(self.bot.DATABASE_NAME,
                                        'SELECT ROLE_ID FROM VOICE_ROLES WHERE CHANNEL_ID=?',
                                        (channel.id,)):
            role = ctx.guild.get_role(role[0])

            if not role:
                await ctx.send(f'There is currently an invalid role associated with the channel **{channel.name}**.')
            else:
                await ctx.send(f'**{role.name}** will be assigned to members who join **{channel.name}**.')

        else:
            await ctx.send('Could not find any voice roles associated with the specified channel.')

        await cleanup(cleanup_messages, ctx.channel)

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        """
        A listener method that is called whenever a VoiceState is modified.

        Parameters:
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

        """
        internal structure that stores members and voice states (channel, id, something)
        after x seconds, count occurrences of member
            if count > 1, do nothing
            else, proceed with role update
        remove occurrence
        """

        self.recently_changed.append(member.id)
        await sleep(3)
        if self.recently_changed.count(member.id) > 1:
            self.recently_changed.remove(member.id)
            return
        else:
            self.recently_changed.remove(member.id)

        if data := await retrieve_query(self.bot.DATABASE_NAME,
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


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(VoiceRoles(bot))
    print('Completed Setup for Cog: VoiceRoles')
