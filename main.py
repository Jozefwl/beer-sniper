import pygame
import pygame.freetype
import random
from enum import Enum
from pygame.sprite import Sprite
from pygame.sprite import RenderUpdates

BLUE = (106, 159, 181)
WHITE = (255, 255, 255)
GOLD = (180, 150, 20)
GREEN = (0, 200, 0)
BLACK = (0, 0, 0)

WIDTH = 800
HEIGHT = 600

GAME_TITLE = "Beer Sniper"
TITLE_BG_COLOR = BLACK
TITLE_FONT_NAME = "Impact"

# Difficulty setting
TARGET_SIZE = 100
TARGET_SPEED = 4
MAX_TARGETS = 5
SPAWN_INTERVAL = 300 # in ms

# Spritesheet vybuchu: 4 stlpce x 4 riadky po 64x64 pixelov (16 snimkov celkovo).
# https://opengameart.org/content/explosion
# Snimky sa citaju zlava doprava, zhora nadol:
#   0  1  2  3
#   4  5  6  7
#   8  9 10 11
#  12 13 14 15
CROSSHAIR_WIDTH = 150
CROSSHAIR_HEIGHT = 150

# Velkost naboja ktory odpadne
CARTRIDGE_WIDTH = 40
CARTRIDGE_HEIGHT = 15
CARTRIDGE_PATH = "cartridge.png"

CARTRIDGE_OFFSET_X = 0
CARTRIDGE_OFFSET_Y = 0

# Pridaj dalsie cesty ak chces viac typov terca.
TARGET_PATHS = ["target1.png", "target2.png", "target3.png"]

EXPLOSION_SHEET_PATH = "explosion.png"
EXPLOSION_FRAME_SIZE = 64
EXPLOSION_COLS = 4
EXPLOSION_ROWS = 4
EXPLOSION_FRAME_COUNT = EXPLOSION_COLS * EXPLOSION_ROWS
EXPLOSION_FRAME_MS = 40

# https://programmingpixels.com/handling-a-title-screen-game-flow-and-buttons-in-pygame.html

def create_surface_with_text(text, font_size, text_rgb, bg_rgb, font_name="Impact"):
    """ Vrati surface s nakreslenim textom """
    font = pygame.freetype.SysFont(font_name, font_size, bold=True)
    surface, _ = font.render(text=text, fgcolor=text_rgb, bgcolor=bg_rgb)
    return surface.convert_alpha()

def load_cartridge_image(path):
    """ Nacita obrazok naboja raz a zmensi ho. Vrati None ak chyba. """
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (CARTRIDGE_WIDTH, CARTRIDGE_HEIGHT))
    except (FileNotFoundError, pygame.error):
        print(path + " chyba / nespravna cesta k suboru")
        return None


class Cartridge:
    """ Vystrelena nabojnica: leti do strany krivkou a zrychluje smerom dolu. """

    def __init__(self, image, x, y):
        self.image = image
        self.x = x - CARTRIDGE_OFFSET_X
        self.y = y - CARTRIDGE_OFFSET_Y
        # vx do strany (vystrel vlavo), vy mala nadol -> kazdy frame zrychli
        self.vx = random.uniform(random.randint(-6, 6), -2)
        self.vy = random.uniform(1, 3)
        self.finished = False

    def update(self):
        self.vy += self.vy * 0.2   # zrychli padanie o 20% kazdy frame -> krivka
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT:
            self.finished = True

    def draw(self, surface):
        if self.image is not None:
            surface.blit(self.image, (self.x, self.y))



def load_explosion_frames(path):
    """ Nacita spritesheet zo zadanej cesty a rozreze ho na 16 snimkov v poradi.
        https://www.pygame.org/docs/ref/surface.html#pygame.Surface.subsurface
        https://www.101computing.net/pygame-animations-using-a-spritesheet/
        https://stackoverflow.com/questions/10560446/how-do-you-select-a-sprite-image-from-a-sprite-sheet-in-python
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
        print(sheet)
    except (FileNotFoundError, pygame.error):
        print("explosion.png chyba / nespravna cesta k suboru")
        return

    sheet = pygame.image.load(path).convert_alpha()
    frames = []
    for row in range(EXPLOSION_ROWS):
        for col in range(EXPLOSION_COLS):
            rect = pygame.Rect(
                col * EXPLOSION_FRAME_SIZE,
                row * EXPLOSION_FRAME_SIZE,
                EXPLOSION_FRAME_SIZE,
                EXPLOSION_FRAME_SIZE,
            )
            frames.append(sheet.subsurface(rect).copy())
    return frames


class Explosion:
    """ Prehrava jednorazovu animaciu vybuchu centered na pozicii. """

    def __init__(self, frames, center):
        self.frames = frames
        self.center = center
        self.start_time = pygame.time.get_ticks()
        self.finished = False

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed >= EXPLOSION_FRAME_COUNT * EXPLOSION_FRAME_MS:
            self.finished = True

    def draw(self, surface):
        if self.finished:
            return
        index = (pygame.time.get_ticks() - self.start_time) // EXPLOSION_FRAME_MS
        index = min(index, EXPLOSION_FRAME_COUNT - 1)
        frame = self.frames[index]
        rect = frame.get_rect(center=self.center)
        surface.blit(frame, rect)


class UIElement(Sprite):
    """ Prvok user interface, ktory mozno pridat na porvch """

    def __init__(self, center_position, text, font_size, bg_rgb, text_rgb, action=None):
        self.mouse_over = False

        default_image = create_surface_with_text(
            text=text, font_size=font_size, text_rgb=text_rgb, bg_rgb=bg_rgb
        )
        highlighted_image = create_surface_with_text(
            text=text, font_size=font_size * 1.2, text_rgb=text_rgb, bg_rgb=bg_rgb
        )

        self.images = [default_image, highlighted_image]
        self.rects = [
            default_image.get_rect(center=center_position),
            highlighted_image.get_rect(center=center_position),
        ]

        self.action = action

        super().__init__()

    @property
    def image(self):
        return self.images[1] if self.mouse_over else self.images[0]

    @property
    def rect(self):
        return self.rects[1] if self.mouse_over else self.rects[0]

    def update(self, mouse_pos, mouse_up):
        """ Aktualizuje podla pozicie mysi; vrati akciu on press. """
        if self.rect.collidepoint(mouse_pos):
            self.mouse_over = True
            if mouse_up:
                return self.action
        else:
            self.mouse_over = False

    def draw(self, surface):
        """ Nakresli prvok na surface """
        surface.blit(self.image, self.rect)


class GameState(Enum):
    QUIT = -1
    TITLE = 0
    NEWGAME = 1


def main():
    pygame.init()
    pygame.mouse.set_visible(True)

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Najlepsia Hra")


    game_state = GameState.TITLE

    while True:
        if game_state == GameState.TITLE:
            game_state = title_screen(screen)

        if game_state == GameState.NEWGAME:
            game_state = play_level(screen)

        if game_state == GameState.QUIT:
            pygame.quit()
            return


def game_loop(screen, buttons, bg_color=BLUE, static_elements=None):
    pygame.mouse.set_visible(True)

    """ Spravuje menu loop, kym niektore tlacidlo nevrati akciu. """
    static_elements = static_elements or []
    while True:
        mouse_up = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return GameState.QUIT
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_up = True
        screen.fill(bg_color)

        for surface, rect in static_elements:
            screen.blit(surface, rect)

        for button in buttons:
            ui_action = button.update(pygame.mouse.get_pos(), mouse_up)
            if ui_action is not None:
                return ui_action

        buttons.draw(screen)
        pygame.display.flip()


def title_screen(screen):
    title_surface = create_surface_with_text(
        text=GAME_TITLE,
        font_size=72,
        text_rgb=WHITE,
        bg_rgb=TITLE_BG_COLOR,
        font_name=TITLE_FONT_NAME,
    )
    title_rect = title_surface.get_rect(center=(WIDTH / 2, HEIGHT * 1 / 4))

    instructions_font = pygame.font.SysFont("Arial", 20)
    instructions_text = instructions_font.render(
        "Spicka hlavne = cursor, R = nabit zasobnik, ESC = menu.", True, WHITE
    )
    instructions_rect = instructions_text.get_rect(center=(WIDTH / 2, HEIGHT * 1 / 4 + 60))

    start_btn = UIElement(
        center_position=(400, 400),
        font_size=30,
        bg_rgb=TITLE_BG_COLOR,
        text_rgb=WHITE,
        text="Start",
        action=GameState.NEWGAME,
    )
    quit_btn = UIElement(
        center_position=(400, 500),
        font_size=30,
        bg_rgb=TITLE_BG_COLOR,
        text_rgb=WHITE,
        text="Quit",
        action=GameState.QUIT,
    )

    buttons = RenderUpdates(start_btn, quit_btn)

    return game_loop(
        screen,
        buttons,
        bg_color=TITLE_BG_COLOR,
        static_elements=[
            (title_surface, title_rect),
            (instructions_text, instructions_rect),
        ],
    )


def win_screen(screen):
    pygame.mouse.set_visible(True)

    big_font = pygame.font.SysFont("Arial", 64, bold=True)
    win_text = big_font.render("Si alkoholik", True, WHITE)
    win_rect = win_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 40))

    info_font = pygame.font.SysFont("Arial", 24)
    info_text = info_font.render("Press ESC to return to menu", True, WHITE)
    info_rect = info_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 40))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return GameState.QUIT
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return GameState.TITLE

        screen.fill(BLACK)
        screen.blit(win_text, win_rect)
        screen.blit(info_text, info_rect)
        pygame.display.flip()


def play_level(screen):
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    score = 0

    font = pygame.font.SysFont("Arial", 32)
    text = font.render(f"Score: {score}", True, WHITE, BLACK)
    textRect = text.get_rect()
    textRect.center = (WIDTH * 1 / 10, HEIGHT * 1 / 10)

    hint_font = pygame.font.SysFont("Arial", 18)
    hint_text = hint_font.render("Press ESC to go to main menu...", True, BLACK)
    hint_rect = hint_text.get_rect()
    hint_rect.center = (WIDTH * 2 / 8, HEIGHT * 7 / 8)

    ammo_empty_font = pygame.font.SysFont("Arial", 20, bold=True)
    ammo_empty_text = ammo_empty_font.render("AMMO EMPTY", True, (255, 0, 0))

    ammo_count_font = pygame.font.SysFont("Arial", 18, bold=True)
    ammo_shot_cost = 10

    ammo_box_height = 20
    ammo_box_width = 120

    ammo_bar_height = 20
    ammo_bar_width = 120

    box_size = TARGET_SIZE
    boxes = []
    last_spawn = pygame.time.get_ticks()

    target_imgs = []
    for path in TARGET_PATHS:
        try:
            img = pygame.image.load(path).convert_alpha()
            target_imgs.append(pygame.transform.scale(img, (box_size, box_size)))
        except (FileNotFoundError, pygame.error):
            print(path + " chyba / nespravna cesta k suboru")

    # Smery: L->R, R->L, T->B, B->T a 4 uhlopriecky.
    directions = [
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
    ]

    def spawn_box():
        dir_x, dir_y = random.choice(directions)
        vx = dir_x * TARGET_SPEED
        vy = dir_y * TARGET_SPEED

        if dir_x > 0:
            x = -box_size
        elif dir_x < 0:
            x = WIDTH
        else:
            x = random.randint(0, WIDTH - box_size)

        if dir_y > 0:
            y = -box_size
        elif dir_y < 0:
            y = HEIGHT
        else:
            y = random.randint(0, HEIGHT - box_size)

        rect = pygame.Rect(x, y, box_size, box_size)
        img = random.choice(target_imgs) if target_imgs else None
        boxes.append((rect, img, vx, vy))

    spawn_box()

    try:
        crosshair_img = pygame.image.load("sniper.png").convert_alpha()
        crosshair_img = pygame.transform.scale(crosshair_img, (CROSSHAIR_WIDTH, CROSSHAIR_HEIGHT))
    except (FileNotFoundError, pygame.error):
        print("sniper.png chyba / nespravna cesta k suboru")
        crosshair_img = None

    try:
        firstperson_img = pygame.image.load("firstperson.png").convert_alpha()
    except (FileNotFoundError, pygame.error):
        print("firstperson.png chyba / nespravna cesta k suboru")
        firstperson_img = None

    explosion_frames = load_explosion_frames(EXPLOSION_SHEET_PATH)
    explosions = []

    cartridge_img = load_cartridge_image(CARTRIDGE_PATH)
    cartridges = []

    try:
        reward_img = pygame.image.load("reward.png").convert_alpha()
        reward_img = pygame.transform.scale(reward_img, (130, 90))
    except (FileNotFoundError, pygame.error):
        print("reward.png chyba / nespravna cesta k suboru")
        reward_img = None

    reward_font = pygame.font.SysFont("Arial", 32, bold=True)
    hit_streak = 0
    multiplier = 1

    debug = True

    while True:
        mouse_x, mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return GameState.QUIT
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_box_color = (0, 0, 0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_box_color = (255, 0, 0)
                if ammo_bar_width > 0:
                    ammo_bar_width = ammo_bar_width - 10

                    hit = False
                    for box in boxes[:]:
                        rect, img, vx, vy = box
                        if rect.collidepoint(mouse_x, mouse_y):
                            explosions.append(Explosion(explosion_frames, rect.center))
                            boxes.remove(box)
                            hit = True
                            break

                    if hit:
                        hit_streak = hit_streak + 1
                        score = score + multiplier
                        if hit_streak % 3 == 0:
                            multiplier = multiplier + 1
                        text = font.render(f"Score: {score}", True, WHITE, BLACK)
                        if score >= 100:
                            return win_screen(screen)
                    else:
                        hit_streak = 0
                        multiplier = 1

                    cartridges.append(Cartridge(cartridge_img, mouse_x, mouse_y))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    ammo_bar_width = 120
                if event.key == pygame.K_ESCAPE:
                    return GameState.TITLE

        now = pygame.time.get_ticks()
        if now - last_spawn >= SPAWN_INTERVAL and len(boxes) < MAX_TARGETS:
            spawn_box()
            last_spawn = now

        for box in boxes[:]:
            rect, img, vx, vy = box
            rect.x += vx
            rect.y += vy
            if rect.right < 0 or rect.left > WIDTH or rect.bottom < 0 or rect.top > HEIGHT:
                boxes.remove(box)

        for explosion in explosions[:]:
            explosion.update()
            if explosion.finished:
                explosions.remove(explosion)

        for cartridge in cartridges[:]:
            cartridge.update()
            if cartridge.finished:
                cartridges.remove(cartridge)

        screen.fill(WHITE)

        for rect, img, vx, vy in boxes:
            if img is not None:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, BLACK, rect)

        for explosion in explosions:
            explosion.draw(screen)

        for cartridge in cartridges:
            cartridge.draw(screen)

        if firstperson_img is not None:
            firstperson_rect = firstperson_img.get_rect()
            firstperson_rect.bottomright = (WIDTH, HEIGHT)
            screen.blit(firstperson_img, firstperson_rect)

        if crosshair_img is not None:
            crosshair_rect = crosshair_img.get_rect()
            crosshair_rect.center = (mouse_x, mouse_y)
            screen.blit(crosshair_img, crosshair_rect)

        box_ammo = pygame.Rect(
            WIDTH * 3/4,
            HEIGHT * 1/8,
            ammo_box_width,
            ammo_box_height,
        )
        pygame.draw.rect(screen, (0,0,0), box_ammo)

        ammo_rect = pygame.Rect(
            WIDTH * 3/4,
            HEIGHT * 1/8,
            ammo_bar_width,
            ammo_bar_height,
        )
        pygame.draw.rect(screen, GOLD, ammo_rect)

        ammo_current = max(0, ammo_bar_width) // ammo_shot_cost
        ammo_full = ammo_box_width // ammo_shot_cost
        ammo_count_text = ammo_count_font.render(
            f"Ammo: {ammo_current} / {ammo_full}", True, BLACK
        )
        ammo_count_rect = ammo_count_text.get_rect()
        ammo_count_rect.midtop = (box_ammo.centerx, box_ammo.bottom + 8)
        screen.blit(ammo_count_text, ammo_count_rect)

        if ammo_bar_width <= 0 and (pygame.time.get_ticks() // 400) % 2 == 0:
            ammo_empty_rect = ammo_empty_text.get_rect()
            ammo_empty_rect.midtop = (box_ammo.centerx, ammo_count_rect.bottom + 6)
            screen.blit(ammo_empty_text, ammo_empty_rect)

        screen.blit(text, textRect)
        screen.blit(hint_text, hint_rect)

        mult_text = reward_font.render(f"x{multiplier}", True, BLACK)
        if reward_img is not None:
            reward_rect = reward_img.get_rect()
            reward_rect.topleft = (20, 100)
            screen.blit(reward_img, reward_rect)
            screen.blit(mult_text, (reward_rect.right + 8, reward_rect.centery - mult_text.get_height() // 2))
        else:
            screen.blit(mult_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
