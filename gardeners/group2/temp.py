from contextlib import suppress
from core.garden import Garden
from core.gardener import Gardener
from core.micronutrients import Micronutrient
from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.point import Position


class Gardener2(Gardener):
    STEP = 0.5  # Increased step for faster grid-based placement (was 0.2, now 0.5)

    def __init__(self, garden: Garden, varieties: list[PlantVariety]):
        super().__init__(garden, varieties)
        self.min_available_radius = (
            min([v.radius for v in varieties], default=1.0) if varieties else 1.0
        )
        self.max_radius = max([v.radius for v in varieties], default=1.0) if varieties else 1.0

    # --- Utility Methods (Scoring and Balancing) ---

    def _calculate_net_production_score(self, variety: PlantVariety) -> float:
        """Calculates a composite score based on production efficiency and radius."""
        coeffs = variety.nutrient_coefficients
        production = 0.0
        total_consumption = 0.0

        if variety.species == Species.RHODODENDRON:
            production = coeffs.get(Micronutrient.R, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.G, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.GERANIUM:
            production = coeffs.get(Micronutrient.G, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.B, 0.0)
            )
        elif variety.species == Species.BEGONIA:
            production = coeffs.get(Micronutrient.B, 0.0)
            total_consumption = abs(coeffs.get(Micronutrient.R, 0.0)) + abs(
                coeffs.get(Micronutrient.G, 0.0)
            )
        else:
            return 0.0

        if total_consumption <= 0:
            return float('inf')

        base_ratio = production / total_consumption
        radius_multiplier = 10 - (variety.radius * variety.radius) 

        composite_score = base_ratio * radius_multiplier
        return composite_score

    def _get_sorted_varieties(self) -> list[tuple[float, PlantVariety]]:
        """Sorts all available varieties by their composite score (descending)."""
        scored_varieties = []
        for variety in self.varieties:
            score = self._calculate_net_production_score(variety)
            scored_varieties.append((score, variety))
        scored_varieties.sort(key=lambda x: x[0], reverse=True)
        return scored_varieties

    def _get_current_net_nutrients(self) -> dict[Micronutrient, float]:
        """Calculates the current net amount of each micronutrient in the system."""
        net_nutrients = {m: 0.0 for m in Micronutrient}
        for plant in self.garden.plants:
            coeffs = plant.variety.nutrient_coefficients
            for nutrient, amount in coeffs.items():
                net_nutrients[nutrient] += amount
        return net_nutrients

    def _get_species_for_most_deficient_nutrient(self) -> set[str]:
        """
        Identifies the species that produces the most deficient micronutrient.
        """
        net_nutrients = self._get_current_net_nutrients()
        
        if not net_nutrients:
            most_deficient_nutrient = Micronutrient.R
        else:
            min_net_value = min(net_nutrients.values())
            deficient_nutrients = [
                nutrient for nutrient, value in net_nutrients.items() if value == min_net_value
            ]
            if Micronutrient.R in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.R
            elif Micronutrient.G in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.G
            elif Micronutrient.B in deficient_nutrients:
                most_deficient_nutrient = Micronutrient.B
            else:
                return set()

        if most_deficient_nutrient == Micronutrient.R:
            return {Species.RHODODENDRON.value}
        elif most_deficient_nutrient == Micronutrient.G:
            return {Species.GERANIUM.value}
        elif most_deficient_nutrient == Micronutrient.B:
            return {Species.BEGONIA.value}

        return set()

    _get_underrepresented_species = _get_species_for_most_deficient_nutrient

    def _find_best_variety_to_plant(
        self, scored_varieties: list[tuple[float, PlantVariety]], underrepresented_species: set[str]
    ) -> tuple[float, PlantVariety] | None:
        """Selects the single highest-scoring variety that belongs to the "fixing" species."""
        if not scored_varieties or not underrepresented_species:
            return None
        target_species_value = next(iter(underrepresented_species))
        for score, variety in scored_varieties:
            if variety.species.value == target_species_value:
                return (score, variety)
        return None

    # --- Placement Scoring Methods ---

    def _get_interaction_counts(self, variety: PlantVariety, position: Position) -> dict[Species, int]:
        """Counts the number of interactions for each species."""
        counts = {s: 0 for s in Species}
        new_radius = variety.radius

        for existing_plant in self.garden.plants:
            distance = self.garden._calculate_distance(position, existing_plant.position)
            interaction_distance = new_radius + existing_plant.variety.radius

            if distance < interaction_distance:
                counts[existing_plant.variety.species] += 1
        return counts

    def _calculate_placement_score(self, variety: PlantVariety, position: Position) -> float:
        """
        Calculates a placement score that maximizes balanced inter-species interactions.
        Score = (Minimum Interacting Species Count * 100) + (Total Interacting Species Count)
        """
        counts = self._get_interaction_counts(variety, position)
        current_species = variety.species

        # Interactions with other species only
        inter_species_counts = [
            count for species, count in counts.items() 
            if species != current_species
        ]

        # Calculate Intra-species interactions (interactions with self)
        intra_species_count = counts.get(current_species, 0)
        
        # PENALTY: Disqualify positions with self-species interaction
        if intra_species_count > 0:
            return -1.0 

        # If there are no inter-species interactions, the score is 0
        if not inter_species_counts or sum(inter_species_counts) == 0:
            return 0.0

        min_inter_count = min(inter_species_counts)
        total_inter_count = sum(inter_species_counts)

        # Score rewards minimum count (balance) most heavily, then total count (density)
        score = (min_inter_count * 100) + total_inter_count

        return score


    def _generate_placement_grid(self) -> list[Position]:
        """Generates a grid of candidate positions across the garden."""
        positions = []
        step = self.STEP
        start_x = step
        start_y = step

        y = start_y
        while y < self.garden.height - step:
            x = start_x
            while x < self.garden.width - step:
                positions.append(Position(x, y))
                x += step
            y += step
        return positions

    # --- Cluster Methods ---

    def _get_best_variety_per_species(self) -> dict[Species, PlantVariety]:
        """Gets the highest-scoring variety for each species."""
        scored_varieties = self._get_sorted_varieties()
        best_of_each = {}
        for _, variety in scored_varieties:
            if variety.species not in best_of_each:
                best_of_each[variety.species] = variety
        return best_of_each

    def _get_cluster_seed_positions(self) -> list[Position]:
        """
        Calculates four non-overlapping cluster centers in the specified order:
        Top-Left (0), Bottom-Right (1), Top-Right (2), Bottom-Left (3)
        """
        R = self.max_radius + 1.0  
        W, H = self.garden.width, self.garden.height
        
        # Order: TL, BR, TR, BL
        centers = [
            Position(R, H - R),      # Index 0: Top-Left
            Position(W - R, R),      # Index 1: Bottom-Right
            Position(W - R, H - R),  # Index 2: Top-Right
            Position(R, R),          # Index 3: Bottom-Left
        ]
        return centers

    def _grow_cluster(self, center: Position, available_varieties: list[PlantVariety], max_plants: int, cluster_index: int) -> list[PlantVariety]:
        """
        Grows a cluster, using the cluster_index to seed the first plant.
        """
        used_varieties = []
        cluster_plants = [] 
        
        local_positions = []
        grid_size = 3 * self.max_radius 
        
        for i in range(-int(grid_size / self.STEP), int(grid_size / self.STEP) + 1):
            for j in range(-int(grid_size / self.STEP), int(grid_size / self.STEP) + 1):
                x = center.x + i * self.STEP
                y = center.y + j * self.STEP
                local_positions.append(Position(x, y))

        local_positions.sort(key=lambda p: self.garden._calculate_distance(p, center)) 

        all_scored_varieties = self._get_sorted_varieties()

        # Define the seeding sequence: R, G, B, R (using modulo 3 for index)
        seeding_species_map = {
            0: Species.RHODODENDRON, # Top-Left
            1: Species.GERANIUM,     # Bottom-Right
            2: Species.BEGONIA,      # Top-Right
            3: Species.RHODODENDRON, # Bottom-Left (Reruns R since there are only 3 species)
        }
        
        starting_species = seeding_species_map[cluster_index]


        for _ in range(max_plants): 
            
            plant_to_place = None
            best_position = None  # Reset best_position for each iteration
            
            if not cluster_plants: 
                # SEEDING LOGIC: Determine the variety to place
                top_variety_tuple = next(
                    ((s, v) for s, v in all_scored_varieties if v in available_varieties and v.species == starting_species), 
                    None
                )
                plant_to_place = top_variety_tuple[1] if top_variety_tuple else None

                # *** MODIFICATION START ***
                # For the FIRST plant, explicitly try to place it at the designated corner 'center'.
                if plant_to_place and self.garden.can_place_plant(plant_to_place, center):
                    best_position = center
                # If the center is not valid (e.g., radius too big), we let best_position remain None,
                # which will cause the loop to break, as the intended corner position isn't usable.
                # *** MODIFICATION END ***
            
            else:
                # Subsequent plants: Use global deficiency check to find variety
                underrepresented = self._get_species_for_most_deficient_nutrient() 
                target_species = next(iter(underrepresented), None)

                if target_species:
                    target_variety_tuple = self._find_best_variety_to_plant(
                        [(s, v) for s, v in all_scored_varieties if v in available_varieties], 
                        underrepresented
                    )
                    if target_variety_tuple:
                        plant_to_place = target_variety_tuple[1]

            if not plant_to_place:
                break 

            # --- Placement Logic (Only runs for SUBSEQUENT plants) ---
            if cluster_plants and best_position is None:
                max_score = -2.0 
                for position in local_positions:
                    if not self.garden.can_place_plant(plant_to_place, position):
                        continue

                    # MAXIMIZE BALANCE SCORE
                    score = self._calculate_placement_score(plant_to_place, position) 
                    
                    if score > max_score: 
                        max_score = score
                        best_position = position
                
                # If no suitable position was found (score >= 0)
                if max_score < 0:
                    best_position = None

            
            # --- Execute Placement ---
            # Placement proceeds if a valid best_position was found (either 'center' or scored)
            if best_position: 
                plant = self.garden.add_plant(plant_to_place, best_position)
                if plant:
                    cluster_plants.append(plant)
                    used_varieties.append(plant_to_place)
                    available_varieties[:] = [v for v in available_varieties if id(v) != id(plant_to_place)]
                else:
                    break
            else:
                break
            
        for i in used_varieties:
            print(i)
            print("-------")
        return used_varieties

    # --- Main Cultivation Method ---

    def cultivate_garden(self) -> None:
        
        # 1. Setup Phase
        all_varieties = list(self.varieties) 
        # Centers are now ordered: TL(0), BR(1), TR(2), BL(3)
        cluster_centers = self._get_cluster_seed_positions()
        MAX_PLANTS_PER_CLUSTER = 15 

        # 2. Clustering Phase: Grow isolated, balanced clusters
        for index, center in enumerate(cluster_centers):
            # Pass the index to determine the seeding species
            self._grow_cluster(center, all_varieties, MAX_PLANTS_PER_CLUSTER, index)

        # 3. Space-Filling/Greedy Phase
        candidate_positions = self._generate_placement_grid()
        
        while all_varieties:
            all_scored_varieties = self._get_sorted_varieties()
            plantable_varieties = [
                (score, variety) for score, variety in all_scored_varieties 
                if variety in all_varieties
            ]

            underrepresented_species = self._get_species_for_most_deficient_nutrient()
            if not underrepresented_species:
                break
                
            best_variety_tuple = self._find_best_variety_to_plant(
                plantable_varieties, underrepresented_species
            )
            
            if best_variety_tuple is None:
                break

            best_variety = best_variety_tuple[1]
            best_position = None
            max_score = -2.0 

            # Place the remaining plants in the best available spot (max balance score)
            for position in candidate_positions:
                if not self.garden.can_place_plant(best_variety, position):
                    continue

                # MAXIMIZE BALANCE SCORE
                score = self._calculate_placement_score(best_variety, position)

                if score > max_score:
                    max_score = score
                    best_position = position
            
            if best_position and max_score >= 0:
                plant = self.garden.add_plant(best_variety, best_position)

                if plant is not None:
                    all_varieties[:] = [v for v in all_varieties if id(v) != id(best_variety)]
                    with suppress(ValueError):
                        candidate_positions.remove(best_position)
                else:
                    break 
            else:
                break