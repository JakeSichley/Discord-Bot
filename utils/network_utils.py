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
    A method that downloads an image from a url.

    Parameters:
        url (str): The url of the request.
        options (**kwargs): Optional, keyword only arguments.
            SUPPORTED:
                'return_type' (NetworkReturnType)
                'header' (Dict)
                'encoding' (str)
                'raise_errors' (bool)

    Returns:
        (Optional[Union[str, bytes, Dict[Any, Optional[Any]]]]) The request's response.
    """

    return_type = NetworkReturnType(options.pop('return_type', 1))
    header = options.pop('header', None)
    encoding = options.pop('encoding', 'utf-8')
    raise_errors = options.pop('raise_errors', True)

    async with aiohttp.ClientSession(raise_for_status=raise_errors) as session:
        async with session.get(url, headers=header) as r:
            if return_type == NetworkReturnType.JSON:
                return await r.json(encoding=encoding)
            elif return_type == NetworkReturnType.BYTES:
                return await r.read()
            else:
                return await r.text(encoding=encoding)
