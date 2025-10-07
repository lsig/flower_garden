import json
import os
import tempfile

from core.nursery import Nursery
from core.plants.species import Species


class TestNurseryFileLoading:
    def test_load_valid_varieties_from_file(self):
        varieties_data = {
            "seed": 42,
            "varieties": [
                {
                    "name": "Test Rhodo",
                    "radius": 2,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {"R": 3.0, "G": -1.0, "B": -1.0},
                    "count": 3,
                },
                {
                    "name": "Test Geranium",
                    "radius": 1,
                    "species": "GERANIUM",
                    "nutrient_coefficients": {"R": -0.5, "G": 2.0, "B": -0.5},
                    "count": 2,
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            varieties = nursery.load_from_file(filepath)

            # Should have 5 total varieties (3 rhodos + 2 geraniums)
            assert len(varieties) == 5

            # First 3 should be rhodos
            assert all(v.species == Species.RHODODENDRON for v in varieties[:3])
            assert all(v.name == "Test Rhodo" for v in varieties[:3])

            # Last 2 should be geraniums
            assert all(v.species == Species.GERANIUM for v in varieties[3:])
            assert all(v.name == "Test Geranium" for v in varieties[3:])
        finally:
            os.unlink(filepath)

    def test_load_without_seed_uses_default(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "No Seed Plant",
                    "radius": 1,
                    "species": "BEGONIA",
                    "nutrient_coefficients": {"R": -0.5, "G": -0.5, "B": 1.5},
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            varieties = nursery.load_from_file(filepath)

            # Should use default seed 91
            assert len(varieties) == 1
        finally:
            os.unlink(filepath)

    def test_load_default_count_of_one(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Solo Plant",
                    "radius": 1,
                    "species": "BEGONIA",
                    "nutrient_coefficients": {"R": -0.5, "G": -0.5, "B": 1.5},
                    # No count specified
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            varieties = nursery.load_from_file(filepath)

            assert len(varieties) == 1
        finally:
            os.unlink(filepath)

    def test_load_multiple_varieties_with_different_counts(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Plant A",
                    "radius": 1,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {"R": 2.0, "G": -0.5, "B": -0.5},
                    "count": 1,
                },
                {
                    "name": "Plant B",
                    "radius": 2,
                    "species": "GERANIUM",
                    "nutrient_coefficients": {"R": -1.0, "G": 3.0, "B": -1.0},
                    "count": 4,
                },
                {
                    "name": "Plant C",
                    "radius": 3,
                    "species": "BEGONIA",
                    "nutrient_coefficients": {"R": -2.0, "G": -2.0, "B": 5.0},
                    "count": 2,
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            varieties = nursery.load_from_file(filepath)

            # Total: 1 + 4 + 2 = 7
            assert len(varieties) == 7

            # Check distribution
            rhodo_count = sum(1 for v in varieties if v.species == Species.RHODODENDRON)
            geranium_count = sum(1 for v in varieties if v.species == Species.GERANIUM)
            begonia_count = sum(1 for v in varieties if v.species == Species.BEGONIA)

            assert rhodo_count == 1
            assert geranium_count == 4
            assert begonia_count == 2
        finally:
            os.unlink(filepath)
