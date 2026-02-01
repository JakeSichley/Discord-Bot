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
    RunescapeHerb('Avantoe', '<:avantoe:1208996504107487272>', 5298, 261, 211),
    RunescapeHerb('Cadantine', '<:cadantine:1208996505126445106>', 5301, 265, 215),
    RunescapeHerb('Dwarf weed', '<:dwarf_weed:1208996506271752302>', 5303, 267, 217),
    RunescapeHerb('Guam', '<:guam:1208996507357806682>', 5291, 249, 199),
    RunescapeHerb('Harralander', '<:harralander:1208996508297334794>', 5294, 255, 205),
    RunescapeHerb('Huasca', '<:huasca:1464213161350533365>', 30088, 30097, 30094),
    RunescapeHerb('Irit', '<:irit:1208996509379469332>', 5297, 259, 209),
    RunescapeHerb('Kwuarm', '<:kwuarm:1208996546285150232>', 5299, 263, 213),
    RunescapeHerb('Lantadyme', '<:lantadyme:1208996547639902259>', 5302, 2481, 2485),
    RunescapeHerb('Marrentill', '<:marrentill:1208996549154046033>', 5292, 251, 201),
    RunescapeHerb('Ranarr', '<:ranarr:1208996550336974919>', 5295, 257, 207),
    RunescapeHerb('Snapdragon', '<:snapdragon:1208996582515548171>', 5300, 3000, 3051),
    RunescapeHerb('Tarromin', '<:tarromin:1208996583841206312>', 5293, 253, 203),
    RunescapeHerb('Toadflax', '<:toadflax:1208996584591986750>', 5296, 2998, 3049),
    RunescapeHerb('Torstol', '<:torstol:1208996586366050315>', 5304, 269, 219),
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

    compost_cost = item_data[ULTRACOMPOST_ID].high or 0

    return [
        profitability for herb in ALL_HERBS
        if (profitability := calculate_profitability(
            herb.name,
            herb.emoji,
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
        emoji: str,
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
        emoji (str): The
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

    cost = int((seed_cost + compost_cost / 2) * patches)
    clean_profit = int((grimy_cost * average_herbs * patches) - cost)
    grimy_profit = int((clean_cost * average_herbs * patches) - cost)

    return RunescapeHerbComparison(name, emoji, cost, clean_profit, grimy_profit)
