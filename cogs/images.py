from discord.ext import commands
from utils.image_utils import NoImage, BufferSizeExceeded, extract_image_as_bytes, invert_object, title_card_generator
from dreambot import DreamBot
import discord


class Images(commands.Cog):
    """
    A Cogs class that invokes ImageUtils methods.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the MemeCoin class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='invert')
    async def invert(self, ctx: commands.Context, url: str = None) -> None:
        """
        A method that invokes image inversion from ImageUtils.

        Parameters:
            ctx (commands.Context): The invocation context.
            url (Optional[str]): An optional image url. Default: None

        Output:
            Success: A discord.File object containing the inverted image.
            Failure: An error message.

        Returns:
            None.
        """

        async with ctx.channel.typing():
            try:
                buffer = await extract_image_as_bytes(ctx.message, url)
                inverted = await invert_object(buffer)
            except NoImage:
                await ctx.send('No image was provided.')
                return
            except BufferSizeExceeded:
                await ctx.send('The supplied image is too large. Bots are limited to images of size < 8 Megabytes.')
                return
            except discord.HTTPException as e:
                await ctx.send(f'Could not download image. Details: [Status {e.status} | {e.text}]')
                return

            try:
                await ctx.send(file=discord.File(inverted, filename="inverted.png"))
            except discord.HTTPException as e:
                await ctx.send(f'Could not send image. Details: [Status {e.status} | {e.text}]')
                return

    @commands.command(name='iasip', aliases=['sun', 'sunny', 'title'])
    async def iasip_title_card(self, ctx: commands.Context, *, title: str) -> None:
        """
        A method that invokes "It's Always Sunny In Philadelphia" title card generation from ImageUtils.

        Parameters:
            ctx (commands.Context): The invocation context.
            title (str): The text to display on the title card.

        Output:
            Success: A discord.File object containing the generated title card image.
            Failure: An error message.

        Returns:
            None.
        """

        async with ctx.channel.typing():
            if not title.startswith('"'):
                title = '"' + title

            if not title.endswith('"'):
                title += '"'

            buffer = await title_card_generator(title)

            try:
                await ctx.send(file=discord.File(buffer, filename="iasip.png"))
            except discord.HTTPException as e:
                await ctx.send(f'Could not send image. Details: [Status {e.status} | {e.text}]')
                return


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Images(bot))
    print('Completed Setup for Cog: Images')
