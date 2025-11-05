import argparse
from dataclasses import dataclass

from core.gardener import Gardener
from gardeners.group1.gardener import Gardener1
from gardeners.group2.adaptivegardener import Gardener2
from gardeners.group3.gardener import Gardener3
from gardeners.group4.gardener import Gardener4
from gardeners.group5.gardener import Gardener5
from gardeners.group6.gardener import Gardener6
from gardeners.group7.gardener import Gardener7
from gardeners.group8.gardener import Gardener8
from gardeners.group9.gardener import Gardener9
from gardeners.group10.gardener import Gardener10
from gardeners.random_gardener import RandomGardener

GARDENERS = {
    'g1': Gardener1,
    'g2': Gardener2,
    'g3': Gardener3,
    'g4': Gardener4,
    'g5': Gardener5,
    'g6': Gardener6,
    'g7': Gardener7,
    'g8': Gardener8,
    'g9': Gardener9,
    'g10': Gardener10,
    'gr': RandomGardener,
}


@dataclass
class Settings:
    gardener: type[Gardener]
    turns: int
    gui: bool
    file_path: str | None
    seed: int | None
    count: int | None


def settings() -> Settings:
    parser = argparse.ArgumentParser(description='Run a flower garden simulation.')

    parser.add_argument(
        '--gardener',
        required=True,
        type=str,
        choices=list(GARDENERS.keys()),
        help='Which gardener to run (g1-g10 or gr for random)',
    )

    parser.add_argument('--turns', type=int, default=100, help='Number of turns in the game')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--json_path',
        type=str,
        help='Path to configuration file (mutually exclusive with --random)',
    )
    group.add_argument(
        '--random',
        action='store_true',
        help='Use random generation (requires --count, optional --seed)',
    )

    parser.add_argument(
        '--count', type=int, default=20, help='Number of plants (only with --random)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=91,
        help='Seed for random number generator (only with --random)',
    )
    parser.add_argument('--gui', action='store_true', help='Enable GUI')
    args = parser.parse_args()

    if args.json_path and (args.count != 20 or args.seed != 91):
        parser.error('--count and --seed can only be used with --random')

    return Settings(
        gardener=GARDENERS[args.gardener],
        turns=args.turns,
        file_path=args.json_path if args.json_path else None,
        seed=args.seed if args.random else None,
        count=args.count if args.random else None,
        gui=args.gui,
    )
