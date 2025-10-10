import random

from core.runner import GameRunner
from core.settings import settings


def main():
    args = settings()

    if args.seed:
        random.seed(args.seed)

    if args.file_path:
        runner = GameRunner(varieties_file=args.file_path, simulation_turns=args.turns)
    else:
        runner = GameRunner(random_count=args.count, simulation_turns=args.turns)

    if args.gui:
        runner.run_gui(args.gardener)
    else:
        result = runner.run(args.gardener)

        print(f"\nResults for {args.gardener.__name__}:")
        print(f"  Final Growth: {result['final_growth']:.2f}")
        print(f"  Plants Placed: {result['plants_placed']}")
        print(f"  Placement Time: {result['placement_time']:.2f}s")


if __name__ == "__main__":
    main()
