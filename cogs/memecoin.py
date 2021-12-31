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
from discord import Embed, HTTPException
from utils.database_utils import execute_query, retrieve_query
from utils.checks import check_memecoin_channel
from typing import Optional
from dreambot import DreamBot
from utils.context import Context
import discord


class MemeCoin(commands.Cog):
    """
    A Cogs class that implements a fake currency system for memes.

    Attributes:
        bot (DreamBot): The Discord bot class.
        channel (int: discord.TextChannel) The id of the channel where MemeCoin can be used.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the MemeCoin class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.channel = 636356259255287808

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is added.
        'raw' events fire regardless of whether a message is cached.
        Requirements listed in check_coin_requirements() must be met to proceed.
        Meme Coin records are stored in the database.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        if not (author_id := await check_coin_requirements(self.bot, payload, self.channel)):
            return

        if str(payload.emoji) == '✅':
            value = 1
        elif str(payload.emoji) == '❌':
            value = -1
        else:
            return

        await execute_query(
            self.bot.database,
            'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?) '
            'ON CONFLICT(USER_ID) DO UPDATE SET COINS=COINS+EXCLUDED.COINS',
            (author_id, value)
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is removed.
        'raw' events fire regardless of whether a message is cached.
        Requirements listed in check_coin_requirements() must be met to proceed.
        Meme Coin records are stored in the database.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        if not (author_id := await check_coin_requirements(self.bot, payload, self.channel)):
            return

        if str(payload.emoji) == '✅':
            value = -1
        elif str(payload.emoji) == '❌':
            value = 1
        else:
            return

        await execute_query(
            self.bot.database,
            'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?) '
            'ON CONFLICT(USER_ID) DO UPDATE SET COINS=COINS+EXCLUDED.COINS',
            (author_id, value)
        )

    @check_memecoin_channel()
    @commands.command(name='coins', help='Checks you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx: Context) -> None:
        """
        A method that outputs the number of Meme Coins a user currently owns.

        Checks:
            check_memecoin_channel(): Whether the command is invoked in the proper channel.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            Success: The number of coins the user currently owns.
            Failure: An error message.

        Returns:
            None.
        """

        result = await retrieve_query(self.bot.database, 'SELECT COINS FROM MEMECOIN WHERE USER_ID=?',
                                      (ctx.author.id,))
        if result:
            await ctx.send(f'{ctx.author.mention}, you have {result[0][0]} Meme Coin(s)!')
        else:
            await ctx.send(f'{ctx.author.mention}, you have no Meme Coins :(')

    @commands.cooldown(1, 300)
    @check_memecoin_channel()
    @commands.command(name='leaderboard', help='Displays a list of highest rollers in Meme Coin Town!',
                      aliases=['leaderboards'])
    async def leaderboard(self, ctx: Context) -> None:
        """
        A method that outputs an embed, detailing the top and bottom Meme Coin owners.

        Checks:
            cooldown(): Whether the command is on cooldown. Can be used (1) time per (5) minutes.
            check_memecoin_channel(): Whether the command is invoked in the proper channel.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            Success: An embed with (at most) the top and bottom 5 Meme Coin owners.
            Failure: Nothing.

        Returns:
            None.
        """

        embed = Embed(title="Meme Coin Leaderboards",
                      description="Whose Meme Coins stash reigns supreme?!\n", color=0xffff00)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.add_field(name='\u200B', value='\u200B')
        embed.add_field(name='\u200B', value='\u200B')
        embed.add_field(name='\u200B', value='\u200B')
        embed.set_footer(text="Please report any issues to my owner!")

        result = await retrieve_query(self.bot.database, 'SELECT * FROM MEMECOIN')

        if len(result) > 0:
            top_scores = sorted(result, key=lambda x: x[1], reverse=True)
            formatted_scores = []
            # Check each entry in the sorted list of scores
            for tup in top_scores:
                user = self.bot.get_user(tup[0])
                # If the user is visible to the bot, add them to the embed
                if user is not None:
                    formatted_scores.append(user.name + ': ' + str(tup[1]))

            most = formatted_scores[:5]
            least = (formatted_scores[::-1])[:5]

            embed.add_field(name='Most Coins', value='\n'.join(most))
            embed.add_field(name='Least Coins', value='\n'.join(least))
        else:
            embed.add_field(name='No Current Meme Coin Owners!',
                            value='Please give or revoke Meme Coin to construct leaderboards!')

        await ctx.send(embed=embed)


async def check_coin_requirements(
        bot: commands.Bot, payload: discord.RawReactionActionEvent, memecoin_channel: int
) -> Optional[int]:
    """
    A method that checks whether an event is eligible for Meme Coins.
    Returns None if requirements are not met.

    Requirements:
        Check to make sure the message comes from the appropriate channel
        Check to make sure the user adding the reaction isn't a bot
        Check to make sure the user adding the reaction isn't adding it to their own message
        Check to make sure the reaction isn't being added to a bot's message
        Check to make sure the message has either an attachment or a link

    Parameters:
        bot (DreamBot): The Discord bot class.
        payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.
        memecoin_channel (int): The ID of the Meme Coin channel.

    Returns:
        (int): If the requirements have been met - the original message's author id. Else: None.
    """

    # get the original message: fetch channel -> fetch message
    try:
        original_channel = bot.get_channel(payload.channel_id)
        original_message = await original_channel.fetch_message(payload.message_id)
        reaction_author = bot.get_user(payload.user_id)
        message_author = original_message.author

        # if we failed to fetch any of our prerequisites, return false
        if not all((original_channel, original_message, reaction_author, message_author)):
            return None

    except HTTPException as e:
        print(f'Check Coin Requirements Error: {e}')
        return None

    if reaction_author.bot or message_author.bot:
        return None
    if not (original_message.content.find('http') != -1 or len(original_message.attachments) > 0):
        return None
    if original_channel.id != memecoin_channel:
        return None
    if reaction_author.id == message_author.id:
        return None
    return message_author.id


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(MemeCoin(bot))
    print('Completed Setup for Cog: MemeCoin')
