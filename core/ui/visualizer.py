import pygame

from core.engine import Engine
from core.garden import Garden
from core.plants.species import Species


class GardenVisualizer:
    def __init__(
        self, garden: Garden, engine: Engine, turns: int, width=800, height=600
    ):
        pygame.init()

        self.garden = garden
        self.engine = engine
        self.width = width
        self.height = height
        self.simulation_turns = turns

        # Create window
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Flower Garden Simulation")

        # Colors
        self.bg_color = (240, 240, 240)
        self.grid_color = (200, 200, 200)

        # Species colors
        self.species_colors = {
            Species.RHODODENDRON: (255, 100, 100),  # Red
            Species.GERANIUM: (100, 255, 100),  # Green
            Species.BEGONIA: (100, 100, 255),  # Blue
        }

        # Calculate scale (pixels per meter)
        self.scale_x = (width - 100) / garden.width
        self.scale_y = (height - 100) / garden.height
        self.offset_x = 50
        self.offset_y = 50

        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        self.running = True
        self.paused = True
        self.turn = 0
        self.clock = pygame.time.Clock()

    def garden_to_screen(self, x, y):
        """Convert garden coordinates to screen coordinates."""
        screen_x = int(x * self.scale_x + self.offset_x)
        screen_y = int(y * self.scale_y + self.offset_y)
        return screen_x, screen_y

    def draw_grid(self):
        """Draw garden boundaries and grid."""
        # Draw border
        border_rect = pygame.Rect(
            self.offset_x,
            self.offset_y,
            self.garden.width * self.scale_x,
            self.garden.height * self.scale_y,
        )
        pygame.draw.rect(self.screen, (0, 0, 0), border_rect, 2)

        # Draw grid lines
        for i in range(int(self.garden.width) + 1):
            x = self.offset_x + i * self.scale_x
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (x, self.offset_y),
                (x, self.offset_y + self.garden.height * self.scale_y),
            )

        for i in range(int(self.garden.height) + 1):
            y = self.offset_y + i * self.scale_y
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (self.offset_x, y),
                (self.offset_x + self.garden.width * self.scale_x, y),
            )

    def draw_interactions(self):
        """Draw lines between interacting plants."""
        interactions = self.garden.get_all_interactions()
        for plant1, plant2 in interactions:
            pos1 = self.garden_to_screen(plant1.position.x, plant1.position.y)
            pos2 = self.garden_to_screen(plant2.position.x, plant2.position.y)
            pygame.draw.line(self.screen, (200, 200, 200), pos1, pos2, 1)

    def draw_plants(self):
        """Draw all plants in the garden."""
        for plant in self.garden.plants:
            pos = self.garden_to_screen(plant.position.x, plant.position.y)
            color = self.species_colors[plant.variety.species]

            # Draw root radius (faint circle)
            root_radius = int(plant.variety.radius * min(self.scale_x, self.scale_y))
            pygame.draw.circle(self.screen, (*color, 50), pos, root_radius, 1)

            # Draw plant size (based on growth)
            # Scale size from 0 to max_size -> 5 to root_radius pixels
            if plant.max_size > 0:
                growth_ratio = plant.size / plant.max_size
            else:
                growth_ratio = 0

            plant_radius = int(5 + growth_ratio * (root_radius - 5))
            pygame.draw.circle(self.screen, color, pos, plant_radius)

            # Draw border
            pygame.draw.circle(self.screen, (0, 0, 0), pos, plant_radius, 1)

    def draw_info(self):
        """Draw simulation information."""
        info_lines = [
            f"Turn: {self.turn}",
            f"Total Growth: {self.garden.total_growth():.2f}",
            f"Plants: {len(self.garden.plants)}",
            f"{'PAUSED' if self.paused else 'RUNNING'}",
            "",
            "Controls:",
            "SPACE: Play/Pause",
            "RIGHT: Step forward",
            "Q: Quit",
        ]

        y_offset = 10
        for line in info_lines:
            text = self.small_font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (self.width - 180, y_offset))
            y_offset += 20

    def draw_legend(self):
        """Draw species legend."""
        legend_y = self.height - 100
        legend_x = 10

        title = self.small_font.render("Species:", True, (0, 0, 0))
        self.screen.blit(title, (legend_x, legend_y))
        legend_y += 25

        for species, color in self.species_colors.items():
            # Draw colored circle
            pygame.draw.circle(self.screen, color, (legend_x + 10, legend_y + 10), 8)
            pygame.draw.circle(
                self.screen, (0, 0, 0), (legend_x + 10, legend_y + 10), 8, 1
            )

            # Draw species name
            text = self.small_font.render(species.name, True, (0, 0, 0))
            self.screen.blit(text, (legend_x + 30, legend_y + 2))
            legend_y += 25

    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_RIGHT:
                    self.step_simulation()
                elif event.key == pygame.K_q:
                    self.running = False

    def step_simulation(self):
        """Run one turn of simulation."""
        if self.turn < self.simulation_turns:
            self.engine.run_turn()
            self.turn += 1

    def run(self):
        """Main visualization loop."""
        while self.running:
            self.handle_events()

            # Step simulation if not paused
            if not self.paused:
                self.step_simulation()
                self.clock.tick(10)  # 10 turns per second

            # Draw everything
            self.screen.fill(self.bg_color)
            self.draw_grid()
            self.draw_interactions()
            self.draw_plants()
            self.draw_info()
            self.draw_legend()

            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS

        pygame.quit()


# Usage function
def visualize_simulation(garden: Garden, turns: int = 1000):
    """Helper function to visualize a garden simulation."""
    engine = Engine(garden)
    engine.simulation_turns = turns

    visualizer = GardenVisualizer(garden, engine)
    visualizer.run()
