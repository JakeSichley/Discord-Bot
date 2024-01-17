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

import time
from typing import TypeVar, Dict, Tuple, MutableMapping, Iterator, Optional, Union

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')
_T = TypeVar('_T')


class ExpiringDict(MutableMapping[_KT, _VT]):
    """
    A dictionary with time-expiring keys.

    Notes:
        items(), keys(), and values() may contain expired keys. These methods return views - which cannot be
        invalidated after the reference is obtained.

    Attributes:
        __ttl (float): The number of seconds keys should exist for.
        __mapping (Dict[_KT, Tuple[_VT, float]]): The internal mapping object.
    """

    __slots__ = ('__ttl', '__mapping')

    def __init__(self, seconds: float) -> None:
        """
        The constructor for the ExpiringDict class.

        Parameters:
            seconds (float): The number of seconds keys should exist for.
        """

        self.__ttl: float = seconds
        self.__mapping: Dict[_KT, Tuple[_VT, float]] = dict()

    def __verify_cache_integrity(self) -> None:
        """
        Internal method for invalidating expired keys. Called before individual access methods.

        Parameters:
            None.

        Returns:
            None.
        """

        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__mapping.items() if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self.__mapping[k]

    def __contains__(self, key: _KT) -> bool:  # type: ignore[override]
        """
        Checks whether the supplied key exists in the mapping.

        Parameters:
            key (_KT): The key to check for.

        Returns:
            (bool): Whether the key exists.
        """

        self.__verify_cache_integrity()
        return self.__mapping.__contains__(key)

    def __getitem__(self, key: _KT) -> _VT:
        """
        Retrieve's the specified key's value from the mapping.

        Raises:
            KeyError: The key does not exist.

        Parameters:
            key (_KT): The key whose value to retrieve.

        Returns:
            (_VT): The key's value.
        """

        self.__verify_cache_integrity()
        return self.__mapping.__getitem__(key)[0]

    def __setitem__(self, key: _KT, value: _VT) -> None:
        """
        Adds the supplied key-value pair to the mapping.

        Parameters:
            key (_KT): The key to add.
            value (_VT): The value to add.

        Returns:
            None.
        """

        self.__mapping.__setitem__(key, (value, time.monotonic()))

    def __delitem__(self, key: _KT) -> None:
        """
        Deletes the specified key-value pair from the mapping.

        Raises:
            KeyError: The key does not exist.

        Parameters:
            key (_KT): The key whose value to retrieve.

        Returns:
            None.
        """

        self.__mapping.__delitem__(key)

    def __len__(self) -> int:
        """
        Returns the length of the mapping.

        Parameters:
            None.

        Returns:
            (int) The mapping's length.
        """

        return len(self.__mapping)

    def __iter__(self) -> Iterator[_KT]:
        """
        Returns an iterator of the mapping's keys.

        Parameters:
            None.

        Returns:
            (Iterator[_KT]) The an iterator of the mapping's keys.
        """

        return iter(self.__mapping)

    def get(  # type: ignore[override]
            self, key: _KT, /, default: Optional[Union[_VT, _T]] = None
    ) -> Optional[Union[_VT, _T]]:
        """
        Safety gets a value from the mapping.

        Parameters:
            key (_KT): The key whose value to retrieve.
            default (Optional[Union[_VT, _T]]): The value to return if the key doesn't exist. Default: None.

        Returns:
            (Optional[Union[_VT, _T]]): The value of the key if it exists, otherwise the default value.
        """

        self.__verify_cache_integrity()
        return self.__mapping.__getitem__(key)[0] if self.__mapping.__contains__(key) else default

    def get_item_with_time(self, key: _KT) -> Tuple[_VT, float]:
        """
        Retrieve's the specified key's value from the mapping.

        Raises:
            KeyError: The key does not exist.

        Parameters:
            key (_KT): The key whose value to retrieve.

        Returns:
            (Tuple[_VT, float]): The key's value and the time the key expires.
        """

        self.__verify_cache_integrity()
        return self.__mapping.__getitem__(key)

    def clear(self) -> None:
        """
        Clears all key-value pairs from the mapping.

        Parameters:
            None.

        Returns:
            None.
        """

        self.__mapping.clear()
