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
from utils.context import Context
from dreambot import DreamBot
import logging


class LostArk(commands.Cog):
    """
    A Cogs class that contains Lost Ark commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the LostArk class.

        Parameters:
           bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='split', aliases=['loot', 'auction'],
                      help='Calculates the maximum worthwhile bidding price for an auction item.')
    async def loot_auction_split(self, ctx: Context, market_price: int, party_size: int = 4) -> None:
        """
        A method to calculate the bidding breakpoint for a loot auction item in Lost Ark.
        The bidding breakpoint is the value where bidding makes you more money than you would receive from the split.
        You should continue to bid while the next minimum bid is less than this value.

        Parameters:
            ctx (Context): The invocation context.
            market_price (int): The current market price for the auction item.
            party_size (int): The number of members in the party. Use 4 for regular parties and 8 for raids.

        Formula:
            .95cp / (1 + .95p) > x where c = market price and p = party size

        Returns:
            None.
        """

        party_size -= 1  # split does not include winning bidder

        bidding_breakpoint = int((.95 * market_price * party_size) / (1 + .95 * party_size))

        await ctx.send(f'For an item with a market value of {"{:,}".format(market_price)} and a party size '
                       f'of {party_size + 1}, you should continue to bid while the next minimum bid price is less than '
                       f'**{"{:,}".format(bidding_breakpoint)}**.')


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(LostArk(bot))
    logging.info('Completed Setup for Cog: Lost Ark')
