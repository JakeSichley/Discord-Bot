import discord
from discord.ext import commands


class MemeCoin(commands.Cog):
    def __init__(self, bot):
        print('Cog Added')
        self.bot = bot
        self.channel = 618847896305139722
        self.coins = {}

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        if reaction.message.channel.id == self.channel and not user.bot and not reaction.message.author.bot:
            if str(reaction) == '✅':
                if reaction.message.author not in self.coins:
                    self.coins[reaction.message.author] = 1
                else:
                    self.coins[reaction.message.author] += 1
            elif str(reaction) == '❌':
                if reaction.message.author not in self.coins:
                    self.coins[reaction.message.author] = -1
                else:
                    self.coins[reaction.message.author] -= 1

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        if reaction.message.channel.id == self.channel and not user.bot and not reaction.message.author.bot:
            if str(reaction) == '✅':
                if reaction.message.author in self.coins:
                    self.coins[reaction.message.author] -= 1
            elif str(reaction) == '❌':
                if reaction.message.author in self.coins:
                    self.coins[reaction.message.author] += 1

    @commands.command(name='Coins', help='Tests you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx):
        if ctx.message.channel.id == self.channel:
            if ctx.author in self.coins:
                if self.coins[ctx.author] == 1:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[ctx.author]} meme coin!')
                else:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[ctx.author]} meme coins!')
            else:
                await ctx.send(f'{ctx.author.mention}, you have no meme coins :(')

    @commands.command(name='Leaderboard', help='Displays a list of highest rollers in Meme Coin Town!')
    async def leaderboard(self, ctx):
        if ctx.message.channel.id == self.channel:
            if len(self.coins) > 0:
                topscores = sorted(self.coins, key=lambda y: self.coins.get(y), reverse=True)
                lowscores = sorted(self.coins, key=lambda y: self.coins.get(y))

                most = []
                least = []
                for x in topscores:
                    most.append(str(x.name + ': ' + str(self.coins[x])))

                for x in lowscores:
                    least.append(str(x.name + ': ' + str(self.coins[x])))

                if len(most) > 5:
                    most = most[:5]
                    least = least[:5]

                embed = discord.Embed(title="Meme Coin Leaderboards",
                                      description="Whose Meme Coins stash reigns supreme?!\n", color=0xffff00)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                embed.add_field(name='\u200B', value='\u200B', inline=True)
                embed.add_field(name='\u200B', value='\u200B', inline=True)
                embed.add_field(name='\u200B', value='\u200B', inline=True)
                embed.add_field(name='Most Coins', value='\n'.join(most), inline=True)
                embed.add_field(name='Least Coins', value='\n'.join(least), inline=True)
                embed.set_footer(text="Please report any issues to my owner!")
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(title="Meme Coin Leaderboards",
                                      description="Whose Meme Coins stash reigns supreme?!", color=0xffff00)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                embed.add_field(name='\u200B', value='\u200B')
                embed.add_field(name='No Current Meme Coin Owners!',
                                value='Please give or revoke Meme Coin to construct leaderboards!')
                embed.set_footer(text="Please report any issues to my owner!")
                await ctx.send(embed=embed)
