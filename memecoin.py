import discord
from discord.ext import commands


class MemeCoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ldchannel = 618847896305139722
        self.devchannel = 636356259255287808
        self.channel = self.ldchannel
        self.coins = {}

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        # Meme Coins can only be awarded on messages that have a link or an attachment
        if (reaction.message.channel.id == self.channel and not user.bot
                and not reaction.message.author.bot and validmeme(reaction.message)):
            if str(reaction) == '✅':
                if user == reaction.message.author:
                    await reaction.message.channel.send(f'Man, look at this clown {user.mention}..'
                                                        f' trying to give themself Meme Coins.. just shameful.')
                elif userkey(user) not in self.coins:
                    self.coins[userkey(user)] = 1
                else:
                    self.coins[userkey(user)] += 1
            elif str(reaction) == '❌':
                if user == reaction.message.author:
                    return
                elif userkey(user) not in self.coins:
                    self.coins[userkey(user)] = -1
                else:
                    self.coins[userkey(user)] -= 1

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        # Meme Coins can only be awarded on messages that have a link or an attachment
        if (reaction.message.channel.id == self.channel and not user.bot
                and not reaction.message.author.bot and validmeme(reaction.message)):
            if user == reaction.message.author:
                return
            if str(reaction) == '✅':
                if userkey(user) in self.coins:
                    self.coins[userkey(user)] -= 1
            elif str(reaction) == '❌':
                if userkey(user) in self.coins:
                    self.coins[userkey(user)] += 1

    @commands.command(name='coins', help='Tests you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx):
        if ctx.message.channel.id == self.channel:
            if userkey(ctx.author) in self.coins:
                if self.coins[userkey(ctx.author)] == 1:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[userkey(ctx.author)]} Meme Coin!')
                else:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[userkey(ctx.author)]} Meme Coins!')
            else:
                await ctx.send(f'{ctx.author.mention}, you have no Meme Coins :(')

    @commands.command(name='leaderboard', help='Displays a list of highest rollers in Meme Coin Town!')
    async def leaderboard(self, ctx):
        if ctx.message.channel.id == self.channel:
            if len(self.coins) > 0:
                topscores = sorted(self.coins, key=lambda y: self.coins.get(y), reverse=True)
                formattedscores = [y[0] + ': ' + str(self.coins[y]) for y in topscores]

                most = formattedscores[:5]
                least = (formattedscores[::-1])[:5]

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


'''Helper Functions'''


def validmeme(message):
    # Checks whether or not a message mets the criteria for Meme Coins
    if message.content.find('http') != -1:
        return True
    if len(message.attachments) > 0:
        return True

    return False


def userkey(user):
    # Returns a neat tuple for accessing Meme Coin data
    return user.name, user.discriminator
