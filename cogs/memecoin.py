from discord.ext import commands
from discord import Embed, HTTPException
import aiosqlite


def check_memecoin_channel():
    def predicate(ctx):
        """
        A commands.check decorator that ensures MemeCoin commands are only executed in the proper channel.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            (boolean): Whether or not the invocation channel is the authorized MemeCoin channel.
        """

        return ctx.message.channel.id == 636356259255287808
    return commands.check(predicate)


class MemeCoin(commands.Cog):
    """
    A Cogs class that implements a fake currency system for memes.

    Attributes:
        bot (commands.Bot): The Discord bot class.
        channel (int: discord.TextChannel) The id of the channel where MemeCoin can be used.
    """

    def __init__(self, bot):
        """
        The constructor for the MemeCoin class.

        Parameters:
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot
        self.channel = 636356259255287808

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        A listener method that is called whenever a reaction is added.
        'raw' events fire regardless of whether or not a message is cached.
        Requirements listed in check_coin_requirements() must be met to proceed.
        Meme Coin records are stored in the database.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        query = values = None
        if not (author_id := await check_coin_requirements(self.bot, payload, self.channel)):
            return

        if str(payload.emoji) == '✅':
            # if the user is NOT in the database, create their record with a value of 1
            if not (await check_for_user(self.bot.DATABASE_NAME, author_id)):
                query = 'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?)'
                values = (author_id, 1)
            # otherwise, increment their record
            else:
                query = 'UPDATE MEMECOIN SET COINS=COINS+1 WHERE USER_ID=?'
                values = (author_id,)
        elif str(payload.emoji) == '❌':
            # if the user is NOT in the database, create their record with a value of -1
            if not (await check_for_user(self.bot.DATABASE_NAME, author_id)):
                query = 'INSERT INTO MEMECOIN (USER_ID, COINS) VALUES (?, ?)'
                values = (author_id, -1)
            # otherwise, decrement their record
            else:
                query = 'UPDATE MEMECOIN SET COINS=COINS-1 WHERE USER_ID=?'
                values = (author_id,)

        if query is not None:
            await execute_query(self.bot.DATABASE_NAME, query, values, 'MemeCoin Reaction_Add Database Transaction')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        A listener method that is called whenever a reaction is removed.
        'raw' events fire regardless of whether or not a message is cached.
        Requirements listed in check_coin_requirements() must be met to proceed.
        Meme Coin records are stored in the database.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        query = None
        if not (author_id := await check_coin_requirements(self.bot, payload, self.channel)):
            return

        # Don't create a record on a reaction removal. Increment or decrement an existing record where appropriate
        if str(payload.emoji) == '✅':
            if await check_for_user(self.bot.DATABASE_NAME, author_id):
                query = 'UPDATE MEMECOIN SET COINS=COINS-1 WHERE USER_ID=?'
        elif str(payload.emoji) == '❌':
            if await check_for_user(self.bot.DATABASE_NAME, author_id):
                query = 'UPDATE MEMECOIN SET COINS=COINS+1 WHERE USER_ID=?'

        if query is not None:
            await execute_query(self.bot.DATABASE_NAME, query, (author_id,),
                                'MemeCoin Reaction_Remove Database Transaction')

    @check_memecoin_channel()
    @commands.command(name='coins', help='Checks you how many of those sweet, sweet Meme Coins you own!')
    async def coins(self, ctx):
        """
        A method that outputs the number of Meme Coins a user currently owns.

        Checks:
            check_memecoin_channel(): Whether or not the command is invoked in the proper channel.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Success: The number of coins the user currently owns.
            Failure: An error message.

        Returns:
            None.
        """

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
        """
        A method that outputs an embed, detailing the top and bottom Meme Coin owners.

        Checks:
            cooldown(): Whether or not the command is on cooldown. Can be used (1) time per (5) minutes.
            check_memecoin_channel(): Whether or not the command is invoked in the proper channel.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Success: An embed with (at most) the top and bottom 5 Meme Coin owners.
            Failure: Nothing.

        Returns:
            None.
        """

        embed = Embed(title="Meme Coin Leaderboards",
                      description="Whose Meme Coins stash reigns supreme?!\n", color=0xffff00)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.add_field(name='\u200B', value='\u200B', inline=True)
        embed.add_field(name='\u200B', value='\u200B', inline=True)
        embed.add_field(name='\u200B', value='\u200B', inline=True)
        embed.set_footer(text="Please report any issues to my owner!")

        result = await retrieve_query(self.bot.DATABASE_NAME, 'SELECT * FROM MEMECOIN', (),
                                      'MemeCoin Leaderboard Retrieval Database')

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

            embed.add_field(name='Most Coins', value='\n'.join(most), inline=True)
            embed.add_field(name='Least Coins', value='\n'.join(least), inline=True)
        else:
            embed.add_field(name='No Current Meme Coin Owners!',
                            value='Please give or revoke Meme Coin to construct leaderboards!')

        await ctx.send(embed=embed)


async def check_coin_requirements(bot, payload, memecoin_channel):
    """
    A method that checks whether or not an event is eligible for Meme Coins.
    Returns -1 if requirements are not met.
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
        (int): If the requirements have been met - the original message's author id. Else - -1.
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


async def check_for_user(database_name, user_id):
    """
    A method that checks whether or not a user exists in the Meme Coin database table.

    Parameters:
        database_name (str): The name of the database.
        user_id (int): The id of the user.

    Returns:
        (boolean): Whether or not the user exists in the table.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            async with db.execute('SELECT EXISTS(SELECT 1 FROM MEMECOIN WHERE USER_ID=?)', (user_id,)) as cursor:
                return (await cursor.fetchone())[0] == 1

    except aiosqlite.Error as e:
        print(f'MemeCoin Existence Error: {e}')
        return False


async def execute_query(database_name, query, values, instigator='Default MemeCoin'):
    """
    A method that executes an sqlite3 statement.
    Note: Use retrieve_query() for 'SELECT' statements.

    Parameters:
        database_name (str): The name of the database.
        query (str): The statement to execute.
        values (tuple): The values to insert into the query.
        instigator (str): The invocation context of the query. Default: 'Default MemeCoin'.

    Returns:
        None.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            await db.execute(query, values)
            await db.commit()

    except aiosqlite.Error as e:
        print(f'{instigator} Error: {e}')


async def retrieve_query(database_name, query, values, instigator='Default MemeCoin'):
    """
    A method that returns the result of an sqlite3 'SELECT' statement.
    Note: Use execute_query() for non-'SELECT' statements.

    Parameters:
        database_name (str): The name of the database.
        query (str): The statement to execute.
        values (tuple): The values to insert into the query.
        instigator (str): The invocation context of the query. Default: 'Default MemeCoin'.

    Returns:
        (list): A list of sqlite3 row objects. Can be empty.
    """

    try:
        async with aiosqlite.connect(database_name) as db:
            async with db.execute(query, values) as cursor:
                return await cursor.fetchall()

    except aiosqlite.Error as e:
        print(f'{instigator} Error: {e}')


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(MemeCoin(bot))
    print('Completed Setup for Cog: MemeCoin')
