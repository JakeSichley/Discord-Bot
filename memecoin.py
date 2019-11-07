import discord
from discord.ext import commands, tasks
import os


class MemeCoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ldchannel = 618847896305139722
        self.devchannel = 636356259255287808
        self.owner = 91995622093123584
        self.channel = self.devchannel
        self.filepath = 'vault.txt'
        self.coins = {}
        self.load.start()
        self.save.start()

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
                elif userkey(reaction.message.author) not in self.coins:
                    self.coins[userkey(reaction.message.author)] = 1
                else:
                    self.coins[userkey(reaction.message.author)] += 1
            elif str(reaction) == '❌':
                if user == reaction.message.author:
                    return
                elif userkey(reaction.message.author) not in self.coins:
                    self.coins[userkey(reaction.message.author)] = -1
                else:
                    self.coins[userkey(reaction.message.author)] -= 1

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
                if userkey(reaction.message.author) in self.coins:
                    self.coins[userkey(reaction.message.author)] -= 1
            elif str(reaction) == '❌':
                if userkey(reaction.message.author) in self.coins:
                    self.coins[userkey(reaction.message.author)] += 1

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

    @commands.command(name='leaderboard', help='Displays a list of highest rollers in Meme Coin Town!',
                      aliases=['leaderboards'])
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

    @commands.command(name='pop', help='Removes a key from the Meme Coin vault', hidden=True)
    async def pop(self, ctx, username):
        if ctx.message.author.id == self.owner and ctx.message.channel.id == self.channel:
            user = ctx.message.mentions[0] if len(ctx.message.mentions) > 0 else None

            if user is None:
                parts = username.split('#', 1)
                user = (parts[0], parts[1])
                if user in self.coins:
                    plural = 's' if self.coins[user] != 1 else ''
                    await ctx.send(f'{username} with {self.coins[user]}'
                                   f' Meme Coin{plural} was removed from the vault.')
                    self.coins.pop(user)
                else:
                    await ctx.send(f'{user} is not in the Meme Coin Vaults.')

            elif userkey(user) in self.coins:
                plural = 's' if self.coins[userkey(user)] != 1 else ''
                await ctx.send(f'{user.mention} with {self.coins[userkey(user)]}'
                               f' Meme Coin{plural} was removed from the vault.')
                self.coins.pop(userkey(user))
            else:
                await ctx.send(f'{user} is not in the Meme Coin Vaults.')

    @commands.command(name='adjust', help='Adjusts Meme Coin values', hidden=True)
    async def adjust(self, ctx, username, value: int):
        if ctx.message.author.id == self.owner and ctx.message.channel.id == self.channel:
            _ = username
            user = ctx.message.mentions[0] if len(ctx.message.mentions) > 0 else None

            if userkey(user) in self.coins:
                self.coins[userkey(user)] += value
            else:
                self.coins[userkey(user)] = value

            plural = 's' if self.coins[userkey(user)] != 1 else ''
            await ctx.send(f'{user.mention} now has {self.coins[userkey(user)]} Meme Coin{plural}.')

    @commands.command(name='save', help='Forces a save of the current Meme Coin values', hidden=True)
    async def forcesave(self, ctx):
        if ctx.message.author.id == self.owner and ctx.message.channel.id == self.channel:
            self.save.restart()
            await ctx.send('Meme Coin data was forcefully saved.')

    @commands.command(name='load', help='Forces a load of the most recent current Meme Coin values', hidden=True)
    async def forceload(self, ctx):
        if ctx.message.author.id == self.owner and ctx.message.channel.id == self.channel:
            self.load.start()
            await ctx.send('Meme Coin data was forcefully loaded.')

    # noinspection PyCallingNonCallable
    @tasks.loop(minutes=15)
    async def save(self):
        with open(self.filepath, 'w') as file:
            for name, discriminator in self.coins:
                file.write(f'{name} {discriminator} {self.coins[(name, discriminator)]}\n')

    # noinspection PyCallingNonCallable
    @tasks.loop(count=1)
    async def load(self):
        if not os.path.isfile(self.filepath):
            return
        else:
            self.coins.clear()

        with open(self.filepath) as file:
            for line in file:
                entry = line.split(' ')
                self.coins[(entry[0], entry[1])] = int(entry[2])


'''Helper Functions'''


def validmeme(message):
    # Checks whether or not a message meets the criteria for Meme Coins
    if message.content.find('http') != -1:
        return True
    if len(message.attachments) > 0:
        return True

    return False


def userkey(user):
    # Returns a neat tuple for accessing Meme Coin data
    return user.name, user.discriminator
