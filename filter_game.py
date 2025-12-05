import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 40
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 100, 100)
BLUE = (100, 100, 255)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 100)
PURPLE = (200, 100, 255)

# Maze layouts - 1 = wall, 0 = path, S = start, E = exit, A/B = source locations
# CRITICAL: Sources A and B must be at positions that are ALWAYS open paths
MAZE_LAYOUTS = {
    "neutral": [
        "11111111111111111111",
        "1S000001111A11111111",  # A at (3,1) - requires navigation
        "11111101111011111111",
        "11000101111011111111",
        "11010101111011111111",
        "11010100000000000111",
        "11010111111111110111",
        "11010111111111110111",
        "11010000000000000111",
        "110B1111111111111111",  # B at (3,9) - behind walls
        "11011111111111111111",
        "11000000000000000E01",  # Long path to exit
        "11111111111111111111"
    ],
    "source_A": [  # Red source - opens left-biased paths
        "11111111111111111111",
        "1S000001111A11111111",  # Keep A position clear
        "10000001111011111111",  # Left wall opens!
        "10010101111011111111",
        "10010101111111111111",
        "10010100000000000111",
        "10010000000011110111",  # New left passages
        "10011111111011110111",
        "10000000000011110111",  # But some right paths close
        "100B1111111111111111",  # B still hard to reach
        "10011111111111111111",
        "10000000001111100E01",  # Different route to exit
        "11111111111111111111"
    ],
    "source_B": [  # Blue source - opens right-biased paths
        "11111111111111111111",
        "1S000001111A11000001",  # Keep A position clear  
        "11111101111011010001",
        "11000101111011010001",
        "11010101111011010001",
        "11010100000000000001",  # Right side opens
        "11010111111111110001",
        "11010111111111110001",
        "11010000000000000001",  # Major right shortcut
        "110B0000000000000001",  # B area fully accessible
        "11011111111100000001",
        "11011111111100000E01",  # Right-side exit route
        "11111111111111111111"
    ],
    "both_sources": [  # Both collected - balanced view reveals best path
        "11111111111111111111",
        "1S000001111A11000001",  # Both perspectives
        "10000001111011010001",
        "10010100000000010001",  # LEFT + RIGHT = CENTER
        "10010100111111010001",
        "10010100000000000001",
        "10010000000011110001",  # All options available
        "10011111111011110001",
        "10000000000000000001",  # Central corridor emerges
        "100B0000000000000001",  # Everything accessible
        "10011111111100000001",
        "10000000000000000E01",  # Most direct path revealed
        "11111111111111111111"
    ]
}

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x * TILE_SIZE + 5, y * TILE_SIZE + 5, 
                               TILE_SIZE - 10, TILE_SIZE - 10)
        self.speed = 4
        
    def move(self, dx, dy, walls):
        # Move horizontally first
        self.rect.x += dx * self.speed
        if self.check_collision(walls):
            self.rect.x -= dx * self.speed
            
        # Then move vertically
        self.rect.y += dy * self.speed
        if self.check_collision(walls):
            self.rect.y -= dy * self.speed
    
    def check_collision(self, walls):
        for wall in walls:
            if self.rect.colliderect(wall):
                return True
        return False
    
    def draw(self, screen):
        pygame.draw.rect(screen, GREEN, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)

class NewsSource:
    def __init__(self, x, y, source_type, color):
        self.rect = pygame.Rect(x * TILE_SIZE + 10, y * TILE_SIZE + 10,
                               TILE_SIZE - 20, TILE_SIZE - 20)
        self.source_type = source_type
        self.color = color
        self.collected = False
        
    def draw(self, screen):
        if not self.collected:
            pygame.draw.circle(screen, self.color, self.rect.center, 15)
            pygame.draw.circle(screen, BLACK, self.rect.center, 15, 2)
            
    def collect(self):
        self.collected = True

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Filter Bubble - Media Maze")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 48)
        
        # Game state
        self.collected_sources = {"A": False, "B": False}
        self.current_worldview = "neutral"
        self.game_complete = False
        self.completion_message = ""
        self.flash_timer = 0  # For visual feedback
        
        # Initialize level
        self.init_level()
        
    def init_level(self):
        # Find start position and create entities
        start_x, start_y = 1, 1  # Default
        self.exit_pos = None
        source_positions = {'A': None, 'B': None}
        
        # Parse the neutral maze to find special positions
        for y, row in enumerate(MAZE_LAYOUTS["neutral"]):
            for x, cell in enumerate(row):
                if cell == 'S':
                    start_x, start_y = x, y
                elif cell == 'E':
                    self.exit_pos = (x, y)
                elif cell == 'A':
                    source_positions['A'] = (x, y)
                elif cell == 'B':
                    source_positions['B'] = (x, y)
        
        self.player = Player(start_x, start_y)
        
        # Place news sources at their designated safe positions
        self.news_sources = []
        if source_positions['A']:
            self.news_sources.append(NewsSource(source_positions['A'][0], 
                                              source_positions['A'][1], "A", RED))
        if source_positions['B']:
            self.news_sources.append(NewsSource(source_positions['B'][0], 
                                              source_positions['B'][1], "B", BLUE))
        
        # Build initial walls
        self.update_maze()
        
    def update_maze(self):
        """Rebuild maze based on collected sources"""
        if self.collected_sources["A"] and self.collected_sources["B"]:
            self.current_worldview = "both_sources"
            maze = MAZE_LAYOUTS["both_sources"]
        elif self.collected_sources["A"]:
            self.current_worldview = "source_A"
            maze = MAZE_LAYOUTS["source_A"]
        elif self.collected_sources["B"]:
            self.current_worldview = "source_B"
            maze = MAZE_LAYOUTS["source_B"]
        else:
            self.current_worldview = "neutral"
            maze = MAZE_LAYOUTS["neutral"]
        
        # Create wall rectangles
        self.walls = []
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                # Only create walls for '1' cells, ignore special markers
                if cell == '1':
                    wall_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, 
                                          TILE_SIZE, TILE_SIZE)
                    self.walls.append(wall_rect)
        
        # FIXED: Better collision detection and safe spot finding
        stuck = False
        for wall in self.walls:
            if self.player.rect.colliderect(wall):
                stuck = True
                break
        
        if stuck:
            # Find nearest safe spot using grid positions
            player_grid_x = self.player.rect.centerx // TILE_SIZE
            player_grid_y = self.player.rect.centery // TILE_SIZE
            
            found_safe_spot = False
            
            # Search in expanding circles
            for radius in range(1, 10):
                positions_to_check = []
                
                # Generate positions in a circle around player
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if abs(dx) == radius or abs(dy) == radius:  # Only check border
                            grid_x = player_grid_x + dx
                            grid_y = player_grid_y + dy
                            
                            # Check bounds
                            if 0 <= grid_y < len(maze) and 0 <= grid_x < len(maze[0]):
                                if maze[grid_y][grid_x] != '1':  # Not a wall (could be 0, A, B, S, E)
                                    positions_to_check.append((grid_x, grid_y))
                
                # Check each position
                for grid_x, grid_y in positions_to_check:
                    new_x = grid_x * TILE_SIZE + 5
                    new_y = grid_y * TILE_SIZE + 5
                    test_rect = pygame.Rect(new_x, new_y, TILE_SIZE - 10, TILE_SIZE - 10)
                    
                    # Verify no collision
                    collision = False
                    for wall in self.walls:
                        if test_rect.colliderect(wall):
                            collision = True
                            break
                    
                    if not collision:
                        self.player.rect.x = new_x
                        self.player.rect.y = new_y
                        found_safe_spot = True
                        break
                
                if found_safe_spot:
                    break
            
            if not found_safe_spot:
                # Emergency respawn at start
                self.player.rect.x = 1 * TILE_SIZE + 5
                self.player.rect.y = 1 * TILE_SIZE + 5
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
            
        if dx != 0 or dy != 0:
            self.player.move(dx, dy, self.walls)
    
    def update(self):
        if self.game_complete:
            return
        
        # Update flash timer
        if self.flash_timer > 0:
            self.flash_timer -= 1
            
        # Check news source collection
        for source in self.news_sources:
            if not source.collected and self.player.rect.colliderect(source.rect):
                source.collect()
                self.collected_sources[source.source_type] = True
                self.flash_timer = 30  # Flash for 0.5 seconds at 60 FPS
                
                # Before updating maze, slightly nudge player away from walls
                # This prevents being right on the edge when walls change
                self.player.rect.x = (self.player.rect.x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 4
                self.player.rect.y = (self.player.rect.y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 4
                
                self.update_maze()  # Rebuild maze with new perspective
        
        # Check if player reached exit
        if self.exit_pos:
            exit_rect = pygame.Rect(self.exit_pos[0] * TILE_SIZE, 
                                   self.exit_pos[1] * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)
            if self.player.rect.colliderect(exit_rect):
                self.game_complete = True
                if self.current_worldview == "both_sources":
                    self.completion_message = "Balanced View Achievement!"
                elif self.current_worldview != "neutral":
                    self.completion_message = "Limited Perspective - Try collecting all sources!"
                else:
                    self.completion_message = "Completed with no sources - Missed opportunities!"
    
    def draw(self):
        self.screen.fill(WHITE)
        
        # Flash effect when collecting sources
        if self.flash_timer > 0:
            flash_alpha = int(255 * (self.flash_timer / 30))
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surface.set_alpha(flash_alpha)
            flash_surface.fill(YELLOW)
            self.screen.blit(flash_surface, (0, 0))
        
        # Draw maze with color coding based on worldview
        base_color = GRAY
        if self.current_worldview == "source_A":
            base_color = (200, 150, 150)  # Reddish
        elif self.current_worldview == "source_B":
            base_color = (150, 150, 200)  # Bluish
        elif self.current_worldview == "both_sources":
            base_color = (180, 150, 200)  # Purple
            
        for wall in self.walls:
            pygame.draw.rect(self.screen, base_color, wall)
            pygame.draw.rect(self.screen, BLACK, wall, 1)
        
        # Draw exit
        if self.exit_pos:
            exit_rect = pygame.Rect(self.exit_pos[0] * TILE_SIZE + 5, 
                                   self.exit_pos[1] * TILE_SIZE + 5,
                                   TILE_SIZE - 10, TILE_SIZE - 10)
            pygame.draw.rect(self.screen, YELLOW, exit_rect)
            pygame.draw.rect(self.screen, BLACK, exit_rect, 2)
        
        # Draw news sources
        for source in self.news_sources:
            source.draw(self.screen)
        
        # Draw player
        self.player.draw(self.screen)
        
        # Draw UI
        self.draw_ui()
        
        # Draw completion message if game is done
        if self.game_complete:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            
            text = self.big_font.render(self.completion_message, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
            
            subtext = self.font.render("Press ESC to quit or R to restart", True, WHITE)
            subtext_rect = subtext.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
            self.screen.blit(subtext, subtext_rect)
        
        pygame.display.flip()
    
    def draw_ui(self):
        # Draw current worldview indicator
        worldview_text = f"Current Perspective: {self.current_worldview.replace('_', ' ').title()}"
        text_surface = self.font.render(worldview_text, True, BLACK)
        self.screen.blit(text_surface, (10, 10))
        
        # Draw collected sources
        y_offset = 40
        for source_type, collected in self.collected_sources.items():
            color = RED if source_type == "A" else BLUE
            status = "Collected" if collected else "Not Found"
            text = f"News Source {source_type}: {status}"
            text_surface = self.font.render(text, True, color if collected else GRAY)
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += 25
        
        # Instructions
        instructions = [
            "Use ARROW KEYS or WASD to move",
            "Collect news sources to reveal new paths",
            "Different sources show different realities",
            "Press TAB to see source locations (debug)",
            "Press SPACE if stuck (emergency respawn)"
        ]
        y_offset = SCREEN_HEIGHT - 120
        for instruction in instructions:
            text_surface = self.font.render(instruction, True, BLACK)
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += 25
            
        # Debug: Show source locations when TAB is pressed
        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            for source in self.news_sources:
                if not source.collected:
                    # Draw a line from player to source
                    pygame.draw.line(self.screen, source.color, 
                                   self.player.rect.center, 
                                   source.rect.center, 2)
                    # Draw circle around source
                    pygame.draw.circle(self.screen, source.color, 
                                     source.rect.center, 25, 2)
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r and self.game_complete:
                        # Reset game
                        self.collected_sources = {"A": False, "B": False}
                        self.current_worldview = "neutral"
                        self.game_complete = False
                        self.completion_message = ""
                        self.init_level()
                    elif event.key == pygame.K_SPACE:
                        # Emergency unstuck - respawn at start
                        self.player.rect.x = 1 * TILE_SIZE + 5
                        self.player.rect.y = 1 * TILE_SIZE + 5
            
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()