import pygame

from core.engine import Engine
from core.garden import Garden
from core.plants.species import Species


class GardenVisualizer:
    def __init__(
        self, garden: Garden, engine: Engine, turns: int, width=1280, height=800
    ):
        pygame.init()

        self.garden = garden
        self.engine = engine
        self.width = width
        self.height = height
        self.simulation_turns = turns

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Flower Garden Simulation")

        self.bg_color = (240, 240, 240)
        self.grid_color = (200, 200, 200)
        self.interaction_line_color = (100, 100, 100)

        self.species_colors = {
            Species.RHODODENDRON: (220, 20, 60),  # Crimson Red
            Species.GERANIUM: (46, 139, 87),  # Sea Green
            Species.BEGONIA: (65, 105, 225),  # Royal Blue
        }

        self.padding = 80
        info_pane_width = 220
        self.scale_x = (width - self.padding * 2 - info_pane_width) / garden.width
        self.scale_y = (height - self.padding * 2) / garden.height
        self.offset_x = self.padding
        self.offset_y = self.padding

        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)

        self.running = True
        self.paused = True
        self.turn = 0
        self.clock = pygame.time.Clock()

    def garden_to_screen(self, x, y):
        """Convert garden coordinates to screen coordinates."""
        return int(x * self.scale_x + self.offset_x), int(
            y * self.scale_y + self.offset_y
        )

    def draw_grid(self):
        """Draw garden boundaries and grid."""
        garden_width_px = self.garden.width * self.scale_x
        garden_height_px = self.garden.height * self.scale_y
        border_rect = pygame.Rect(
            self.offset_x, self.offset_y, garden_width_px, garden_height_px
        )
        pygame.draw.rect(self.screen, (0, 0, 0), border_rect, 2)

        for i in range(1, int(self.garden.width)):
            x = self.offset_x + i * self.scale_x
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (x, self.offset_y),
                (x, self.offset_y + garden_height_px),
            )

        for i in range(1, int(self.garden.height)):
            y = self.offset_y + i * self.scale_y
            pygame.draw.line(
                self.screen,
                self.grid_color,
                (self.offset_x, y),
                (self.offset_x + garden_width_px, y),
            )

    def draw_interactions(self):
        """Draw lines between interacting plants."""
        for plant1, plant2 in self.garden.get_all_interactions():
            pos1 = self.garden_to_screen(plant1.position.x, plant1.position.y)
            pos2 = self.garden_to_screen(plant2.position.x, plant2.position.y)
            pygame.draw.line(self.screen, self.interaction_line_color, pos1, pos2, 2)

    def draw_plants(self):
        """Draw all plants in the garden."""
        for plant in self.garden.plants:
            pos = self.garden_to_screen(plant.position.x, plant.position.y)
            color = self.species_colors[plant.variety.species]
            root_radius = int(plant.variety.radius * min(self.scale_x, self.scale_y))
            pygame.draw.circle(self.screen, color, pos, root_radius, 2)

            growth_ratio = plant.size / plant.max_size if plant.max_size > 0 else 0
            min_radius, max_radius = 5, root_radius * 0.9
            plant_radius = int(min_radius + growth_ratio * (max_radius - min_radius))

            pygame.draw.circle(self.screen, color, pos, plant_radius)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, plant_radius, 1)

    def draw_info_panel(self):
        """
        MODIFICATION: This method now draws all UI text, including the
        simulation info, controls, and the species legend, into a single
        panel on the right side of the screen.
        """
        info_pane_x = self.width - self.padding - 170  # Adjusted for better fit
        y_offset = self.offset_y

        # --- Draw simulation stats ---
        info_lines = [
            f"Turn: {self.turn}",
            f"Total Growth: {self.garden.total_growth():.2f}",
            f"Plants: {len(self.garden.plants)}",
            "",
            f"{'PAUSED' if self.paused else 'RUNNING'}",
        ]
        for line in info_lines:
            text = self.small_font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (info_pane_x, y_offset))
            y_offset += 30

        y_offset += 20  # Add extra space

        # --- Draw controls ---
        control_lines = [
            "Controls:",
            "SPACE: Play/Pause",
            "RIGHT: Step forward",
            "Q: Quit",
        ]
        for line in control_lines:
            text = self.small_font.render(line, True, (0, 0, 0))
            self.screen.blit(text, (info_pane_x, y_offset))
            y_offset += 30

        y_offset += 20  # Add extra space

        # --- Draw species legend ---
        title = self.font.render("Species:", True, (0, 0, 0))
        self.screen.blit(title, (info_pane_x, y_offset))
        y_offset += 40

        for species, color in self.species_colors.items():
            name = species.name.replace("_", " ").title()
            text = self.small_font.render(name, True, (0, 0, 0))

            # Vertically center the circle next to the text
            circle_y = y_offset + text.get_height() // 2
            pygame.draw.circle(self.screen, color, (info_pane_x + 15, circle_y), 10)
            pygame.draw.circle(
                self.screen, (0, 0, 0), (info_pane_x + 15, circle_y), 10, 1
            )

            self.screen.blit(text, (info_pane_x + 35, y_offset))
            y_offset += 35

    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_q
            ):
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_RIGHT and self.paused:
                    self.step_simulation()

    def step_simulation(self):
        """Run one turn of simulation."""
        if self.turn < self.simulation_turns:
            self.engine.run_turn()
            self.turn += 1
        else:
            self.paused = True

    def run(self):
        """Main visualization loop."""
        while self.running:
            self.handle_events()

            if not self.paused:
                self.step_simulation()
                self.clock.tick(10)

            self.screen.fill(self.bg_color)
            self.draw_grid()
            self.draw_plants()
            self.draw_interactions()

            # MODIFICATION: Replaced draw_info() and draw_legend() with a single call
            self.draw_info_panel()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


def visualize_simulation(garden: Garden, turns: int = 1000):
    """Initializes and runs the garden visualization."""
    engine = Engine(garden)
    visualizer = GardenVisualizer(garden, engine, turns)
    visualizer.run()
