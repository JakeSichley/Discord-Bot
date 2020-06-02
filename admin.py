from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name='reload', hidden=True)
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
            await ctx.send(f'Could Not Load Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='mreload', hidden=True)
    async def unload(self, ctx, module):
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
            await ctx.send(f'Manually Reloaded Module: `{module}`')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Could Not Manually Reloaded Module: `{module}`')

    @commands.is_owner()
    @commands.command(name='logout', aliases=['shutdown'], hidden=True)
    async def logout(self, ctx):
        await ctx.send('Logging Out')
        await self.bot.logout()


def setup(bot):
    bot.add_cog(Admin(bot))
    print('Completed Setup for Cog: Admin')
