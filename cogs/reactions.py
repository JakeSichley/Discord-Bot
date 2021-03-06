from discord.ext import commands
from asyncio import TimeoutError
from utils import execute_query, retrieve_query, GuildConverter, cleanup
from typing import Union, Optional
import discord


class UserInputReceived(Exception):
    """
    Error raised when a user supplies valid input. Used as a double break.
    """

    pass


class ReactionRoles(commands.Cog):
    """
    A Cogs class that implements reaction roles.

    Attributes:
        bot (commands.Bot): The Discord bot.
    """

    def __init__(self, bot):
        """
        The constructor for the ReactionRoles class.

        Parameters:
            bot (commands.Bot): The Discord bot.
        """

        self.bot = bot

    @commands.group(name='reactionrole', aliases=['rr', 'reactionroles'])
    async def reaction_role(self, ctx: commands.Context) -> None:
        """
        Parent command that handles the reaction role commands.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('reactionrole')

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='add', help='Begins the process of setting up a Reaction Role.\nYou can invoke this '
                                            'command without any arguments to go through the entire setup process.\n'
                                            'Alternatively, you can pass just a message ID, or both a message ID and a '
                                            'role name or role ID. If you choose to pass a role name, you need to quote'
                                            ' the role name in order for it to be properly parsed ("my role").\nYou can'
                                            ' also use this method to change the role of an existing reaction. Specify'
                                            ' the same message and reaction and simply supply a new role!')
    async def add_reaction_role(self, ctx: commands.Context, message: discord.Message = None,
                                role: discord.Role = None) -> None:
        """
        Adds a reaction role to a specified message.

        Parameters:
            ctx (commands.Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.
            role: (discord.Role): The role to grant/remove when a user reacts. Could be None.

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

        if not message:
            cleanup_messages.append(await ctx.send('Please specify the message you want to set up Reaction Roles for!'
                                                   '\nYou can right click on a message and send either the Message ID '
                                                   'or you can also send the entire Message Link!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a message object
                    try:
                        message = await commands.MessageConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a message from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the message is from this guild (full message link check)
        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            raise commands.UserInputError

        # reaction role setup should have the base message. Check role properties now.
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

        # reaction role setup should have the base message and a role
        # if the user passed in a role at the start, check the hierarchy
        reaction_message = await ctx.send('Please specify the reaction you want to set up Reaction Roles for!'
                                          '\nYou can react to this message with the reaction!')
        cleanup_messages.append(reaction_message)

        def reaction_check(pl: discord.RawReactionActionEvent):
            if pl.event_type == 'REACTION_REMOVE':
                return
            return pl.message_id == reaction_message.id and pl.member == ctx.author

        # wrap the entire operation in a try -> break this with timeout
        try:
            payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)
            # try to add the reaction the base message
            try:
                await message.add_reaction(payload.emoji)
            except discord.HTTPException:
                cleanup_messages.append(await ctx.send("I wasn't able to add the reaction to the base message. If you"
                                                       " have not already done so, please add the reaction for me!"))
        except TimeoutError:
            await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
            return await cleanup(cleanup_messages, ctx.channel)

        # we should have all pieces for a reaction role now
        await execute_query(self.bot.DATABASE_NAME,
                            'INSERT INTO REACTION_ROLES (GUILD_ID, CHANNEL_ID, MESSAGE_ID, REACTION, ROLE_ID) '
                            'VALUES (?, ?, ?, ?, ?) '
                            'ON CONFLICT(MESSAGE_ID, REACTION) DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID',
                            (message.guild.id, message.channel.id, message.id, str(payload.emoji), role.id))
        await ctx.send(f"Awesome! Whenever a user reacts to the message {message.jump_url} with the reaction "
                       f"{payload.emoji}, I'll assign them the **{role.name}** role!")
        await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='remove', help='Begins the process of removing an existing Reaction Role.\nIf you '
                                               'invoke this command without a supplying a message, you will be '
                                               'prompted for one.\nIf you wish to change the role associated with a '
                                               'specific reaction, consider using "add" instead!\nIf you wish to '
                                               'remove all reaction roles from a message, consider using "clear" '
                                               'instead!')
    async def remove_reaction_role(self, ctx: commands.Context, message: discord.Message = None) -> None:
        """
        Removes a reaction role from a specified message.

        Parameters:
            ctx (commands.Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        if not message:
            cleanup_messages.append(await ctx.send('Please specify the message you want to remove a Reaction Role for!'
                                                   '\nYou can right click on a message and send either the Message ID '
                                                   'or you can also send the entire Message Link!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a message object
                    try:
                        message = await commands.MessageConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a message from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the message is from this guild (full message link check)
        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            raise commands.UserInputError

        # once we have a message id, proceed with deletion confirmation
        if roles := await retrieve_query(self.bot.DATABASE_NAME,
                                         'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                         'WHERE MESSAGE_ID=?', (message.id,)):
            # give the user a display of potential options
            details = f'Reaction Roles for Message: <https://discordapp.com/channels/' \
                      f'{ctx.guild.id}/{roles[0][2]}/{message.id}>\n'

            for pair in roles:
                role_name = ctx.guild.get_role(pair[1])
                details += ('\t' * 2) + f'{pair[0]} {role_name if role_name else "Invalid Role"}\n'

            details += '\nReact to this message with the reaction you would like to remove!'

            # add the details message to the cleanup list
            breakdown = await ctx.send(details)
            cleanup_messages.append(breakdown)

            # build a list of reactions and add all of them to the breakdown message
            reactions = [x[0] for x in roles]
            for reaction in reactions:
                try:
                    await breakdown.add_reaction(reaction)
                except discord.DiscordException:
                    pass

            # make sure the reaction is added to the correct message and the reaction is added by our author
            def reaction_check(pl: discord.RawReactionActionEvent):
                if pl.event_type == 'REACTION_REMOVE':
                    return
                return pl.message_id == breakdown.id and pl.member == ctx.author

            try:
                # confirm that the user wants to remove the reaction role from the specified message
                payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)

                if str(payload.emoji) in reactions:
                    await execute_query(self.bot.DATABASE_NAME,
                                        'DELETE FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                        (message.id, str(payload.emoji)))
                    # try to remove the deleted reaction
                    try:
                        await message.remove_reaction(payload.emoji, ctx.me)
                    except discord.HTTPException:
                        pass

                    await ctx.send('Removed the specified reaction role from the message.')
                else:
                    raise commands.BadArgument

            # if the user reacts with the wrong reaction doesn't react at all, cancel the command
            except (commands.BadArgument, TimeoutError):
                await ctx.send('Aborting reaction role removal.')
        else:
            await ctx.send('Could not find any reaction roles associated with the specified message.')

        await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='clear', help='Begins the process of removing an existing Reaction Role.\nIf you invoke'
                                              ' this command without a supplying a message, you will be prompted for'
                                              ' one.\nIf you wish to remove only a single reaction role, consider'
                                              ' using "remove" instead!')
    async def clear_reaction_roles(self, ctx: commands.Context, message: discord.Message = None) -> None:
        """
        Clears all reaction roles from a specified message.

        Parameters:
            ctx (commands.Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        if not message:
            cleanup_messages.append(await ctx.send('Please specify the message you want to clear Reaction Roles for!'
                                                   '\nYou can right click on a message and send either the Message ID '
                                                   'or you can also send the entire Message Link!'))

            def message_check(m):
                return m.author == ctx.author

            # wrap the entire operation in a try -> break this with timeout
            try:
                # give the user multiple attempts to pass a valid argument
                while True:
                    # wait for them to respond
                    response = await self.bot.wait_for('message', timeout=30.0, check=message_check)
                    # try to convert their response to a message object
                    try:
                        message = await commands.MessageConverter().convert(ctx, response.content)
                        raise UserInputReceived
                    except (commands.CommandError, commands.BadArgument):
                        cleanup_messages.append(await ctx.send("I wasn't able to extract a message from your response."
                                                               " Please try again!"))
            except TimeoutError:
                await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
                return await cleanup(cleanup_messages, ctx.channel)
            except UserInputReceived:
                pass

        # check to make sure the message is from this guild (full message link check)
        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            raise commands.UserInputError

        # once we have a message id, proceed with deletion confirmation
        if roles := await retrieve_query(self.bot.DATABASE_NAME,
                                         'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                         'WHERE MESSAGE_ID=?', (message.id,)):
            response = await ctx.send(f'Are you sure want to remove **{len(roles)}** reaction roles from '
                                      f'<https://discordapp.com/channels/{ctx.guild.id}/{roles[0][2]}/{message.id}>? '
                                      f'This cannot be undone. If you wish to proceed, react to this message with ✅.')
            cleanup_messages.append(response)

            # make sure the reaction is added to the correct message and the reaction is added by our author
            def reaction_check(pl: discord.RawReactionActionEvent):
                if pl.event_type == 'REACTION_REMOVE':
                    return
                return pl.message_id == response.id and pl.member == ctx.author

            try:
                # confirm that the user wants to remove all the reaction roles from the specified message
                await response.add_reaction('✅')
                # wait for the user to respond with the checkmark
                payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)

                if str(payload.emoji) == '✅':
                    await execute_query(self.bot.DATABASE_NAME,
                                        'DELETE FROM REACTION_ROLES WHERE MESSAGE_ID=?', (message.id,))
                    # try to remove the respective reactions
                    for reaction in message.reactions:
                        if reaction.me:
                            try:
                                await message.remove_reaction(reaction, ctx.me)
                            except discord.HTTPException:
                                pass
                    await ctx.send('Removed all reaction roles from the specified message.')
                else:
                    raise commands.BadArgument

            # if the user reacts with the wrong reaction or doesn't react at all, cancel the command
            except (commands.BadArgument, TimeoutError):
                await ctx.send('Aborting reaction role removal.')
        else:
            await ctx.send('Could not find any reaction roles associated with the specified message.')

        await cleanup(cleanup_messages, ctx.channel)

    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='check', help='Generates a breakdown of reaction roles for the given scope. Valid '
                                              'scopes: Guild, Channel, Message.')
    async def check_reaction_roles(self, ctx: commands.Context,
                                   source: Union[GuildConverter, discord.TextChannel, discord.Message] = None) -> None:
        """
        Generates a breakdown of reaction roles for the given scope. Valid scopes: Guild, Channel, Message.
        This method defines sub-methods that generate a breakdown for their given scopes.
        Scopes higher in the hierarchy (Guild > Channel > Message) recursively call lower scopes until the entire
            specified scope has been filled out.

        Parameters:
            ctx (commands.Context): The invocation context.
            source (Union[discord.Guild, discord.TextChannel, discord.Message]):
                The scope for which a reaction role breakdown should be generated.

        Returns:
            None.
        """

        async def message_selection(message_id: int, indent_level: int = 0) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified message.

            Parameters:
                message_id (int): The ID of the message to generate a breakdown for.
                indent_level (int): The amount of whitespace to pad this breakdown with. Default: 0.

            Returns:
                details (Optional[str]): Details about the reaction roles of the message if possible. Could be None.
            """

            if roles := await retrieve_query(self.bot.DATABASE_NAME,
                                             'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                             'WHERE MESSAGE_ID=?', (message_id,)):
                details = ('\t' * indent_level) + f'Reaction Roles for **Message:** <https://discordapp.com/channels/' \
                                                  f'{ctx.guild.id}/{roles[0][2]}/{message_id}>\n'

                for pair in roles:
                    role_name = ctx.guild.get_role(pair[1])
                    details += ('\t' * (indent_level + 2)) + f'{pair[0]} {role_name if role_name else "Invalid Role"}\n'

                return details
            else:
                return None

        async def channel_selection(channel_id: int, indent_level: int = 0) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified channel.

            Parameters:
                channel_id (int): The ID of the channel to generate a breakdown for.
                indent_level (int): The amount of whitespace to pad this breakdown with. Default: 0.

            Returns:
                details (Optional[str]): Details about the reaction roles of the channel if possible. Could be None.
            """

            if messages := await retrieve_query(self.bot.DATABASE_NAME,
                                                'SELECT DISTINCT MESSAGE_ID FROM REACTION_ROLES WHERE CHANNEL_ID=?',
                                                (channel_id,)):
                details = ('\t' * indent_level) + f'Reaction Roles for **Channel:** <#{channel_id}>\n'

                for message in messages:
                    message_details = await message_selection(message[0], indent_level + 1)
                    details += ('\t' * indent_level) + message_details + '\n' if message_details is not None else 'None'

                return details
            else:
                return None

        async def guild_selection(guild_id: int) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified guild.

            Parameters:
                guild_id (int): The ID of the guild to generate a breakdown for.

            Returns:
                details (Optional[str]): Details about the reaction roles of the guild if possible. Could be None.
            """

            if channels := await retrieve_query(self.bot.DATABASE_NAME,
                                                'SELECT DISTINCT CHANNEL_ID FROM REACTION_ROLES WHERE GUILD_ID=?',
                                                (guild_id,)):
                details = f'Reaction Roles for **Guild: {ctx.guild.name}**\n'

                for channel in channels:
                    channel_details = await channel_selection(channel[0], 1)
                    details += channel_details if channel_details is not None else 'None'

                return details
            else:
                return None

        # invoke the proper sub-method based on our source type
        if isinstance(source, discord.Message):
            # check to make sure the message is from this guild (full message link check)
            if source.guild.id != ctx.guild.id:
                await ctx.send("That message doesn't belong to this guild.")
                raise commands.UserInputError
            breakdown = await message_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified message.')
        elif isinstance(source, discord.TextChannel):
            breakdown = await channel_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified channel.')
        elif isinstance(source, discord.Guild):
            breakdown = await guild_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified guild.')
        else:
            await ctx.send("Invalid object was passed - couldn't fetch reaction roles.\n"
                           "```Messages: If the message is in the channel, you can pass the Message ID. If the message "
                           "is in another channel, you can pass the Channel-Message ID (shift-click on 'Copy ID'). "
                           "Otherwise, passing the entire message link works.\n"
                           "Channels: You can pass the Channel ID, Channel Name, or mention the channel.\n"
                           "Guilds: You can pass the Guild ID or Guild Name.```")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is added.
        'raw' events fire regardless of whether or not a message is cached.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        if payload.user_id == self.bot.user.id:
            return

        if role_id := await retrieve_query(self.bot.DATABASE_NAME,
                                           'SELECT ROLE_ID FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                           (payload.message_id, str(payload.emoji))):
            # if there's a role for the given message + reaction, attempt to fetch the guild
            if guild := self.bot.get_guild(payload.guild_id):
                # if we fetched the guild, try to fetch the member and the role
                role = guild.get_role(role_id[0][0])
                member = guild.get_member(payload.user_id)
                # if we fetched all our prerequisites, attempt to add the role to the member
                if role and member:
                    try:
                        await member.add_roles(role, reason=f'Reaction Roles [MESSAGE ID: {payload.message_id}]')
                    except discord.HTTPException:
                        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is removed.
        'raw' events fire regardless of whether or not a message is cached.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Returns:
            None.
        """

        if payload.user_id == self.bot.user.id:
            return

        if role_id := await retrieve_query(self.bot.DATABASE_NAME,
                                           'SELECT ROLE_ID FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                           (payload.message_id, str(payload.emoji))):
            # if there's a role for the given message + reaction, attempt to fetch the guild
            if guild := self.bot.get_guild(payload.guild_id):
                # if we fetched the guild, try to fetch the member and the role
                role = guild.get_role(role_id[0][0])
                member = guild.get_member(payload.user_id)
                # if we fetched all our prerequisites, attempt to remove the role from the member
                if role and member:
                    try:
                        await member.remove_roles(role, reason=f'Reaction Roles [MESSAGE ID: {payload.message_id}]')
                    except discord.HTTPException:
                        pass

# todo: add note about raw ids only working in the same channel
# todo: improve reaction remove/add checks


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(ReactionRoles(bot))
    print('Completed Setup for Cog: Reactions')
