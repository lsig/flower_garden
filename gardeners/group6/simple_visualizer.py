#!/usr/bin/env python3
"""
Simple test visualizer to debug the issue.
"""

import pygame
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plants.plant_variety import PlantVariety
from core.plants.species import Species
from gardeners.group6.force_layout import scatter_seeds


def main():
    """Simple test with just a few varieties."""
    print("Creating simple test varieties...")
    
    # Create just 3 test varieties
    varieties = [
        PlantVariety('Radish', 1, Species.RHODODENDRON, {'R': 1.0, 'G': -0.4, 'B': -0.2}),
        PlantVariety('Green Bean', 2, Species.GERANIUM, {'G': 1.0, 'R': -0.5, 'B': -0.3}),
        PlantVariety('Blueberry', 1, Species.BEGONIA, {'B': 1.0, 'R': -0.3, 'G': -0.2})
    ]
    
    print(f"Created {len(varieties)} test varieties")
    
    # Test scatter_seeds
    print("Testing scatter_seeds...")
    X, labels, inv = scatter_seeds(varieties, W=16.0, H=10.0)
    print(f"Scatter result: X={X.shape}, labels={len(labels)}, inv={inv.shape}")
    
    # Initialize pygame
    print("Initializing pygame...")
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Simple Test")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    
    # Colors
    colors = {
        Species.RHODODENDRON: (255, 100, 100),
        Species.GERANIUM: (100, 255, 100),
        Species.BEGONIA: (100, 100, 255)
    }
    
    # Scale
    scale = 30
    offset_x, offset_y = 100, 100
    
    print("Starting visualization loop...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Clear screen
        screen.fill((255, 255, 255))
        
        # Draw plants
        for i, (x, y) in enumerate(X):
            variety = varieties[labels[i]]
            color = colors[variety.species]
            
            screen_x = int(offset_x + x * scale)
            screen_y = int(offset_y + y * scale)
            radius = int(variety.radius * scale)
            
            pygame.draw.circle(screen, color, (screen_x, screen_y), radius)
            pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), radius, 2)
        
        # Draw info
        text = font.render(f"Plants: {len(X)}", True, (0, 0, 0))
        screen.blit(text, (10, 10))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    print("Done!")


if __name__ == '__main__':
    main()
