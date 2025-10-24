#!/usr/bin/env python3
"""
Limited visualizer that only shows a subset of varieties to avoid performance issues.
"""

import pygame
import numpy as np
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from gardeners.group6.force_layout import scatter_seeds, separate_overlapping_plants, create_beneficial_interactions, measure_garden_quality


def load_limited_varieties(config_file: str, max_varieties: int = 15):
    """Load a limited number of varieties for visualization."""
    config_path = Path(__file__).parent / 'config' / config_file
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    varieties = []
    count = 0
    
    for item in data['varieties']:
        if count >= max_varieties:
            break
            
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
        
        # Add limited instances
        instances_to_add = min(item['count'], max_varieties - count)
        for _ in range(instances_to_add):
            varieties.append(variety)
            count += 1
            if count >= max_varieties:
                break
    
    return varieties


class LimitedVisualizer:
    def __init__(self, varieties, width=1000, height=700):
        self.varieties = varieties
        self.width = width
        self.height = height
        
        # Garden dimensions
        self.garden_width = 16.0
        self.garden_height = 10.0
        self.scale = min(width * 0.6 / self.garden_width, height * 0.6 / self.garden_height)
        self.offset_x = width * 0.2
        self.offset_y = height * 0.2
        
        # Colors
        self.species_colors = {
            Species.RHODODENDRON: (255, 100, 100),
            Species.GERANIUM: (100, 255, 100),
            Species.BEGONIA: (100, 100, 255)
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
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Group 6 Algorithm Visualizer (Limited)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
    
    def world_to_screen(self, x, y):
        screen_x = int(self.offset_x + x * self.scale)
        screen_y = int(self.offset_y + y * self.scale)
        return screen_x, screen_y
    
    def draw_garden_bounds(self):
        garden_rect = pygame.Rect(
            self.offset_x, self.offset_y,
            self.garden_width * self.scale,
            self.garden_height * self.scale
        )
        pygame.draw.rect(self.screen, (200, 200, 200), garden_rect, 2)
        
        text = self.font.render("Garden (16m × 10m)", True, (0, 0, 0))
        self.screen.blit(text, (self.offset_x, self.offset_y - 30))
    
    def draw_plants(self):
        if self.X is None:
            return
            
        for i, (x, y) in enumerate(self.X):
            if i >= len(self.labels):
                continue
                
            variety = self.varieties[self.labels[i]]
            species = variety.species
            radius = variety.radius
            
            screen_x, screen_y = self.world_to_screen(x, y)
            screen_radius = max(3, int(radius * self.scale))
            
            color = self.species_colors[species]
            pygame.draw.circle(self.screen, color, (screen_x, screen_y), screen_radius)
            pygame.draw.circle(self.screen, (0, 0, 0), (screen_x, screen_y), screen_radius, 2)
            
            # Draw label
            label_text = variety.name[:6]
            text = self.small_font.render(label_text, True, (0, 0, 0))
            text_rect = text.get_rect(center=(screen_x, screen_y))
            self.screen.blit(text, text_rect)
    
    def draw_interactions(self):
        if self.X is None:
            return
            
        for i in range(len(self.X)):
            for j in range(i + 1, len(self.X)):
                if i >= len(self.labels) or j >= len(self.labels):
                    continue
                    
                variety_i = self.varieties[self.labels[i]]
                variety_j = self.varieties[self.labels[j]]
                
                if variety_i.species == variety_j.species:
                    continue
                
                dist = np.linalg.norm(self.X[i] - self.X[j])
                interaction_dist = variety_i.radius + variety_j.radius
                
                if dist < interaction_dist:
                    start_x, start_y = self.world_to_screen(self.X[i, 0], self.X[i, 1])
                    end_x, end_y = self.world_to_screen(self.X[j, 0], self.X[j, 1])
                    pygame.draw.line(self.screen, (100, 100, 100), (start_x, start_y), (end_x, end_y), 1)
    
    def draw_info_panel(self):
        panel_x = self.width - 250
        panel_y = 20
        
        panel_rect = pygame.Rect(panel_x, panel_y, 230, 300)
        pygame.draw.rect(self.screen, (240, 240, 240), panel_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), panel_rect, 2)
        
        y_offset = panel_y + 20
        
        # Current step
        step_text = self.font.render(f"Step: {self.step_names[self.current_step]}", True, (0, 0, 0))
        self.screen.blit(step_text, (panel_x + 10, y_offset))
        y_offset += 40
        
        # Info
        if self.X is not None:
            info_lines = [
                f"Plants: {len(self.X)}",
                f"Score: {self.score:.1f}",
                "",
                "Controls:",
                "SPACE: Next step",
                "R: Reset",
                "ESC: Quit"
            ]
            
            for line in info_lines:
                if line:
                    text = self.small_font.render(line, True, (0, 0, 0))
                    self.screen.blit(text, (panel_x + 10, y_offset))
                y_offset += 20
    
    def run_algorithm_step(self):
        if self.current_step == 0:
            print("Step 1: Scattering seeds...")
            self.X, self.labels, self.inv = scatter_seeds(
                self.varieties, W=self.garden_width, H=self.garden_height
            )
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            print(f"Scattered {len(self.X)} plants, score: {self.score:.1f}")
            
        elif self.current_step == 1:
            print("Step 2: Separating overlapping plants...")
            self.X = separate_overlapping_plants(self.X, self.varieties, self.labels, iters=200)
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            print(f"Separated plants, score: {self.score:.1f}")
            
        elif self.current_step == 2:
            print("Step 3: Creating beneficial interactions...")
            self.X = create_beneficial_interactions(
                self.X, self.varieties, self.labels, self.inv, iters=150
            )
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            print(f"Created interactions, score: {self.score:.1f}")
            
        elif self.current_step == 3:
            print("Step 4: Final layout complete!")
    
    def reset(self):
        self.current_step = 0
        self.X = None
        self.labels = None
        self.inv = None
        self.score = 0.0
    
    def run(self):
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
            
            # Clear screen
            self.screen.fill((255, 255, 255))
            
            # Draw everything
            self.draw_garden_bounds()
            self.draw_plants()
            self.draw_interactions()
            self.draw_info_panel()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    print("Loading limited varieties...")
    varieties = load_limited_varieties('fruits_and_veggies.json', max_varieties=15)
    print(f"Loaded {len(varieties)} varieties")
    
    visualizer = LimitedVisualizer(varieties)
    visualizer.run()


if __name__ == '__main__':
    main()
