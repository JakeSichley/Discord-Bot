import discord
import PIL.ImageOps
from discord.ext import commands
from aiohttp import ClientSession
from PIL import Image
from io import BytesIO
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from re import search


class Images(commands.Cog):
    """
    A Cogs class that invokes ImageSupport methods.

    Attributes:
        bot (commands.Bot): The Discord bot class.
    """

    def __init__(self, bot):
        """
        The constructor for the MemeCoin class.

        Parameters:
            bot (commands.Bot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='invert')
    async def invert(self, ctx: commands.Context, url: str = None) -> None:
        """
        A method that invokes image inversion from ImageSupport.

        Parameters:
            ctx (commands.Context): The invocation context.
            url (Optional[str]): An optional image url. Default: None

        Output:
            Success: a discord.File object containing the inverted image2.
            Failure: An error message.

        Returns:
            None.
        """

        async with ctx.channel.typing():
            try:
                buffer = await ImageSupport.extract_image_as_bytes(ctx.message, url)
                inverted = await ImageSupport.invert_object(buffer)
            except NoImage:
                await ctx.send('No image was provided.')
                return
            except discord.HTTPException as e:
                await ctx.send(f'Could not download image. Details: [Status {e.status} | {e.text}]')
                return

            await ctx.send(file=discord.File(inverted, filename="inverted.png"))


class ImageSupport:
    """
    A class that implements image manipulation methods.

    Attributes:
        None.
    """

    @staticmethod
    async def get_from_cdn(url) -> bytes:
        """
        A method that downloads an image from a url.

        Parameters:
            url (str): The url of the image.

        Returns:
            (bytes): A bytes object of the downloaded image.
        """

        async with ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                elif resp.status == 404:
                    raise discord.NotFound(resp, 'Not Found')
                elif resp.status == 403:
                    raise discord.Forbidden(resp, 'Forbidden')
                else:
                    raise discord.HTTPException(resp, 'Failed')

    @staticmethod
    async def extract_image_as_bytes(message: discord.Message, url: str) -> BytesIO:
        """
        A method that downloads an image from a url.

        Parameters:
            message (discord.Message): The message in the invocation context.
            url (str): An image url.
        Returns:
            buffer (BytesIO): A BytesIO object of the image data.
        """

        if message.attachments:
            buffer = BytesIO()
            await message.attachments[0].save(buffer, seek_begin=True)
            return buffer
        elif url and search(r'.(webp|jpeg|jpg|png|bmp)', url):
            # if the user provided an embed, refresh to allow discord time to update the message
            buffer = BytesIO()
            data = await ImageSupport.get_from_cdn(url)
            buffer.write(data)
            buffer.seek(0)
            return buffer
        else:
            raise NoImage

    @staticmethod
    async def invert_object(file: BytesIO) -> BytesIO:
        """
        A method that downloads an image from a url.
        The inner function actually performs the inversion (blocking).
        The outer function (this) wraps the blocking code, allowing for async execution.

        Parameters:
            file (BytesIO): A BytesIO object of the image to invert.
        Returns:
            inverted_buffer (BytesIO): A BytesIO object of the inverted image.
        """

        def blocking_invert() -> BytesIO:
            inverted_buffer = BytesIO()
            image = Image.open(file)

            if image.mode == 'RGBA':
                r, g, b, a = image.split()
                rgb_image = Image.merge('RGB', (r, g, b))
                inverted_image = PIL.ImageOps.invert(rgb_image)
                r2, g2, b2 = inverted_image.split()
                final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
                final_transparent_image.save(inverted_buffer, format='PNG')
            else:
                inverted_image = PIL.ImageOps.invert(image)
                inverted_image.save(inverted_buffer, format='PNG')

            inverted_buffer.seek(0)
            return inverted_buffer

        loop = get_event_loop()
        return await loop.run_in_executor(ThreadPoolExecutor(), blocking_invert)


class NoImage(Exception):
    """
    Error raised when no image was supplied.
    """

    pass


def setup(bot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Images(bot))
    print('Completed Setup for Cog: Images')
