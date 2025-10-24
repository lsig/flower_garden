"""Interactive visualizer for the force-directed layout algorithm."""

import pygame
import numpy as np
import sys
import json
from pathlib import Path
from typing import List, Tuple, Optional
from tqdm import tqdm

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from core.micronutrients import Micronutrient
from gardeners.group6.force_layout import (
    scatter_seeds,
    separate_overlapping_plants,
    create_beneficial_interactions,
    measure_garden_quality
)


class AlgorithmVisualizer:
    def __init__(self, varieties: List[PlantVariety], width=1280, height=800):
        """
        Initialize the algorithm visualizer using the same style as the existing GUI.
        
        Args:
            varieties: List of plant varieties to visualize
            width: Window width
            height: Window height
        """
        pygame.init()
        
        self.varieties = varieties
        self.width = width
        self.height = height
        
        # Garden dimensions (same as existing visualizer)
        self.garden_width = 16.0
        self.garden_height = 10.0
        
        # Same styling as existing visualizer
        self.bg_color = (240, 240, 240)
        self.grid_color = (200, 200, 200)
        self.interaction_line_color = (100, 100, 100)
        
        # Same species colors as existing visualizer
        self.species_colors = {
            Species.RHODODENDRON: (220, 20, 60),  # Crimson Red
            Species.GERANIUM: (46, 139, 87),      # Sea Green
            Species.BEGONIA: (65, 105, 225),      # Royal Blue
        }
        
        # Same layout as existing visualizer
        self.padding = 80
        info_pane_width = 220
        self.scale_x = (width - self.padding * 2 - info_pane_width) / self.garden_width
        self.scale_y = (height - self.padding * 2) / self.garden_height
        self.offset_x = self.padding
        self.offset_y = self.padding
        
        # Same fonts as existing visualizer
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        self.tiny_font = pygame.font.Font(None, 20)
        
        # Algorithm state
        self.current_step = -1  # Start before step 0 so first SPACE runs step 0
        self.step_names = [
            "1. Scatter Seeds",
            "2. Separate Overlapping Plants", 
            "3. Create Beneficial Interactions",
            "4. Final Layout"
        ]
        
        # Animation state for iterative steps
        self.animating = False
        self.animation_paused = False
        self.animation_step = 0
        self.max_animation_steps = 0
        self.animation_data = None  # Store intermediate positions
        
        # Layout data
        self.X = None
        self.labels = None
        self.inv = None
        self.score = 0.0
        self.interactions = []
        
        # UI state (same as existing visualizer)
        self.running = True
        self.paused = True
        self.debug_mode = False
        self.clock = pygame.time.Clock()
        
        # Initialize display
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Group 6 Algorithm Visualizer')
    
    def garden_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Convert garden coordinates to screen coordinates (same as existing)."""
        return int(x * self.scale_x + self.offset_x), int(y * self.scale_y + self.offset_y)
    
    def draw_grid(self):
        """Draw garden boundaries and grid (same as existing visualizer)."""
        garden_width_px = self.garden_width * self.scale_x
        garden_height_px = self.garden_height * self.scale_y
        border_rect = pygame.Rect(self.offset_x, self.offset_y, garden_width_px, garden_height_px)
        pygame.draw.rect(self.screen, (0, 0, 0), border_rect, 2)
        
        # Draw grid lines
        for i in range(1, int(self.garden_width)):
            x = self.offset_x + i * self.scale_x
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (x, self.offset_y),
                (x, self.offset_y + garden_height_px),
            )
        
        for i in range(1, int(self.garden_height)):
            y = self.offset_y + i * self.scale_y
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (self.offset_x, y),
                (self.offset_x + garden_width_px, y),
            )
    
    def draw_interactions(self):
        """Draw lines between interacting plants (same style as existing)."""
        if self.X is None or not self.interactions:
            return
            
        for i, j in self.interactions:
            if i >= len(self.X) or j >= len(self.X):
                continue
                
            pos1 = self.garden_to_screen(self.X[i, 0], self.X[i, 1])
            pos2 = self.garden_to_screen(self.X[j, 0], self.X[j, 1])
            pygame.draw.line(self.screen, self.interaction_line_color, pos1, pos2, 2)
    
    def draw_plants(self):
        """Draw all plants (same style as existing visualizer)."""
        if self.X is None:
            return
            
        for i, (x, y) in enumerate(self.X):
            if i >= len(self.labels):
                continue
                
            variety = self.varieties[self.labels[i]]
            pos = self.garden_to_screen(x, y)
            color = self.species_colors[variety.species]
            
            # Draw root radius circle (same as existing)
            root_radius = int(variety.radius * min(self.scale_x, self.scale_y))
            pygame.draw.circle(self.screen, color, pos, root_radius, 2)
            
            # Draw plant circle (same as existing)
            plant_radius = max(5, int(root_radius * 0.6))
            pygame.draw.circle(self.screen, color, pos, plant_radius)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, plant_radius, 1)
    
    def draw_debug_info(self):
        """Draw detailed plant information (same as existing visualizer)."""
        if not self.debug_mode or self.X is None:
            return
        
        for i, (x, y) in enumerate(self.X):
            if i >= len(self.labels):
                continue
                
            variety = self.varieties[self.labels[i]]
            pos = self.garden_to_screen(x, y)
            
            # Get coefficients
            coeffs = variety.nutrient_coefficients
            r_coeff = coeffs[Micronutrient.R]
            g_coeff = coeffs[Micronutrient.G]
            b_coeff = coeffs[Micronutrient.B]
            
            # Create debug text lines (same as existing)
            debug_lines = [
                f'#{variety.name[:10]}',
                f'Radius: {variety.radius}m',
                f'R:{r_coeff:+.1f}',
                f'G:{g_coeff:+.1f}',
                f'B:{b_coeff:+.1f}',
                f'Species: {variety.species.name}',
            ]
            
            # Draw semi-transparent background (same as existing)
            line_height = 18
            box_height = len(debug_lines) * line_height + 10
            box_width = 150
            box_x = pos[0] + 25
            box_y = pos[1] - box_height // 2
            
            # Create surface with transparency
            debug_surface = pygame.Surface((box_width, box_height))
            debug_surface.set_alpha(235)
            debug_surface.fill((255, 255, 230))
            self.screen.blit(debug_surface, (box_x, box_y))
            
            # Draw border
            pygame.draw.rect(self.screen, (0, 0, 0), (box_x, box_y, box_width, box_height), 1)
            
            # Draw text lines
            for j, line in enumerate(debug_lines):
                text = self.tiny_font.render(line, True, (0, 0, 0))
                self.screen.blit(text, (box_x + 5, box_y + 5 + j * line_height))
    
    def draw_info_panel(self):
        """Draw info panel (same style as existing visualizer)."""
        info_pane_x = self.width - self.padding - 170
        y_offset = self.offset_y
        
        # Draw algorithm info
        current_step_name = self.step_names[self.current_step] if 0 <= self.current_step < len(self.step_names) else "Ready to start"
        
        # Animation progress
        animation_info = ""
        if self.animating and self.animation_data:
            progress = (self.animation_step / len(self.animation_data)) * 100
            animation_info = f"Frame: {self.animation_step}/{len(self.animation_data)-1} ({progress:.0f}%)"
        
        info_lines = [
            'Group 6 Algorithm',
            f'Step: {current_step_name}',
            f'Score: {self.score:.1f}',
            f'Plants: {len(self.X) if self.X is not None else 0}',
            f'Interactions: {len(self.interactions)}',
            animation_info,
            '',
            f'{"PAUSED" if self.paused else "RUNNING"}',
            f'{"DEBUG ON" if self.debug_mode else "DEBUG OFF"}',
        ]
        
        for line in info_lines:
            if line:
                text = self.small_font.render(line, True, (0, 0, 0))
                self.screen.blit(text, (info_pane_x, y_offset))
                y_offset += 30
        
        y_offset += 20
        
        # Draw controls (same as existing)
        control_lines = [
            'Controls:',
            'SPACE: Next step / Next frame',
            'RIGHT: Step forward',
            'D: Debug mode',
            'R: Reset',
            'Q: Quit',
        ]
        
        for line in control_lines:
            text = self.small_font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (info_pane_x, y_offset))
            y_offset += 30
        
        y_offset += 20
        
        # Draw species legend (same as existing)
        title = self.font.render('Species:', True, (0, 0, 0))
        self.screen.blit(title, (info_pane_x, y_offset))
        y_offset += 40
        
        for species, color in self.species_colors.items():
            name = species.name.replace('_', ' ').title()
            text = self.small_font.render(name, True, (0, 0, 0))
            
            circle_y = y_offset + text.get_height() // 2
            pygame.draw.circle(self.screen, color, (info_pane_x + 15, circle_y), 10)
            pygame.draw.circle(self.screen, (0, 0, 0), (info_pane_x + 15, circle_y), 10, 1)
            
            self.screen.blit(text, (info_pane_x + 35, y_offset))
            y_offset += 35
    
    def handle_events(self):
        """Handle pygame events (same as existing visualizer)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_q
            ):
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.animating:
                        # Step through animation frames one by one
                        if self.animation_step < len(self.animation_data) - 1:
                            self.animation_step += 1
                            self.X = self.animation_data[self.animation_step].copy()
                            print(f"Animation frame {self.animation_step}/{len(self.animation_data)-1}")
                        else:
                            # Animation complete
                            self.animating = False
                            self.animation_paused = False
                            self.animation_step = 0
                            print("Animation complete!")
                    else:
                        self.next_algorithm_step()
                elif event.key == pygame.K_RIGHT and self.paused:
                    self.next_algorithm_step()
                elif event.key == pygame.K_d:
                    self.debug_mode = not self.debug_mode
                elif event.key == pygame.K_r:
                    self.reset_algorithm()
    
    def next_algorithm_step(self):
        """Run the next step of the algorithm."""
        if self.current_step >= len(self.step_names) - 1:
            return
            
        self.current_step += 1
        self.run_algorithm_step()
    
    def run_algorithm_step(self):
        """Run the current step of the algorithm."""
        if self.current_step == 0:
            # Step 1: Scatter seeds
            print("Step 1: Scattering seeds...")
            self.X, self.labels, self.inv = scatter_seeds(
                self.varieties,
                W=self.garden_width,
                H=self.garden_height
            )
            self.score = measure_garden_quality(self.X, self.varieties, self.labels)
            print(f"Scattered {len(self.X)} plants, score: {self.score:.1f}")
            
        elif self.current_step == 1:
            # Step 2: Separate overlapping plants (with animation)
            if self.X is None:
                print("Error: No plants to separate. Run step 1 first.")
                return
            print("Step 2: Separating overlapping plants...")
            self.start_animation("separate_overlapping_plants", 100)  # Reduced from 300 to 100
            
        elif self.current_step == 2:
            # Step 3: Create beneficial interactions (with animation)
            if self.X is None:
                print("Error: No plants to optimize. Run previous steps first.")
                return
            print("Step 3: Creating beneficial interactions...")
            self.start_animation("create_beneficial_interactions", 50)  # Reduced from 200 to 50
            
        elif self.current_step == 3:
            # Step 4: Calculate final interactions
            if self.X is None:
                print("Error: No plants to analyze. Run previous steps first.")
                return
            print("Step 4: Final layout complete!")
            self.calculate_interactions()
    
    def start_animation(self, animation_type: str, max_steps: int):
        """Start animating the iterative algorithm steps."""
        self.animating = True
        self.animation_step = 0
        self.max_animation_steps = max_steps
        self.animation_data = []
        
        # Capture initial state
        self.animation_data.append(self.X.copy())
        
        # Run the algorithm with animation
        if animation_type == "separate_overlapping_plants":
            self.X = self.animate_separate_overlapping_plants()
        elif animation_type == "create_beneficial_interactions":
            self.X = self.animate_create_beneficial_interactions()
        
        # Animation complete
        self.animating = False
        self.score = measure_garden_quality(self.X, self.varieties, self.labels)
        print(f"Animation complete, score: {self.score:.1f}")
    
    def animate_separate_overlapping_plants(self):
        """Animate the separate overlapping plants algorithm."""
        X = self.X.copy()
        step_size = 0.1
        jitter_interval = 20
        jitter_amount = 0.01
        
        print("Separating overlapping plants...")
        for i in tqdm(range(self.max_animation_steps), desc="Step 2: Separating", unit="iter"):
            # Store current state for animation
            if i % 5 == 0:  # Capture every 5th frame
                self.animation_data.append(X.copy())
            
            # Apply jitter periodically
            if i % jitter_interval == 0 and i > 0:
                jitter = np.random.normal(0, jitter_amount, X.shape)
                X += jitter
            
            # Calculate forces
            forces = np.zeros_like(X)
            for j in range(len(X)):
                for k in range(j + 1, len(X)):
                    if j >= len(self.labels) or k >= len(self.labels):
                        continue
                    
                    variety_j = self.varieties[self.labels[j]]
                    variety_k = self.varieties[self.labels[k]]
                    
                    # Distance and minimum separation
                    dist = np.linalg.norm(X[j] - X[k])
                    min_sep = max(variety_j.radius, variety_k.radius)
                    
                    if dist < min_sep and dist > 0:
                        # Repulsive force
                        direction = (X[j] - X[k]) / dist
                        force_magnitude = (min_sep - dist) / min_sep
                        forces[j] += direction * force_magnitude
                        forces[k] -= direction * force_magnitude
            
            # Update positions
            X += forces * step_size
            
            # Keep within garden bounds
            X[:, 0] = np.clip(X[:, 0], 0, self.garden_width)
            X[:, 1] = np.clip(X[:, 1], 0, self.garden_height)
        
        return X
    
    def animate_create_beneficial_interactions(self):
        """Animate the create beneficial interactions algorithm."""
        X = self.X.copy()
        step_size = 0.05
        band_delta = 0.25
        degree_cap = 4
        
        print("Creating beneficial interactions...")
        for i in tqdm(range(self.max_animation_steps), desc="Step 3: Optimizing", unit="iter"):
            # Store current state for animation
            if i % 5 == 0:  # Capture every 5th frame
                self.animation_data.append(X.copy())
            
            # Calculate forces
            forces = np.zeros_like(X)
            degrees = np.zeros(len(X))
            
            # Count degrees for each plant
            for j in range(len(X)):
                for k in range(j + 1, len(X)):
                    if j >= len(self.labels) or k >= len(self.labels):
                        continue
                    
                    variety_j = self.varieties[self.labels[j]]
                    variety_k = self.varieties[self.labels[k]]
                    
                    # Only cross-species interactions
                    if variety_j.species == variety_k.species:
                        continue
                    
                    dist = np.linalg.norm(X[j] - X[k])
                    interaction_dist = variety_j.radius + variety_k.radius - band_delta
                    
                    if dist < interaction_dist + band_delta:
                        degrees[j] += 1
                        degrees[k] += 1
            
            # Apply attractive forces
            for j in range(len(X)):
                for k in range(j + 1, len(X)):
                    if j >= len(self.labels) or k >= len(self.labels):
                        continue
                    
                    variety_j = self.varieties[self.labels[j]]
                    variety_k = self.varieties[self.labels[k]]
                    
                    # Only cross-species interactions
                    if variety_j.species == variety_k.species:
                        continue
                    
                    dist = np.linalg.norm(X[j] - X[k])
                    interaction_dist = variety_j.radius + variety_k.radius - band_delta
                    
                    if dist > interaction_dist:
                        # Attractive force
                        direction = (X[k] - X[j]) / dist if dist > 0 else np.random.normal(0, 0.01, 2)
                        force_magnitude = (dist - interaction_dist) / interaction_dist
                        
                        # Dampen force for high-degree plants
                        dampen_j = 1.0 if degrees[j] < degree_cap else 0.5
                        dampen_k = 1.0 if degrees[k] < degree_cap else 0.5
                        
                        forces[j] += direction * force_magnitude * dampen_j
                        forces[k] -= direction * force_magnitude * dampen_k
            
            # Update positions
            X += forces * step_size
            
            # Keep within garden bounds
            X[:, 0] = np.clip(X[:, 0], 0, self.garden_width)
            X[:, 1] = np.clip(X[:, 1], 0, self.garden_height)
        
        return X
    
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
    
    def reset_algorithm(self):
        """Reset to the beginning."""
        self.current_step = -1
        self.X = None
        self.labels = None
        self.inv = None
        self.score = 0.0
        self.interactions = []
        print("Algorithm reset to beginning")
    
    def run(self):
        """Main visualization loop (same as existing visualizer)."""
        while self.running:
            self.handle_events()
            
            # Same rendering as existing visualizer
            self.screen.fill(self.bg_color)
            self.draw_grid()
            self.draw_plants()
            self.draw_interactions()
            self.draw_info_panel()
            self.draw_debug_info()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def load_varieties_from_config(config_file: str, max_varieties: int = 20):
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


def main():
    """Run the algorithm visualizer with fruits and veggies."""
    print("Loading varieties...")
    varieties = load_varieties_from_config('fruits_and_veggies.json', max_varieties=20)
    print(f"Loaded {len(varieties)} varieties")
    
    try:
        visualizer = AlgorithmVisualizer(varieties)
        visualizer.run()
    except Exception as e:
        print(f"Error in visualizer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
