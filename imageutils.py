import discord
import PIL.ImageOps
from aiohttp import ClientSession
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from io import BytesIO
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from re import search
from discord.ext.commands import MissingRequiredArgument, BadArgument
from typing import List, Tuple


async def fetch_from_cdn(url: str) -> bytes:
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
        if buffer.getbuffer().nbytes >= 8000000:
            raise BufferSizeExceeded
        else:
            return buffer
    elif url and search(r'.(webp|jpeg|jpg|png|bmp)', url):
        # if the user provided an embed, refresh to allow discord time to update the message
        buffer = BytesIO()
        data = await fetch_from_cdn(url)
        buffer.write(data)
        buffer.seek(0)
        if buffer.getbuffer().nbytes >= 8000000:
            raise BufferSizeExceeded
        else:
            return buffer
    else:
        raise NoImage


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


async def title_card_generator(title: str) -> BytesIO:
    """
    A method that generates an "It's Always Sunny In Philadelphia" style title card.

    Parameters:
        title (str): The text to display on the title card.

    Returns:
        buffer (BytesIO): A BytesIO object containing the generated title card.
    """

    def generate_card() -> BytesIO:
        width = 4000
        height = 2000

        # Create the font
        font = ImageFont.truetype('textile.ttf', 250)
        # New image based on the settings defined above
        img = Image.new("RGB", (width, height), color='black')
        # Interface to draw on the image
        draw_interface = ImageDraw.Draw(img)

        # Wrap the `text` string into a list of `CHAR_LIMIT`-character strings
        text_lines = wrap(title, 22)
        # Get the first vertical coordinate at which to draw text and the height of each line of text
        y, line_heights = get_y_and_heights(text_lines, (width, height), 40, font)

        # Draw each line of text
        for i, line in enumerate(text_lines):
            # Calculate the horizontally-centered position at which to draw this line
            line_width = font.getmask(line).getbbox()[2]
            x = ((width - line_width) // 2)

            # Draw this line
            draw_interface.text((x, y), line, font=font, fill='white')

            # Move on to the height at which the next line should be drawn at
            y += line_heights[i]

        # Save the resulting image
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    loop = get_event_loop()
    return await loop.run_in_executor(ThreadPoolExecutor(), generate_card)


def get_y_and_heights(text_wrapped: List[str], dimensions: Tuple[int, int], margin: int,
                      font: ImageFont.FreeTypeFont) -> Tuple[int, List[int]]:
    """
    A method to calculate the first vertical coordinate at which to draw text and the height of each line of text.

    Parameters:
        text_wrapped (List[str]): A list a 'wrapped' text strings
        dimensions (Tuple[int, int]): The height and width of the image.
        margin (int): The size of the left and right margins.
        font (ImageFont.FreeTypeFont): The specified font.

    Returns:
        y, line_heights (Tuple[int, List[int]]): First vertical coordinate and subsequent line heights to draw text at.
    """

    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()
    print(type(font))

    # Calculate the height needed to draw each line of text (including its bottom margin)
    line_heights = [font.getmask(text_line).getbbox()[3] + descent + margin for text_line in text_wrapped]
    # The last line doesn't have a bottom margin
    line_heights[-1] -= margin

    # Total height needed
    height_text = sum(line_heights)

    # Calculate the Y coordinate at which to draw the first line of text
    y = (dimensions[1] - height_text) // 2

    # Return the first Y coordinate and a list with the height of each line
    return y, line_heights


class NoImage(MissingRequiredArgument):
    """
    Error raised when no image was supplied.
    """

    pass


class BufferSizeExceeded(BadArgument):
    """
    Error raised when the image supplied was too large.
    """

    pass
