"""
MIT License

Copyright (c) 2021 Jake Sichley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any
from enum import Enum
import aiohttp


class NetworkReturnType(Enum):
    """
    An Enum class that represents how a network request's response should be returned.
    """

    TEXT = 1  # str
    JSON = 2  # Union[Dict[Any, Optional[Any]]]
    BYTES = 3  # bytes


async def network_request(url: str, **options) -> Any:
    """
    A method that downloads an image from an url.

    Parameters:
        url (str): The url of the request.
        options (**kwargs): Optional, keyword only arguments.
            SUPPORTED:
                'return_type' (NetworkReturnType)
                'header' (Dict)
                'encoding' (str)
                'raise_errors' (bool)
                'ssl' (bool)

    Raises:
        aiohttp.ClientResponseError

    Returns:
        (Optional[Union[str, bytes, Dict[Any, Optional[Any]]]]) The request's response.
    """

    return_type = NetworkReturnType(options.pop('return_type', 1))
    header = options.pop('header', None)
    encoding = options.pop('encoding', 'utf-8')
    raise_errors = options.pop('raise_errors', True)
    ssl = options.pop('ssl', None)

    async with aiohttp.ClientSession(raise_for_status=raise_errors) as session:
        async with session.get(url, headers=header, ssl=ssl) as r:
            if return_type == NetworkReturnType.JSON:
                return await r.json(encoding=encoding)
            elif return_type == NetworkReturnType.BYTES:
                return await r.read()
            else:
                return await r.text(encoding=encoding)
