"""
MIT License

Copyright (c) 2019-2023 Jake Sichley

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

from enum import IntFlag, auto


class GuildFeature(IntFlag):
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

    return bool(features & feature)


def set_guild_feature(features: int, feature: GuildFeature, value: bool) -> int:
    """
    Sets a feature status for this guild.

    Parameters:
        features (int): The features the guild currently has.
        feature (GuildFeature): The feature whose status to modify.
        value (bool): The status of the feature.

    Returns:
        int.
    """

    if value:
        return features | feature
    else:
        return features ^ feature
