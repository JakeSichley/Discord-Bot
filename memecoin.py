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
                elif reaction.message.author.id not in self.coins:
                    self.coins[reaction.message.author.id] = 1
                else:
                    self.coins[reaction.message.author.id] += 1
            elif str(reaction) == '❌':
                if user == reaction.message.author:
                    return
                elif reaction.message.author.id not in self.coins:
                    self.coins[reaction.message.author.id] = -1
                else:
                    self.coins[reaction.message.author.id] -= 1

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
                if reaction.message.author.id in self.coins:
                    self.coins[reaction.message.author.id] -= 1
            elif str(reaction) == '❌':
                if reaction.message.author.id in self.coins:
                    self.coins[reaction.message.author.id] += 1

    @commands.command(name='coins', help='Tests you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx):
        if ctx.message.channel.id == self.channel:
            if ctx.author.id in self.coins:
                if self.coins[ctx.author.id] == 1:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[ctx.author.id]} Meme Coin!')
                else:
                    await ctx.send(f'{ctx.author.mention}, you have {self.coins[ctx.author.id]} Meme Coins!')
            else:
                await ctx.send(f'{ctx.author.mention}, you have no Meme Coins :(')

    @commands.command(name='leaderboard', help='Displays a list of highest rollers in Meme Coin Town!',
                      aliases=['leaderboards'])
    @commands.cooldown(1, 300)
    async def leaderboard(self, ctx):
        if ctx.message.channel.id == self.channel:
            if len(self.coins) > 0:
                topscores = sorted(self.coins, key=lambda y: self.coins.get(y), reverse=True)
                # formattedscores = [self.bot.get_user(y).name + ': ' + str(self.coins[y]) for y in topscores]
                formattedscores = []

                # Check each entry in the sorted list of scores
                for entry in topscores:
                    user = self.bot.get_user(entry)
                    # If the user id is bad, invoke the `pop` command
                    if user is None:
                        pop = self.bot.get_command('pop')
                        await ctx.invoke(pop, entry, True)
                    # Otherwise, build our list of top scores
                    else:
                        formattedscores.append(user.name + ': ' + str(self.coins[user.id]))

                if len(formattedscores) > 0:
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
                    embed.add_field(name='\u200B', value='\u200B', inline=True)
                    embed.add_field(name='\u200B', value='\u200B', inline=True)
                    embed.add_field(name='\u200B', value='\u200B', inline=True)
                    embed.add_field(name='No Current Meme Coin Owners!',
                                    value='Please give or revoke Meme Coin to construct leaderboards!')
                    embed.set_footer(text="Please report any issues to my owner!")
                    await ctx.send(embed=embed)

    @commands.command(name='pop', help='Removes a key from the Meme Coin vault', hidden=True)
    @commands.is_owner()
    async def pop(self, ctx, userid, inactive=False):
        if ctx.message.channel.id == self.channel:
            user = ctx.message.mentions[0] if len(ctx.message.mentions) > 0 else None

            if user is None:
                snowflakeid = int(userid)
            else:
                snowflakeid = user.id

            if snowflakeid in self.coins:
                plural = 's' if self.coins[snowflakeid] != 1 else ''
                context = '`[Automatic Removal: Bad ID]` ' if inactive is True else ''

                await ctx.send(f'{context}User ID: `{snowflakeid}` with {self.coins[snowflakeid]}'
                               f' Meme Coin{plural} was removed from the vault.')
                self.coins.pop(snowflakeid)
            else:
                await ctx.send(f'User ID: `{snowflakeid}` is not in the Meme Coin Vaults.')

    @commands.command(name='adjust', help='Adjusts Meme Coin values', hidden=True)
    @commands.is_owner()
    async def adjust(self, ctx, username, value: int):
        if ctx.message.channel.id == self.channel:
            _ = username
            user = ctx.message.mentions[0] if len(ctx.message.mentions) > 0 else None

            if user.id in self.coins:
                self.coins[user.id] += value
            else:
                self.coins[user.id] = value

            plural = 's' if self.coins[user.id] != 1 else ''
            await ctx.send(f'{user.mention} now has {self.coins[user.id]} Meme Coin{plural}.')

    @commands.command(name='save', help='Forces a save of the current Meme Coin values', hidden=True)
    @commands.is_owner()
    async def forcesave(self, ctx):
        if ctx.message.channel.id == self.channel:
            self.save.restart()
            await ctx.send('Meme Coin data was forcefully saved.')

    @commands.command(name='load', help='Forces a load of the most recent current Meme Coin values', hidden=True)
    @commands.is_owner()
    async def forceload(self, ctx):
        if ctx.message.channel.id == self.channel:
            self.load.start()
            await ctx.send('Meme Coin data was forcefully loaded.')

    # noinspection PyCallingNonCallable
    @tasks.loop(minutes=15)
    async def save(self):
        with open(self.filepath, 'w') as file:
            for userid in self.coins:
                file.write(f'{userid} {self.coins[userid]}\n')

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
                self.coins[int(entry[0])] = int(entry[1])


'''Helper Functions'''


def validmeme(message):
    # Checks whether or not a message meets the criteria for Meme Coins
    if message.content.find('http') != -1:
        return True
    if len(message.attachments) > 0:
        return True

    return False
