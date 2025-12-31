"""
MIT License

Copyright (c) 2019-Present Jake Sichley

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

from typing import Optional, Callable, Awaitable, TypeVar, Set

import aiohttp

from utils.observability.loggers import bot_logger
from utils.network.return_type import JSON
from utils.network.utils import Headers
from utils.network.exponential_backoff import ExponentialBackoff, BackoffRule


ReturnType = TypeVar('ReturnType')


class NetworkClient:
    """
    Client for making network requests with unified error handling.
    """

    def __init__(
            self,
            session: aiohttp.ClientSession,
            default_max_backoff_time: int = 60 * 60 * 4  # four hours
    ) -> None:
        self._session = session
        self._backoff_cache: Set[BackoffRule] = set()
        self._default_max_backoff_time = default_max_backoff_time

    def _get_or_create_backoff_for_url(self, url: str) -> ExponentialBackoff:
        try:
            return next(x.backoff for x in self._backoff_cache if x.matches_url(url))
        except StopIteration:
            new_rule = BackoffRule(url, self._default_max_backoff_time)
            self._backoff_cache.add(new_rule)
            return new_rule.backoff

    def _increment_backoff_for_url(self, url: str) -> None:
        if existing_rule := next((x for x in self._backoff_cache if x.matches_url(url)), None):
            self._backoff_cache.remove(existing_rule)
            existing_rule.backoff.record_failure()
            self._backoff_cache.add(existing_rule)

    async def _request(
            self,
            url: str,
            handler: Callable[[aiohttp.ClientResponse], Awaitable[ReturnType]],
            *,
            headers: Optional['Headers'],
            raise_errors: Optional[bool],
            ssl: Optional[bool],
            bypass_backoff: bool,
    ) -> Optional[ReturnType]:
        """
        Internal generic method to handle the request lifecycle and error logging.
        """

        exception: Optional[Exception] = None

        if (
            not bypass_backoff
            and raise_errors
            and self._get_or_create_backoff_for_url(url).remaining_backoff > 0
        ):
            raise  # something

        try:
            async with self._session.get(
                    url, headers=headers, ssl=ssl, raise_for_status=raise_errors
            ) as r:
                return await handler(r)

        except aiohttp.ClientResponseError as e:
            exception = e
            bot_logger.warning(f'Network Request Error. ("{url}"). {e.status}. {e.message}')
        except aiohttp.ClientError as e:
            exception = e
            bot_logger.warning(f'Network Request Client Error. ("{url}"). {type(e)} - {e} - {e.args}')

        if raise_errors and (caught_exception := exception):
            if not bypass_backoff:
                self._increment_backoff_for_url(url)
            raise caught_exception

        return None

    async def fetch_bytes(
            self,
            url: str,
            /,
            *,
            headers: Optional['Headers'] = None,
            raise_errors: Optional[bool] = True,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False
    ) -> Optional[bytes]:
        """Requests content from the specified url, returned as bytes."""
        return await self._request(
            url,
            lambda r: r.read(),
            headers=headers,
            raise_errors=raise_errors,
            ssl=ssl,
            bypass_backoff=bypass_backoff
        )

    async def fetch_json(
            self,
            url: str,
            /,
            *,
            encoding: str = 'utf-8',
            headers: Optional['Headers'] = None,
            raise_errors: Optional[bool] = True,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False
    ) -> Optional['JSON']:
        """Requests content from the specified url, returned as JSON."""
        return await self._request(
            url,
            lambda r: r.json(encoding=encoding),
            headers=headers,
            raise_errors=raise_errors,
            ssl=ssl,
            bypass_backoff=bypass_backoff
        )

    async def fetch_text(
            self,
            url: str,
            /,
            *,
            encoding: str = 'utf-8',
            headers: Optional['Headers'] = None,
            raise_errors: Optional[bool] = True,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False
    ) -> Optional[str]:
        """
        Requests content from the specified url, returned as text (str).
        """

        return await self._request(
            url,
            lambda r: r.text(encoding=encoding),
            headers=headers,
            raise_errors=raise_errors,
            ssl=ssl,
            bypass_backoff=bypass_backoff
        )

