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


def setup(bot):
    bot.add_cog(Admin(bot))
    print('Completed Setup for Cog: Admin')
