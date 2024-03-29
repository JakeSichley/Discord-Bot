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

from enum import IntEnum, auto
from typing import Optional


class GuildFeature(IntEnum):
    """
    An Enum class that represents variables toggleable features for a guild.
    """

    TAG_DIRECT_INVOKE = auto()


def has_guild_feature(features: int, feature: GuildFeature) -> bool:
    """
    Checks whether the feature is active for this guild.

    Parameters:
        features (int): The features the guild currently has.
        feature (GuildFeature): The feature to check for.

    Returns:
        bool.
    """

    return bool(features & (1 << feature.value - 1))


def set_guild_feature(features: int, feature: GuildFeature, value: Optional[bool]) -> int:
    """
    Sets a feature status for this guild.

    Parameters:
        features (int): The features the guild currently has.
        feature (GuildFeature): The feature whose status to modify.
        value (Optional[bool]): The status of the feature.

    Returns:
        int.
    """

    if value is None:
        return features

    if value:
        return features | (1 << feature.value - 1)
    else:
        return features & ~(1 << feature.value - 1)
