import json
import os
import tempfile

import pytest

from core.nursery import Nursery


class TestNurseryValidation:
    def test_invalid_radius_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Invalid Radius",
                    "radius": 5,  # Invalid!
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {"R": 3.0, "G": -1.0, "B": -1.0},
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Invalid radius"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_coefficient_out_of_range_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Out of Range",
                    "radius": 1,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {
                        "R": 5.0,  # Max should be 2*1 = 2
                        "G": -1.0,
                        "B": -1.0,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Invalid coefficient"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_negative_coefficient_out_of_range(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Too Negative",
                    "radius": 2,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {
                        "R": 2.0,
                        "G": -5.0,  # Min should be -2*2 = -4
                        "B": -1.0,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Invalid coefficient"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_negative_sum_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Negative Sum",
                    "radius": 2,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {
                        "R": 1.0,
                        "G": -2.0,
                        "B": -2.0,  # Sum = -3
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Net micronutrient production"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_zero_sum_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Zero Sum",
                    "radius": 2,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {
                        "R": 2.0,
                        "G": -1.0,
                        "B": -1.0,  # Sum = 0
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Net micronutrient production"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_rhododendron_wrong_signs_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Wrong Signs",
                    "radius": 2,
                    "species": "RHODODENDRON",
                    "nutrient_coefficients": {
                        "R": -1.0,  # Should be positive!
                        "G": 2.0,
                        "B": -0.5,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(
                ValueError, match="Invalid coefficients for Rhododendron"
            ):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_geranium_wrong_signs_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Wrong Signs",
                    "radius": 1,
                    "species": "GERANIUM",
                    "nutrient_coefficients": {
                        "R": 1.0,
                        "G": -0.5,  # Should be positive!
                        "B": -0.5,
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Invalid coefficients for Geranium"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_begonia_wrong_signs_raises_error(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Wrong Signs",
                    "radius": 3,
                    "species": "BEGONIA",
                    "nutrient_coefficients": {
                        "R": -1.0,
                        "G": 2.0,
                        "B": -0.5,  # Should be positive!
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            with pytest.raises(ValueError, match="Invalid coefficients for Begonia"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_valid_edge_case_coefficients(self):
        varieties_data = {
            "varieties": [
                {
                    "name": "Edge Case",
                    "radius": 3,
                    "species": "BEGONIA",
                    "nutrient_coefficients": {
                        "R": -6.0,  # At min limit
                        "G": -6.0,  # At min limit
                        "B": 6.0,  # At max limit, sum = -6
                    },
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(varieties_data, f)
            filepath = f.name

        try:
            nursery = Nursery()
            # This should fail because sum is -6
            with pytest.raises(ValueError, match="Net micronutrient production"):
                nursery.load_from_file(filepath)
        finally:
            os.unlink(filepath)
