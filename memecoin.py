from discord.ext import commands
from discord import Embed
import aiosqlite


def check_memecoin_channel():
    def predicate(ctx):
        return ctx.message.channel.id == 636356259255287808
    return commands.check(predicate)


class MemeCoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @check_memecoin_channel()
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        # Meme Coins can only be awarded on messages that have a link or an attachment
        if not user.bot and not reaction.message.author.bot and valid_meme(reaction.message):
            query = values = None

            if str(reaction) == '✅':
                if user == reaction.message.author:
                    await reaction.message.channel.send(f'Man, look at this clown {user.mention}..'
                                                        f' trying to give themself Meme Coins.. just shameful.')
                elif (await check_for_user(self.bot.DATABASE_NAME, reaction.message.author.id)) != 1:
                    query = 'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?)'
                    values = (reaction.message.author.id, 1)
                else:
                    query = 'UPDATE MEMECOIN SET COINS=COINS+1 WHERE USER_ID=?'
                    values = (reaction.message.author.id,)
            elif str(reaction) == '❌':
                if user == reaction.message.author:
                    return
                elif (await check_for_user(self.bot.DATABASE_NAME, reaction.message.author.id)) != 1:
                    query = 'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?)'
                    values = (reaction.message.author.id, -1)
                else:
                    query = 'UPDATE MEMECOIN SET COINS=COINS-1 WHERE USER_ID=?'
                    values = (reaction.message.author.id,)

            if query is not None:
                await execute_query(self.bot.DATABASE_NAME, query, values, 'MemeCoin Reaction_Add Database Transaction')

    @check_memecoin_channel()
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Check to make sure the message comes from the appropriate channel
        # Check to make sure the user adding the reaction isn't a bot
        # Check to make sure the reaction isn't being added to a bot's message
        # Meme Coins can only be awarded on messages that have a link or an attachment
        if not user.bot and not reaction.message.author.bot and valid_meme(reaction.message):
            query = None

            if user == reaction.message.author:
                return
            elif str(reaction) == '✅':
                if (await check_for_user(self.bot.DATABASE_NAME, reaction.message.author.id)) == 1:
                    query = 'UPDATE MEMECOIN SET COINS=COINS-1 WHERE USER_ID=?'
            elif str(reaction) == '❌':
                if (await check_for_user(self.bot.DATABASE_NAME, reaction.message.author.id)) == 1:
                    query = 'UPDATE MEMECOIN SET COINS=COINS+1 WHERE USER_ID=?'

            if query is not None:
                await execute_query(self.bot.DATABASE_NAME, query, (reaction.message.author.id,),
                                    'MemeCoin Reaction_Remove Database Transaction')

    @check_memecoin_channel()
    @commands.command(name='coins', help='Tests you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx):
        if (await check_for_user(self.bot.DATABASE_NAME, ctx.author.id)) == 1:
            result = await retrieve_query(self.bot.DATABASE_NAME, 'SELECT COINS FROM MEMECOIN WHERE USER_ID=?',
                                          (ctx.author.id,), 'MemeCoin Coins Retrieval Database')
            if result is not None:
                await ctx.send(f'{ctx.author.mention}, you have {result[0][0]} Meme Coin(s)!')
            else:
                await ctx.send(f'{ctx.author.mention}, I might have misplaced your Meme Coins..')
                print(f'MemeCoin Coins Query Result Error: USER_ID exists but returned None (ID: {ctx.author.id})')
        else:
            await ctx.send(f'{ctx.author.mention}, you have no Meme Coins :(')

    @commands.cooldown(1, 300)
    @check_memecoin_channel()
    @commands.command(name='leaderboard', help='Displays a list of highest rollers in Meme Coin Town!',
                      aliases=['leaderboards'])
    async def leaderboard(self, ctx):
        result = await retrieve_query(self.bot.DATABASE_NAME, 'SELECT * FROM MEMECOIN', (),
                                      'MemeCoin Leaderboard Retrival Database')
        if len(result) > 0:
            top_scores = sorted(result, key=lambda x: x[1], reverse=True)
            formatted_scores = []
            # Check each entry in the sorted list of scores
            for tup in top_scores:
                user = self.bot.get_user(tup[0])
                if user is not None:
                    formatted_scores.append(user.name + ': ' + str(tup[1]))

            embed = Embed(title="Meme Coin Leaderboards",
                          description="Whose Meme Coins stash reigns supreme?!\n", color=0xffff00)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.add_field(name='\u200B', value='\u200B', inline=True)
            embed.add_field(name='\u200B', value='\u200B', inline=True)
            embed.add_field(name='\u200B', value='\u200B', inline=True)
            embed.set_footer(text="Please report any issues to my owner!")

            if len(formatted_scores) > 0:
                most = formatted_scores[:5]
                least = (formatted_scores[::-1])[:5]

                embed.add_field(name='Most Coins', value='\n'.join(most), inline=True)
                embed.add_field(name='Least Coins', value='\n'.join(least), inline=True)
            else:
                embed.add_field(name='No Current Meme Coin Owners!',
                                value='Please give or revoke Meme Coin to construct leaderboards!')

            await ctx.send(embed=embed)

    def cog_unload(self):
        print('Completed Unload for Cog: MemeCoin')


'''Helper Functions'''


def valid_meme(message):
    # Checks whether or not a message meets the criteria for Meme Coins
    return message.content.find('http') != -1 or len(message.attachments) > 0


async def check_for_user(database_name, user_id):
    try:
        async with aiosqlite.connect(database_name) as db:
            async with db.execute('SELECT EXISTS(SELECT 1 FROM MEMECOIN WHERE USER_ID=?)', (user_id,)) as cursor:
                return (await cursor.fetchone())[0] == 1

    except aiosqlite.Error as e:
        print(f'MemeCoin Existence Error: {e}')


async def execute_query(database_name, query, values, instigator='Default MemeCoin'):
    try:
        async with aiosqlite.connect(database_name) as db:
            await db.execute(query, values)
            await db.commit()

    except aiosqlite.Error as e:
        print(f'{instigator} Error: {e}')


async def retrieve_query(database_name, query, values, instigator='Default MemeCoin'):
    try:
        async with aiosqlite.connect(database_name) as db:
            async with db.execute(query, values) as cursor:
                return await cursor.fetchall()

    except aiosqlite.Error as e:
        print(f'{instigator} Error: {e}')


def setup(bot):
    bot.add_cog(MemeCoin(bot))
    print('Completed Setup for Cog: MemeCoin')
