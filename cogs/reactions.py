from discord.ext import commands
from asyncio import TimeoutError
from utils import execute_query, retrieve_query, GuildConverter
from typing import Union, Optional
import discord


class UserInputReceived(Exception):
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
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot

    @commands.has_permissions(manage_roles=True)
    @commands.command(name='rrcheck', aliases=['rrc'])
    async def check_reaction_roles(self, ctx: commands.Context):
        #roles = await retrieve_query(self.bot.DATABASE_NAME, 'SELECT REFROM REACTION_ROLES WHERE MESSAGE_ID=?',
        #                             (message.id,))
        #print(roles)
        def reaction_check(pl: discord.RawReactionActionEvent):
            if pl.event_type == 'REACTION_REMOVE':
                return
            return pl.message_id == ctx.message.id and pl.member == ctx.author

        await ctx.send('Waiting', delete_after=5)
        # wrap the entire operation in a try -> break this with timeout
        payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)
        print(payload.emoji)
        print(type(str(payload.emoji)))
        await execute_query(self.bot.DATABASE_NAME, 'INSERT INTO EMOJIS VALUES (?)', (str(payload.emoji),))

    @commands.has_permissions(manage_roles=True)
    @commands.command(name='rrall')
    async def all_reaction_roles(self, ctx: commands.Context,
                                 source: Union[GuildConverter, discord.TextChannel, discord.Message]):

        async def message_selection(message_id: int) -> Optional[str]:
            if roles := await retrieve_query(self.bot.DATABASE_NAME,
                                             'SELECT REACTION, ROLE_ID FROM REACTION_ROLES WHERE MESSAGE_ID=?',
                                             (message_id,)):
                details = f'**Reaction Roles for Message: {message_id}**\n'

                for pair in roles:
                    role_name = ctx.guild.get_role(pair[1])
                    details += f'\n{pair[0]} **{role_name if role_name else "Invalid Role"}**'

                return details
            else:
                return None

        async def channel_selection(channel_id: int) -> Optional[str]:
            if messages := await retrieve_query(self.bot.DATABASE_NAME,
                                                'SELECT DISTINCT MESSAGE_ID FROM REACTION_ROLES WHERE CHANNEL_ID=?',
                                                (channel_id,)):
                details = f'**Reaction Roles for Channel: {channel_id}**\n'

                for message in messages:
                    message_details = await message_selection(message[0])
                    details += '\n' + message_details if message_details is not None else 'None'

                return details
            else:
                return None

        async def guild_selection(guild_id: int) -> Optional[str]:
            if channels := await retrieve_query(self.bot.DATABASE_NAME,
                                                'SELECT DISTINCT CHANNEL_ID FROM REACTION_ROLES WHERE GUILD_ID=?',
                                                (guild_id,)):
                details = f'**Reaction Roles for Guild: {guild_id}**\n'

                for channel in channels:
                    channel_details = await channel_selection(channel[0])
                    details += '\n' + channel_details if channel_details is not None else 'None'

                return details
            else:
                return None

        if isinstance(source, discord.Message):
            breakdown = await message_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified message.')
        elif isinstance(source, discord.TextChannel):
            breakdown = await channel_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified channel.')
        elif isinstance(source, discord.Guild):
            breakdown = await guild_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified guild.')
        else:
            await ctx.send("Invalid object was passed - couldn't fetch reaction roles.")

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @commands.command(name='rradd', aliases=['rra'])
    async def add_reaction_role(self, ctx: commands.Context, message: discord.Message = None,
                                role: discord.Role = None) -> None:
        cleanup_messages = []

        # cleanup our prompt messages once we've timed out or completed setup
        async def cleanup():
            try:
                await ctx.channel.delete_messages(cleanup_messages)
            except discord.Forbidden:
                for msg in cleanup_messages:
                    to_delete = msg
                    await to_delete.delete()
            except discord.DiscordException:
                pass

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
                return await cleanup()
            except UserInputReceived:
                pass

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
                    # try to convert their response to a message object
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
                return await cleanup()
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
            return await cleanup()

        # we should have all pieces for a reaction role now
        await execute_query(self.bot.DATABASE_NAME,
                            'INSERT INTO REACTION_ROLES (GUILD_ID, CHANNEL_ID, MESSAGE_ID, REACTION, ROLE_ID) '
                            'VALUES (?, ?, ?, ?, ?) '
                            'ON CONFLICT(MESSAGE_ID, REACTION) DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID',
                            (message.guild.id, message.channel.id, message.id, str(payload.emoji), role.id))
        await ctx.send(f"Awesome! Whenever a user reacts to the message {message.jump_url} with the reaction "
                       f"{payload.emoji}, I'll assign them the **{role.name}** role!")
        await cleanup()

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
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
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
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                # if we fetched the guild, try to fetch the member and the role
                role = guild.get_role(role_id[0][0])
                member = guild.get_member(payload.user_id)
                # if we fetched all our prerequisites, attempt to remove the role from the member
                if role and member:
                    try:
                        await member.remove_roles(role, reason=f'Reaction Roles [MESSAGE ID: {payload.message_id}]')
                    except discord.HTTPException:
                        pass


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(ReactionRoles(bot))
    print('Completed Setup for Cog: Reactions')
