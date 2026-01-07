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

import inspect
from typing import Optional, Callable, Awaitable, TypeVar, Set

import aiohttp

from utils.network.exponential_backoff import BackoffRule, ExponentialBackoffException
from utils.network.return_type import JSON
from utils.network.utils import Headers, EmptyResponseError
from utils.observability.loggers import bot_logger, make_debug_scope
from utils.utils import short_random_id

ReturnType = TypeVar('ReturnType')


class NetworkClient:
    """
    Client for making network requests with unified error handling.

    Constants
        ITEM_ID_AUTOCOMPLETE_DEBUG_SCOPE (Dict[str, str]): Debug scope tag for item_id autocomplete logs.

    Attributes:
        _session (aiohttp.ClientSession): The client session for the bot.
        _backoff_cache (Set[BackoffRule]): A set of backoff rules to match urls against.
        _default_max_backoff_time (int): The maximum backoff time (used when creating new rules).
    """

    NETWORK_CLIENT_DEBUG_SCOPE = make_debug_scope('network_client')

    def __init__(
            self,
            session: aiohttp.ClientSession,
            default_max_backoff_time: int = 60 * 60 * 4  # four hours
    ) -> None:
        """
        Initializes a NetworkClient instance.

        Parameters:
            session (aiohttp.ClientSession): The client session for the bot.
            default_max_backoff_time (int): The maximum backoff time (used when creating new rules).

        Returns:
            None.
        """

        self._session: aiohttp.ClientSession = session
        self._backoff_cache: Set[BackoffRule] = set()
        self._default_max_backoff_time: int = default_max_backoff_time

    def _get_or_create_backoff_for_url(self, url: str, debug_identifier: str) -> BackoffRule:
        """
        Gets or creates a backoff rule for a url.

        Parameters:
            url (str): The url to get or create a backoff rule for.
            debug_identifier (str): A unique identifier for debugging purposes.

        Returns:
            (BackoffRule): The backoff rule for the url.
        """

        try:
            existing_rule = next(x for x in self._backoff_cache if x.matches_url(url))
            bot_logger.debug(
                f'{debug_identifier} Matched url `{url}` against existing pattern `{existing_rule.pattern.pattern}`.',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
            return existing_rule
        except StopIteration:
            new_rule = BackoffRule(url, self._default_max_backoff_time)
            self._backoff_cache.add(new_rule)
            bot_logger.debug(
                f'{debug_identifier} No matches for url `{url}` against existing patterns, creating new rule.',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
            return new_rule

    def _increment_backoff_for_url(self, url: str, debug_identifier: str) -> None:
        """
        Increments the backoff for a url.

        Parameters:
            url (str): The url to increment the backoff for.
            debug_identifier (str): A unique identifier for debugging purposes.

        Returns:
            None.
        """

        if existing_rule := next((x for x in self._backoff_cache if x.matches_url(url)), None):
            self._backoff_cache.remove(existing_rule)
            existing_rule.backoff.record_failure()
            self._backoff_cache.add(existing_rule)
            bot_logger.debug(
                f'{debug_identifier} Incremented backoff for url `{url}`. '
                f'New count: {existing_rule.backoff.backoff_count}',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
        else:
            bot_logger.warning(f'Attempted to increment backoff for url `{url}` but no matching rule found.')

    def _reset_backoff_for_url(self, url: str, debug_identifier: str) -> None:
        """
        Resets the backoff for a url.

        Parameters:
            url (str): The url to reset the backoff for.
            debug_identifier (str): A unique identifier for debugging purposes.

        Returns:
            None.
        """

        if existing_rule := next((x for x in self._backoff_cache if x.matches_url(url)), None):
            self._backoff_cache.remove(existing_rule)
            existing_rule.backoff.reset()
            self._backoff_cache.add(existing_rule)
            bot_logger.debug(
                f'{debug_identifier} Reset backoff for url `{url}`.', extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
        else:
            bot_logger.warning(f'Attempted to increment reset for url `{url}` but no matching rule found.')

    async def _request(
            self,
            url: str,
            handler: Callable[[aiohttp.ClientResponse], Awaitable[ReturnType]],
            *,
            headers: Optional['Headers'],
            forward_exceptions: bool,
            ssl: Optional[bool],
            bypass_backoff: bool,
            raise_for_empty_response: bool
    ) -> Optional[ReturnType]:
        """
        Makes a request to a url.

        Parameters:
            url (str): The url to make the request to.
            handler (Callable[[aiohttp.ClientResponse], Awaitable[ReturnType]]): The handler for the response.
            headers (Optional[Headers]): The headers to send with the request.
            forward_exceptions (bool): Whether to forward exceptions instead of suppressing them.
            ssl (Optional[bool]): Whether to use ssl.
            bypass_backoff (bool): Whether to bypass the exponential backoff.
            raise_for_empty_response (bool): Whether to raise an `EmptyResponseError` if the response is empty.

        Returns:
            (Optional[ReturnType]): The transformed response, or None if the request failed.
        """

        exception: Optional[Exception] = None
        transformed_response: Optional[ReturnType] = None
        debug_identifier: str = short_random_id()
        return_type_identifier: str = inspect.getouterframes(inspect.currentframe(), 2)[1][3]

        bot_logger.debug(
            f'{debug_identifier} Starting request for url `{url}`. '
            f'Kwargs: {headers=}, {forward_exceptions=}, {ssl=}, {bypass_backoff=}, {raise_for_empty_response=}.',
            extra=self.NETWORK_CLIENT_DEBUG_SCOPE
        )

        try:
            if (
                    not bypass_backoff
                    and (matched_rule := self._get_or_create_backoff_for_url(url, debug_identifier))
                    and matched_rule.backoff.remaining_backoff > 0
            ):
                bot_logger.debug(
                    f'{debug_identifier} Request for url `{url}` is currently backed off without bypass - '
                    f'raising `ExponentialBackoffException`.',
                    extra=self.NETWORK_CLIENT_DEBUG_SCOPE
                )
                raise ExponentialBackoffException(url, matched_rule)

            async with self._session.get(
                    url, headers=headers, ssl=ssl, raise_for_status=True
            ) as r:
                transformed_response = await handler(r)

        except aiohttp.ClientResponseError as e:
            exception = e
            bot_logger.warning(f'Network Request Error. ("{url}"). {e.status}. {e.message}.')
        except aiohttp.ClientError as e:
            exception = e
            bot_logger.warning(f'Network Request Client Error. ("{url}"). {type(e)} - {e} - {e.args}.')
        except ExponentialBackoffException as e:
            exception = e
            bot_logger.warning(f'Network Request ExponentialBackoff Error: {e}.')
        except Exception as e:
            exception = e
            bot_logger.error(f'Network Request Uncaught Exception. ("{url}"). {type(e)} - {e}.')

        # if there was an exception raised, we should always attempt to increment backoff
        #   -> Exceptions: Don't increment if `bypass_backoff` is True,
        #   or if we avoided a bad request by raising ExponentialBackoffException
        if caught_exception := exception:
            if not bypass_backoff and not isinstance(caught_exception, ExponentialBackoffException):
                bot_logger.debug(
                    f'{debug_identifier} Error was encountered during request for `{url}` '
                    f'without bypass backoff - attempting to increment backoff.',
                    extra=self.NETWORK_CLIENT_DEBUG_SCOPE
                )
                self._increment_backoff_for_url(url, debug_identifier)

            if forward_exceptions:
                raise caught_exception

        if transformed_response is not None:
            if not bypass_backoff:
                self._reset_backoff_for_url(url, debug_identifier)

            bot_logger.debug(
                f'{debug_identifier} Request for url `{url}` was successful. '
                f'Response handler type: {return_type_identifier}',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
            return transformed_response

        if raise_for_empty_response:
            bot_logger.debug(
                f'{debug_identifier} Request for url `{url}` was successful, but did not yield a transformable '
                f'response. Per caller, raising for empty response.',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
            raise EmptyResponseError(
                f'Request for url `{url}` was successful, but response was empty. '
                f'Response handler type: {return_type_identifier}.'
            )
        else:
            bot_logger.debug(
                f'{debug_identifier} Request for url `{url}` was either unsuccessful or did not yield a transformable '
                f'response. Errors are either suppressed or no errors were raised. {forward_exceptions=}, {exception=}',
                extra=self.NETWORK_CLIENT_DEBUG_SCOPE
            )
            return None

    async def fetch_bytes(
            self,
            url: str,
            /,
            *,
            headers: Optional['Headers'] = None,
            forward_exceptions: bool = False,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False,
            raise_for_empty_response: bool = False
    ) -> Optional[bytes]:
        """
        Fetches bytes from a url.

        Attributes:
            url (str): The url to fetch bytes from.
            headers (Optional[Headers]): The headers to send with the request.
            forward_exceptions (bool): Whether to forward exceptions instead of suppressing them.
            ssl (Optional[bool]): Whether to use ssl.
            bypass_backoff (bool): Whether to bypass the exponential backoff.
            raise_for_empty_response (bool): Whether to raise an `EmptyResponseError` if the response is empty.

        Returns:
            (Optional[bytes]): The bytes from the url, or None if the request failed.
        """

        return await self._request(
            url,
            lambda r: r.read(),
            headers=headers,
            forward_exceptions=forward_exceptions,
            ssl=ssl,
            bypass_backoff=bypass_backoff,
            raise_for_empty_response=raise_for_empty_response
        )

    async def fetch_json(
            self,
            url: str,
            /,
            *,
            encoding: str = 'utf-8',
            headers: Optional['Headers'] = None,
            forward_exceptions: bool = False,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False,
            raise_for_empty_response: bool = False
    ) -> Optional['JSON']:
        """
        Fetches JSON from a url.

        Attributes:
            url (str): The url to fetch json from.
            encoding (str): The encoding to use.
            headers (Optional[Headers]): The headers to send with the request.
            forward_exceptions (bool): Whether to forward exceptions instead of suppressing them.
            ssl (Optional[bool]): Whether to use ssl.
            bypass_backoff (bool): Whether to bypass the exponential backoff.
            raise_for_empty_response (bool): Whether to raise an `EmptyResponseError` if the response is empty.

        Returns:
            (Optional[JSON]): The json from the url, or None if the request failed.
        """

        return await self._request(
            url,
            lambda r: r.json(encoding=encoding),
            headers=headers,
            forward_exceptions=forward_exceptions,
            ssl=ssl,
            bypass_backoff=bypass_backoff,
            raise_for_empty_response=raise_for_empty_response
        )

    async def fetch_text(
            self,
            url: str,
            /,
            *,
            encoding: str = 'utf-8',
            headers: Optional['Headers'] = None,
            forward_exceptions: bool = False,
            ssl: Optional[bool] = None,
            bypass_backoff: bool = False,
            raise_for_empty_response: bool = False
    ) -> Optional[str]:
        """
        Fetches text from a url.

        Attributes:
            url (str): The url to fetch text from.
            encoding (str): The encoding to use.
            headers (Optional[Headers]): The headers to send with the request.
            forward_exceptions (bool): Whether to forward exceptions instead of suppressing them.
            ssl (Optional[bool]): Whether to use ssl.
            bypass_backoff (bool): Whether to bypass the exponential backoff.
            raise_for_empty_response (bool): Whether to raise an `EmptyResponseError` if the response is empty.

        Returns:
            (Optional[str]): The text from the url, or None if the request failed.
        """

        return await self._request(
            url,
            lambda r: r.text(encoding=encoding),
            headers=headers,
            forward_exceptions=forward_exceptions,
            ssl=ssl,
            bypass_backoff=bypass_backoff,
            raise_for_empty_response=raise_for_empty_response
        )
