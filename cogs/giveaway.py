from discord.ext import commands
import discord
import datetime
import random


class Giveaway(commands.Cog):
    """
    A Cogs class that contains commands for implementing giveaways.

    Attributes:
        bot (commands.Bot): The Discord bot class.
    """

    def __init__(self, bot):
        """
        The constructor for the Giveaway class.

        Parameters:
            bot (commands.Bot): The Discord bot.
        """

        self.bot = bot

    @commands.group(name='giveaway', aliases=['g'])
    async def giveaway(self, ctx: commands.Context) -> None:
        """
        Parent command that handles the giveaway commands.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('giveaway')

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @giveaway.command(name='start', help='Begins the process of hosting a giveaway.')
    async def start_giveaway(self, ctx, channel: discord.TextChannel, title, prize, end_date: int, image = None):
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether or not the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether or not the bot can manage messages
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
        if channel:
            time = datetime.datetime.fromtimestamp(end_date)
            embed = discord.Embed(title=title, color=0x00bbff)
            if image:
                embed.set_thumbnail(url=image)
            embed.description = 'React with 🎉 to enter!'
            embed.add_field(name='Prize', value=prize, inline=False)
            embed.add_field(name='Hosted By', value=ctx.author.mention, inline=False)
            embed.add_field(name='End Date', value=time.strftime('%I:%M %p on %A, %B %d, %Y'), inline=False)
            message = await channel.send(content='🎊   **GIVEAWAY**   🎊', embed=embed)
            await message.add_reaction('🎉')

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @giveaway.command(name='end', help='Selects a winner of a giveaway.')
    async def end_giveaway(self, ctx, message: discord.Message, remove = False):
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether or not the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether or not the bot can manage messages
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
        if message:
            users = None
            for reaction in message.reactions:
                if reaction.me:
                    users = await reaction.users().flatten()

            if users:
                users = [user for user in users if not user.bot]
                winner = random.choice(users)

                embed = discord.Embed(title=':confetti_ball: Giveaway Winner! :confetti_ball:', color=0x00bbff)
                embed.add_field(name='Winner', value=winner.mention, inline=False)
                embed.add_field(name='Source', value=message.jump_url, inline=False)
                embed.set_footer(text='Thanks to everyone who participated!')
                await message.channel.send(embed=embed)

                if remove:
                    await message.remove_reaction('🎉', winner)


def setup(bot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Giveaway(bot))
    print('Completed Setup for Cog: Giveaway')
