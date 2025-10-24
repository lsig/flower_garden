"""
Group 6 Algorithm Visualizer

A custom GUI that shows each step of our force-directed layout algorithm:
1. Scatter seeds (random initial positions)
2. Separate overlapping plants (repulsive forces)
3. Create beneficial interactions (attractive forces)
4. Final layout with interactions

Uses pygame for visualization and keeps all code in group6 directory.
"""

import pygame
import numpy as np
import time
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from gardeners.group6.force_layout import (
    scatter_seeds,
    separate_overlapping_plants,
    create_beneficial_interactions,
    measure_garden_quality
)


class Group6Visualizer:
    def __init__(self, varieties: List[PlantVariety], width: int = 1200, height: int = 800):
        """
        Initialize the visualizer.
        
        Args:
            varieties: List of plant varieties to visualize
            width: Window width
            height: Window height
        """
        self.varieties = varieties
        self.width = width
        self.height = height
        
        # Garden dimensions (scaled to fit in window)
        self.garden_width = 16.0  # meters
        self.garden_height = 10.0  # meters
        self.scale = min(width * 0.7 / self.garden_width, height * 0.7 / self.garden_height)
        self.offset_x = width * 0.15
        self.offset_y = height * 0.15
        
        # Colors for species
        self.species_colors = {
            Species.RHODODENDRON: (255, 100, 100),  # Red
            Species.GERANIUM: (100, 255, 100),      # Green
            Species.BEGONIA: (100, 100, 255),      # Blue
        }
        
        # Algorithm state
        self.current_step = 0
        self.step_names = [
            "1. Scatter Seeds",
            "2. Separate Overlapping Plants", 
            "3. Create Beneficial Interactions",
            "4. Final Layout"
        ]
        
        # Layout data
        self.X = None
        self.labels = None
        self.inv = None
        self.score = 0.0
        self.interactions = []
        
        # Animation settings
        self.animation_speed = 0.1  # seconds per frame
        self.show_forces = True
        self.show_interactions = True
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Group 6 Algorithm Visualizer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        screen_x = int(self.offset_x + x * self.scale)
        screen_y = int(self.offset_y + y * self.scale)
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        x = (screen_x - self.offset_x) / self.scale
        y = (screen_y - self.offset_y) / self.scale
        return x, y
    
    def draw_garden_bounds(self):
        """Draw the garden boundary."""
        # Garden rectangle
        garden_rect = pygame.Rect(
            self.offset_x, self.offset_y,
            self.garden_width * self.scale,
            self.garden_height * self.scale
        )
        pygame.draw.rect(self.screen, (200, 200, 200), garden_rect, 2)
        
        # Garden label
        text = self.font.render("Garden (16m × 10m)", True, (0, 0, 0))
        self.screen.blit(text, (self.offset_x, self.offset_y - 30))
    
    def draw_plants(self, show_forces: bool = False):
        """Draw all plants with their species colors."""
        if self.X is None:
            return
            
        for i, (x, y) in enumerate(self.X):
            if i >= len(self.labels):
                continue
                
            variety = self.varieties[self.labels[i]]
            species = variety.species
            radius = variety.radius
            
            # Convert to screen coordinates
            screen_x, screen_y = self.world_to_screen(x, y)
            screen_radius = int(radius * self.scale)
            
            # Draw plant circle
            color = self.species_colors[species]
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), screen_radius)
            pygame.draw.circle(self.screen, (0, 0, 0), (screen_x, screen_y), screen_radius, 2)
            
            # Draw plant label
            label_text = f"{variety.name[:8]}"
            text = self.small_font.render(label_text, True, (0, 0, 0))
            text_rect = text.get_rect(center=(screen_x, screen_y))
            self.screen.blit(text, text_rect)
            
            # Draw radius indicator
            if self.current_step >= 1:  # Show after scatter step
                pygame.draw.circle(self.screen, (100, 100, 100), (screen_x, screen_y), screen_radius, 1)
    
    def draw_interactions(self):
        """Draw interaction lines between cross-species plants."""
        if not self.show_interactions or self.X is None:
            return
            
        for i in range(len(self.X)):
            for j in range(i + 1, len(self.X)):
                if i >= len(self.labels) or j >= len(self.labels):
                    continue
                    
                variety_i = self.varieties[self.labels[i]]
                variety_j = self.varieties[self.labels[j]]
                
                # Only draw cross-species interactions
                if variety_i.species == variety_j.species:
                    continue
                
                # Check if plants are in interaction range
                dist = np.linalg.norm(self.X[i] - self.X[j])
                interaction_dist = variety_i.radius + variety_j.radius
                
                if dist < interaction_dist:
                    # Draw interaction line
                    start_x, start_y = self.world_to_screen(self.X[i, 0], self.X[i, 1])
                    end_x, end_y = self.world_to_screen(self.X[j, 0], self.X[j, 1])
                    
                    # Color based on interaction strength
                    alpha = max(0, 255 - int((dist / interaction_dist) * 255))
                    color = (alpha, alpha, alpha)
                    pygame.draw.line(self.screen, color, (start_x, start_y), (end_x, end_y), 2)
    
    def draw_info_panel(self):
        """Draw information panel on the right side."""
        panel_x = self.width - 300
        panel_y = 20
        
        # Background
        panel_rect = pygame.Rect(panel_x, panel_y, 280, 400)
        pygame.draw.rect(self.screen, (240, 240, 240), panel_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), panel_rect, 2)
        
        y_offset = panel_y + 20
        
        # Current step
        step_text = self.font.render(f"Step: {self.step_names[self.current_step]}", True, (0, 0, 0))
        self.screen.blit(step_text, (panel_x + 10, y_offset))
        y_offset += 40
        
        # Algorithm info
        if self.X is not None:
            info_lines = [
                f"Plants: {len(self.X)}",
                f"Score: {self.score:.1f}",
                f"Interactions: {len(self.interactions)}",
                "",
                "Species Colors:",
                "🔴 Red: Rhododendron",
                "🟢 Green: Geranium", 
                "🔵 Blue: Begonia"
            ]
            
            for line in info_lines:
                if line:
                    text = self.small_font.render(line, True, (0, 0, 0))
                    self.screen.blit(text, (panel_x + 10, y_offset))
                y_offset += 20
        
        # Controls
        y_offset += 20
        controls = [
            "Controls:",
            "SPACE: Next step",
            "R: Reset",
            "I: Toggle interactions",
            "F: Toggle forces",
            "ESC: Quit"
        ]
        
        for line in controls:
            text = self.small_font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (panel_x + 10, y_offset))
            y_offset += 18
    
    def run_algorithm_step(self):
        """Run the next step of the algorithm."""
        if self.current_step == 0:
            # Step 1: Scatter seeds
            print(f"Scattering seeds for {len(self.varieties)} varieties...")
            self.X, self.labels, self.inv = scatter_seeds(
                self.varieties,
                W=self.garden_width,
                H=self.garden_height
            )
            print(f"Scattered {len(self.X)} plants")
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            
        elif self.current_step == 1:
            # Step 2: Separate overlapping plants
            self.X = separate_overlapping_plants(
                self.X,
                self.varieties,
                self.labels,
                iters=300
            )
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            
        elif self.current_step == 2:
            # Step 3: Create beneficial interactions
            self.X = create_beneficial_interactions(
                self.X,
                self.varieties,
                self.labels,
                self.inv,
                iters=200
            )
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            
        elif self.current_step == 3:
            # Step 4: Calculate final interactions
            self.calculate_interactions()
    
    def calculate_interactions(self):
        """Calculate and store interaction pairs."""
        self.interactions = []
        if self.X is None:
            return
            
        for i in range(len(self.X)):
            for j in range(i + 1, len(self.X)):
                if i >= len(self.labels) or j >= len(self.labels):
                    continue
                    
                variety_i = self.varieties[self.labels[i]]
                variety_j = self.varieties[self.labels[j]]
                
                # Only cross-species interactions
                if variety_i.species == variety_j.species:
                    continue
                
                dist = np.linalg.norm(self.X[i] - self.X[j])
                interaction_dist = variety_i.radius + variety_j.radius
                
                if dist < interaction_dist:
                    self.interactions.append((i, j))
    
    def reset(self):
        """Reset to the beginning."""
        self.current_step = 0
        self.X = None
        self.labels = None
        self.inv = None
        self.score = 0.0
        self.interactions = []
    
    def run(self):
        """Main visualization loop."""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if self.current_step < len(self.step_names) - 1:
                            self.current_step += 1
                            self.run_algorithm_step()
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_i:
                        self.show_interactions = not self.show_interactions
                    elif event.key == pygame.K_f:
                        self.show_forces = not self.show_forces
            
            # Clear screen
            self.screen.fill((255, 255, 255))
            
            # Draw garden
            self.draw_garden_bounds()
            
            # Draw plants and interactions
            self.draw_plants()
            self.draw_interactions()
            
            # Draw info panel
            self.draw_info_panel()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    """Run the visualizer with the fruits and veggies nursery."""
    import json
    
    # Load varieties
    config_path = Path(__file__).parent / 'config' / 'fruits_and_veggies.json'
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    varieties = []
    for item in data['varieties']:
        variety = PlantVariety(
            name=item['name'],
            radius=item['radius'],
            species=Species[item['species']],
            nutrient_coefficients={
                'R': item['nutrient_coefficients']['R'],
                'G': item['nutrient_coefficients']['G'],
                'B': item['nutrient_coefficients']['B']
            }
        )
        # Add multiple instances based on count
        for _ in range(item['count']):
            varieties.append(variety)
    
    print(f"Loaded {len(varieties)} plant varieties")
    
    if len(varieties) == 0:
        print("Error: No varieties loaded!")
        return
    
    # Create and run visualizer
    try:
        visualizer = Group6Visualizer(varieties)
        visualizer.run()
    except Exception as e:
        print(f"Error in visualizer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
