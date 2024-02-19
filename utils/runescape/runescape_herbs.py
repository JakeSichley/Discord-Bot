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

from typing import Optional, List, Dict

from utils.runescape.runescape_data_classes import RunescapeHerb, RunescapeHerbComparison, RunescapeItem

ALL_HERBS = [
    RunescapeHerb('Toadflax', 5296, 2998, 3049),
    RunescapeHerb('Kwuarm', 5299, 263, 213),
    RunescapeHerb('Avantoe', 5298, 261, 211),
    RunescapeHerb('Ranarr', 5295, 265, 207),
    RunescapeHerb('Cadantine', 5301, 3000, 215),
    RunescapeHerb('Snapdragon', 5300, 269, 3051),
    RunescapeHerb('Torstol', 5304, 267, 219),
    RunescapeHerb('Dwarf weed', 5303, 2481, 217),
    RunescapeHerb('Lantadyme', 5302, 255, 2485),
    RunescapeHerb('Irit', 5297, 253, 209),
    RunescapeHerb('Harralander', 5294, 251, 205),
]

ULTRACOMPOST_ID = 21483


def generate_herb_comparison(
        item_data: Dict[int, RunescapeItem], patches: int, average_herbs: float
) -> List[RunescapeHerbComparison]:
    """
    Generates a list of RunescapeHerbComparisons.

    Parameters:
        item_data (Dict[int, RunescapeItem]): The current runescape item data.
        patches (int): The number of patches to use in the comparison.
        average_herbs (float): The average number of herbs per patch to use in the comparison.

    Returns:
        (List[RunescapeHerbComparison]).
    """

    compost_cost = item_data[21483].high or 0

    return [
        profitability for herb in ALL_HERBS
        if (profitability := calculate_profitability(
            herb.name,
            compost_cost,
            item_data[herb.seed_id].high,
            item_data[herb.clean_weed_id].low,
            item_data[herb.grimy_weed_id].low,
            patches,
            average_herbs
        ))
    ]


def calculate_profitability(
        name: str,
        compost_cost: float,
        seed_cost: Optional[float],
        clean_cost: Optional[float],
        grimy_cost: Optional[float],
        patches: int,
        average_herbs: float
) -> Optional[RunescapeHerbComparison]:
    """
    Returns the smallest profitable amount (between grimy and clean).

    Parameters:
        name (str): The name of the herb.
        compost_cost (float): The cost of compost.
        seed_cost (Optional[float]): The cost of the seed.
        clean_cost (Optional[float]): The cost of the clean herb.
        grimy_cost (Optional[float]): The cost of the grimy herb.
        patches (int): The number of patches in the farm run.
        average_herbs (float): The average number of herbs harvested per patch.

    Returns:
        (Optional[RunescapeHerbComparison]): The generated comparison for this herb.
    """

    if not seed_cost or not clean_cost or not grimy_cost:
        return None

    cost = (seed_cost + compost_cost / 2) * patches
    clean_profit = (grimy_cost * average_herbs * patches) - cost
    grimy_profit = (clean_cost * average_herbs * patches) - cost

    return RunescapeHerbComparison(name, cost, clean_profit, grimy_profit)
