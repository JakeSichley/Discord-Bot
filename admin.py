from discord.ext import commands
import aiosqlite
from asyncio import TimeoutError


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name='reload', aliases=['load'], hidden=True)
    async def reload(self, ctx, module):
        try:
            self.bot.reload_extension(module)
            await ctx.send(f'Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(module)
            await ctx.send(f'Loaded Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx, module):
        try:
            self.bot.unload_extension(module)
            await ctx.send(f'Unloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Unload Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='mreload', hidden=True)
    async def mreload(self, ctx, module):
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
            await ctx.send(f'Manually Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Manually Reloaded Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx):
        await ctx.send('Confirm Logout?')

        def check(message):
            return message.content.lower() == 'confirm' and message.author.id == self.bot.owner_id

        try:
            await self.bot.wait_for('message', timeout=10.0, check=check)
        except TimeoutError:
            await ctx.send('Logout Aborted.')
        else:
            await ctx.send('Logout Confirmed.')
            await self.bot.logout()

    @commands.is_owner()
    @commands.command(name='eval', hidden=True)
    async def eval(self, ctx, _ev: str):
        try:
            output = eval(_ev)
        except Exception as e:
            output = e

        await ctx.send(output)

    @commands.is_owner()
    @commands.command(name='execute', hidden=True)
    async def execute(self, ctx, *, _ev: str):
        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                if 'SELECT' in _ev:
                    async with db.execute(_ev) as cursor:
                        await ctx.send(await cursor.fetchall())
                else:
                    await db.execute(_ev)
                    await db.commit()
                    await ctx.send('Executed.')

        except aiosqlite.Error as e:
            await ctx.send(f'Error: {e}')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.is_owner()
    @commands.command(name='reloadprefixes', hidden=True)
    async def reload_prefixes(self, ctx):
        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                async with db.execute("SELECT * FROM Prefixes") as cursor:
                    rows = await cursor.fetchall()
                    if not rows:
                        self.bot.prefixes.clear()
                    else:
                        async for guild, prefix in cursor:
                            self.bot.prefixes[int(guild)] = prefix
                    await ctx.send('Reloaded Prefixes.')

        except aiosqlite.Error as e:
            await ctx.send(f'Error: {e}')
            print(f'Reload Prefixes Error: {e}')

    @commands.is_owner()
    @commands.command(name='resetcooldown', hidden=True)
    async def reset_cooldown(self, ctx, command):
        self.bot.get_command(command).reset_cooldown(ctx)

        await ctx.send(f'Reset cooldown of Command: `{command}`')


def setup(bot):
    bot.add_cog(Admin(bot))
    print('Completed Setup for Cog: Admin')
