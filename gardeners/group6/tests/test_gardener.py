#!/usr/bin/env python3
"""Quick test script for Group 6 Gardener."""

import sys
import time

from core.runner import GameRunner
from gardeners.group6.gardener import Gardener6
from gardeners.random_gardener import RandomGardener


def test_basic():
    """Test basic functionality."""
    print('=' * 60)
    print('TEST 1: Basic Functionality')
    print('=' * 60)

    runner = GameRunner(
        varieties_file='gardeners/group6/config/firstnursery.json', simulation_turns=100
    )

    try:
        result = runner.run(Gardener6)
        print('✅ Test passed!')
        print(f'   Final Growth: {result["final_growth"]:.2f}')
        print(f'   Plants Placed: {result["plants_placed"]}')
        print(f'   Placement Time: {result["placement_time"]:.2f}s')
        return True
    except Exception as e:
        print(f'❌ Test failed: {e}')
        return False


def test_time_limit():
    """Test that placement completes within time limit."""
    print('\n' + '=' * 60)
    print('TEST 2: Time Limit Compliance')
    print('=' * 60)

    runner = GameRunner(
        varieties_file='gardeners/group6/config/firstnursery.json',
        simulation_turns=100,
        time_limit=60.0,
    )

    try:
        result = runner.run(Gardener6)
        if result['placement_time'] < 60.0:
            print(f'✅ Test passed! ({result["placement_time"]:.2f}s < 60s)')
            return True
        else:
            print(f'❌ Test failed: {result["placement_time"]:.2f}s >= 60s')
            return False
    except Exception as e:
        print(f'❌ Test failed: {e}')
        return False


def test_vs_random():
    """Compare against random gardener baseline."""
    print('\n' + '=' * 60)
    print('TEST 3: Comparison with Random Baseline')
    print('=' * 60)

    config_file = 'gardeners/group6/config/firstnursery.json'
    turns = 300

    # Run our gardener
    runner = GameRunner(varieties_file=config_file, simulation_turns=turns)
    our_result = runner.run(Gardener6)

    # Run random gardener
    runner = GameRunner(varieties_file=config_file, simulation_turns=turns)
    random_result = runner.run(RandomGardener)

    print('\nOur Gardener:')
    print(f'  Final Growth: {our_result["final_growth"]:.2f}')
    print(f'  Plants Placed: {our_result["plants_placed"]}')
    print(f'  Placement Time: {our_result["placement_time"]:.2f}s')

    print('\nRandom Gardener:')
    print(f'  Final Growth: {random_result["final_growth"]:.2f}')
    print(f'  Plants Placed: {random_result["plants_placed"]}')
    print(f'  Placement Time: {random_result["placement_time"]:.2f}s')

    improvement = (our_result['final_growth'] / random_result['final_growth'] - 1) * 100
    print(f'\nImprovement: {improvement:+.1f}%')

    if our_result['final_growth'] > random_result['final_growth']:
        print('✅ Test passed! Our gardener beats random baseline.')
        return True
    else:
        print('⚠️  Warning: Random gardener performed better this time.')
        return False


def test_random_varieties():
    """Test with randomly generated varieties."""
    print('\n' + '=' * 60)
    print('TEST 4: Random Varieties')
    print('=' * 60)

    runner = GameRunner(random_count=15, simulation_turns=200)

    try:
        result = runner.run(Gardener6)
        print('✅ Test passed!')
        print(f'   Final Growth: {result["final_growth"]:.2f}')
        print(f'   Plants Placed: {result["plants_placed"]}')
        print(f'   Placement Time: {result["placement_time"]:.2f}s')
        return True
    except Exception as e:
        print(f'❌ Test failed: {e}')
        return False


def main():
    """Run all tests."""
    print('\n' + '=' * 60)
    print('GROUP 6 GARDENER TEST SUITE')
    print('=' * 60)

    tests = [
        test_basic,
        test_time_limit,
        test_vs_random,
        test_random_varieties,
    ]

    results = []
    start_time = time.time()

    for test in tests:
        results.append(test())

    elapsed = time.time() - start_time

    # Summary
    print('\n' + '=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)
    passed = sum(results)
    total = len(results)
    print(f'Passed: {passed}/{total}')
    print(f'Total Time: {elapsed:.2f}s')

    if passed == total:
        print('\n🎉 All tests passed!')
        return 0
    else:
        print(f'\n⚠️  {total - passed} test(s) failed or had warnings.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
