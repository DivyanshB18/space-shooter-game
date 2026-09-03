import pygame
import random
import sys
import math
import struct
import io

# ==============================
# INITIALIZE PYGAME & AUDIO
# ==============================
pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()
pygame.mixer.set_num_channels(16)

WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Space Shooter - Apex Edition")

clock = pygame.time.Clock()
font_hud = pygame.font.SysFont("consolas", 22, bold=True)
font_big = pygame.font.SysFont("consolas", 56, bold=True)
font_sub = pygame.font.SysFont("consolas", 20)

# ==============================
# BULLETPROOF WAV SYNTHESIZER
# ==============================
def generate_wav(wave_type="shoot"):
    sample_rate = 22050
    raw_samples = []

    if wave_type == "shoot":
        duration = 0.12
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            t = i / sample_rate
            freq = 900 - (i / total_samples) * 500
            val = math.sin(2 * math.pi * freq * t) * (1 - i / total_samples)
            sample = int(val * 24000)
            raw_samples.append(sample)

    elif wave_type == "explode":
        duration = 0.25
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            envelope = (1 - (i / total_samples)) ** 2
            val = (random.random() * 2 - 1) * envelope
            sample = int(val * 26000)
            raw_samples.append(sample)

    elif wave_type == "powerup":
        duration = 0.20
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            t = i / sample_rate
            freq = 420 + (i / total_samples) * 600
            val = math.sin(2 * math.pi * freq * t)
            sample = int(val * 22000)
            raw_samples.append(sample)

    elif wave_type == "hit":
        duration = 0.08
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            t = i / sample_rate
            freq = 160 - (i / total_samples) * 70
            val = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
            val *= (1 - i / total_samples)
            sample = int(val * 20000)
            raw_samples.append(sample)

    # Encode into standard Stereo WAV byte stream
    num_samples = len(raw_samples)
    byte_stream = io.BytesIO()

    # RIFF Header
    byte_stream.write(b'RIFF')
    byte_stream.write(struct.pack('<I', 36 + num_samples * 4))
    byte_stream.write(b'WAVE')

    # Sub-chunk 1 (fmt)
    byte_stream.write(b'fmt ')
    byte_stream.write(struct.pack('<I', 16))          # Subchunk size (16 for PCM)
    byte_stream.write(struct.pack('<H', 1))           # PCM format
    byte_stream.write(struct.pack('<H', 2))           # 2 Channels (Stereo)
    byte_stream.write(struct.pack('<I', sample_rate)) # Sample rate
    byte_stream.write(struct.pack('<I', sample_rate * 4)) # Byte rate
    byte_stream.write(struct.pack('<H', 4))           # Block align
    byte_stream.write(struct.pack('<H', 16))          # Bits per sample

    # Sub-chunk 2 (data)
    byte_stream.write(b'data')
    byte_stream.write(struct.pack('<I', num_samples * 4))
    for s in raw_samples:
        clamped = max(-32767, min(32767, s))
        byte_stream.write(struct.pack('<hh', clamped, clamped))

    byte_stream.seek(0)
    try:
        snd = pygame.mixer.Sound(byte_stream)
        snd.set_volume(0.6)
        return snd
    except Exception:
        return None

# Generate Sounds
snd_shoot = generate_wav("shoot")
snd_explode = generate_wav("explode")
snd_powerup = generate_wav("powerup")
snd_hit = generate_wav("hit")

def play_sfx(snd):
    if snd and pygame.mixer.get_init():
        snd.play()

# ==============================
# PALETTE
# ==============================
SPACE = (3, 5, 20)
WHITE = (240, 245, 255)
CYAN = (50, 220, 255)
BLUE = (60, 120, 255)
ORANGE = (255, 140, 40)
NEON_GREEN = (50, 255, 120)
ENEMY_RED = (255, 60, 80)
ENEMY_DARK = (180, 20, 50)
YELLOW = (255, 220, 60)
HEALTH_GREEN = (40, 225, 120)
BAR_BG = (40, 40, 60)
PURPLE = (180, 50, 230)
GOLD = (255, 215, 0)

# ==============================
# STARS BACKGROUND
# ==============================
stars = []
for _ in range(160):
    stars.append([
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT),
        random.randint(1, 3),
        random.uniform(0.5, 2.5)
    ])


# ==============================
# PARTICLE SYSTEM
# ==============================
class Particle:
    def __init__(self, x, y, palette=None):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 7)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifetime = random.randint(18, 30)
        self.color = random.choice(palette or [YELLOW, ORANGE, ENEMY_RED, WHITE])
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        if self.radius > 1 and self.lifetime % 6 == 0:
            self.radius -= 1

    def draw(self):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)


# ==============================
# LASER BULLETS
# ==============================
class Bullet:
    def __init__(self, x, y, vx=0, vy=-14, color=NEON_GREEN, is_enemy=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.width = 4
        self.height = 16
        self.color = color
        self.is_enemy = is_enemy

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self):
        pygame.draw.rect(
            screen,
            self.color,
            (self.x - 2, self.y - 2, self.width + 4, self.height + 4),
            border_radius=3
        )
        pygame.draw.rect(
            screen,
            WHITE if not self.is_enemy else YELLOW,
            (self.x, self.y, self.width, self.height),
            border_radius=2
        )

    def get_rect(self):
        return pygame.Rect(self.x - 2, self.y - 2, self.width + 4, self.height + 4)


# ==============================
# POWER-UP CLASS
# ==============================
class PowerUp:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.type = random.choice(["TRIPLE", "HEALTH"])
        self.color = YELLOW if self.type == "TRIPLE" else HEALTH_GREEN
        self.vy = 2.0
        self.radius = 14
        self.pulse = 0

    def update(self):
        self.y += self.vy
        self.pulse += 0.08

    def draw(self):
        r = self.radius + math.sin(self.pulse) * 3
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(r), 2)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 6)

    def get_rect(self):
        return pygame.Rect(self.x - 14, self.y - 14, 28, 28)


# ==============================
# STANDARD ENEMY CRAFT
# ==============================
class Enemy:
    def __init__(self):
        self.x = random.randint(60, WIDTH - 60)
        self.y = random.randint(-150, -40)
        self.speed_y = random.uniform(2.0, 3.2)
        self.wave_offset = random.uniform(0, math.pi * 2)
        self.wave_speed = random.uniform(0.03, 0.05)
        self.wave_amplitude = random.uniform(1.5, 2.5)
        self.shoot_timer = random.randint(40, 100)

    def update(self, enemy_bullets):
        self.y += self.speed_y
        self.x += math.sin(self.wave_offset) * self.wave_amplitude
        self.wave_offset += self.wave_speed

        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and 50 < self.y < HEIGHT - 150:
            enemy_bullets.append(Bullet(self.x, self.y + 25, vy=7, color=ENEMY_RED, is_enemy=True))
            self.shoot_timer = random.randint(80, 150)

    def draw(self):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(screen, YELLOW, (x, y - 18), 5)
        pygame.draw.polygon(
            screen,
            ENEMY_RED,
            [(x, y + 25), (x - 25, y - 15), (x, y - 8), (x + 25, y - 15)]
        )
        pygame.draw.polygon(screen, ENEMY_DARK, [(x, y + 10), (x - 10, y - 5), (x + 10, y - 5)])
        pygame.draw.circle(screen, CYAN, (x, y + 2), 3)

    def get_rect(self):
        return pygame.Rect(self.x - 22, self.y - 12, 44, 36)


# ==============================
# MOTHERSHIP BOSS CLASS
# ==============================
class Boss:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = -180
        self.target_y = 110
        self.speed_x = 3.5
        self.max_health = 1200
        self.health = 1200
        self.shoot_timer = 0
        self.phase_time = 0

    def update(self, enemy_bullets):
        if self.y < self.target_y:
            self.y += 2.0
            return

        self.x += self.speed_x
        if self.x < 150 or self.x > WIDTH - 150:
            self.speed_x *= -1

        self.phase_time += 1
        self.shoot_timer += 1

        if self.shoot_timer >= 45:
            self.shoot_timer = 0
            angles = [-3, -1.5, 0, 1.5, 3]
            for vx in angles:
                enemy_bullets.append(Bullet(self.x, self.y + 40, vx=vx, vy=6, color=PURPLE, is_enemy=True))

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        return self.health <= 0

    def draw(self):
        x, y = int(self.x), int(self.y)

        pygame.draw.circle(screen, ORANGE, (x - 70, y - 35), random.randint(8, 14))
        pygame.draw.circle(screen, ORANGE, (x + 70, y - 35), random.randint(8, 14))

        pygame.draw.polygon(
            screen,
            ENEMY_DARK,
            [(x, y + 60), (x - 140, y - 20), (x - 80, y - 45), (x + 80, y - 45), (x + 140, y - 20)]
        )
        pygame.draw.polygon(
            screen,
            ENEMY_RED,
            [(x, y + 45), (x - 100, y - 10), (x - 60, y - 30), (x + 60, y - 30), (x + 100, y - 10)]
        )

        pulse_core = 12 + int(math.sin(self.phase_time * 0.1) * 4)
        pygame.draw.circle(screen, PURPLE, (x, y + 5), pulse_core)
        pygame.draw.circle(screen, WHITE, (x, y + 5), 5)

        pygame.draw.rect(screen, CYAN, (x - 72, y + 10, 8, 20), border_radius=2)
        pygame.draw.rect(screen, CYAN, (x + 64, y + 10, 8, 20), border_radius=2)

    def get_rect(self):
        return pygame.Rect(self.x - 120, self.y - 30, 240, 80)


# ==============================
# PLAYER SPACESHIP
# ==============================
class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 100
        self.speed = 6
        self.shoot_cooldown = 0
        self.cooldown_limit = 10
        self.max_health = 100
        self.health = 100
        self.invulnerable_frames = 0
        self.triple_timer = 0

    def move(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_d]:
            self.x += self.speed
        if keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_s]:
            self.y += self.speed

        self.x = max(45, min(WIDTH - 45, self.x))
        self.y = max(80, min(HEIGHT - 50, self.y))

    def shoot(self, bullets_list):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and self.shoot_cooldown == 0:
            play_sfx(snd_shoot)
            if self.triple_timer > 0:
                bullets_list.append(Bullet(self.x, self.y - 15, vx=0, vy=-15, color=YELLOW))
                bullets_list.append(Bullet(self.x - 24, self.y, vx=-3, vy=-14, color=YELLOW))
                bullets_list.append(Bullet(self.x + 20, self.y, vx=3, vy=-14, color=YELLOW))
            else:
                bullets_list.append(Bullet(self.x - 24, self.y, vx=0, vy=-14, color=NEON_GREEN))
                bullets_list.append(Bullet(self.x + 20, self.y, vx=0, vy=-14, color=NEON_GREEN))

            self.shoot_cooldown = self.cooldown_limit

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1
        if self.triple_timer > 0:
            self.triple_timer -= 1

    def take_damage(self, amount):
        if self.invulnerable_frames <= 0:
            self.health = max(0, self.health - amount)
            self.invulnerable_frames = 20
            play_sfx(snd_hit)
            return True
        return False

    def draw(self):
        if self.invulnerable_frames > 0 and (self.invulnerable_frames // 3) % 2 == 0:
            return

        x, y = int(self.x), int(self.y)

        flame_len = random.randint(18, 26)
        pygame.draw.polygon(
            screen,
            ORANGE,
            [(x - 7, y + 25), (x, y + 25 + flame_len), (x + 7, y + 25)]
        )

        wing_color = YELLOW if self.triple_timer > 0 else BLUE
        pygame.draw.polygon(screen, wing_color, [(x, y - 35), (x - 45, y + 25), (x - 12, y + 18)])
        pygame.draw.polygon(screen, wing_color, [(x, y - 35), (x + 45, y + 25), (x + 12, y + 18)])
        pygame.draw.polygon(screen, WHITE, [(x, y - 48), (x - 16, y + 25), (x, y + 35), (x + 16, y + 25)])
        pygame.draw.polygon(screen, CYAN, [(x, y - 30), (x - 8, y + 5), (x + 8, y + 5)])
        pygame.draw.circle(screen, CYAN, (x - 12, y + 25), 4)
        pygame.draw.circle(screen, CYAN, (x + 12, y + 25), 4)

    def get_rect(self):
        return pygame.Rect(self.x - 25, self.y - 30, 50, 60)


# ==============================
# STATE & RESET HANDLERS
# ==============================
def reset_game():
    return Player(), [], [], [], [], [], None, 0, "PLAYING"

player, bullets, enemy_bullets, enemies, powerups, particles, boss, score, game_state = reset_game()
game_state = "MENU"
MAX_ENEMIES = 6
menu_tick = 0

# ==============================
# MAIN GAME LOOP
# ==============================
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if game_state == "MENU" and event.key == pygame.K_SPACE:
                player, bullets, enemy_bullets, enemies, powerups, particles, boss, score, game_state = reset_game()
            elif game_state in ["GAME_OVER", "VICTORY"] and event.key == pygame.K_r:
                player, bullets, enemy_bullets, enemies, powerups, particles, boss, score, game_state = reset_game()

    screen.fill(SPACE)

    # 1. Starfield Background
    for star in stars:
        star[1] += star[3]
        if star[1] > HEIGHT:
            star[1] = 0
            star[0] = random.randint(0, WIDTH)
        pygame.draw.circle(screen, (180, 200, 255), (int(star[0]), int(star[1])), star[2])

    # --------------------------
    # STATE: MENU
    # --------------------------
    if game_state == "MENU":
        menu_tick += 1
        title_surf = font_big.render("AI SPACE SHOOTER", True, CYAN)
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, HEIGHT // 3 - 50))

        subtitle = font_sub.render("WASD to Move  |  SPACEBAR to Shoot", True, WHITE)
        screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT // 3 + 30))

        pulse_alpha = abs(math.sin(menu_tick * 0.05))
        if pulse_alpha > 0.3:
            start_surf = font_hud.render("[ PRESS SPACEBAR TO LAUNCH MISSION ]", True, YELLOW)
            screen.blit(start_surf, (WIDTH // 2 - start_surf.get_width() // 2, HEIGHT // 2 + 80))

    # --------------------------
    # STATE: ACTIVE GAMEPLAY
    # --------------------------
    elif game_state == "PLAYING":
        if score >= 1500 and boss is None:
            boss = Boss()
            enemies.clear()

        if boss is None:
            while len(enemies) < MAX_ENEMIES:
                enemies.append(Enemy())

        player.move()
        player.shoot(bullets)
        player.draw()

        for bullet in bullets[:]:
            bullet.update()
            bullet.draw()
            if bullet.y < -30 or bullet.x < 0 or bullet.x > WIDTH:
                bullets.remove(bullet)

        for enemy in enemies[:]:
            enemy.update(enemy_bullets)
            enemy.draw()
            if enemy.y > HEIGHT + 50:
                enemies.remove(enemy)

        if boss:
            boss.update(enemy_bullets)
            boss.draw()

        for e_bullet in enemy_bullets[:]:
            e_bullet.update()
            e_bullet.draw()
            if e_bullet.y > HEIGHT + 30 or e_bullet.x < -30 or e_bullet.x > WIDTH + 30:
                enemy_bullets.remove(e_bullet)

        player_rect = player.get_rect()
        for p_up in powerups[:]:
            p_up.update()
            p_up.draw()
            if player_rect.colliderect(p_up.get_rect()):
                play_sfx(snd_powerup)
                if p_up.type == "TRIPLE":
                    player.triple_timer = 480
                    for _ in range(25):
                        particles.append(Particle(p_up.x, p_up.y, [YELLOW, WHITE]))
                elif p_up.type == "HEALTH":
                    player.health = min(player.max_health, player.health + 35)
                    for _ in range(25):
                        particles.append(Particle(p_up.x, p_up.y, [HEALTH_GREEN, WHITE]))
                powerups.remove(p_up)
            elif p_up.y > HEIGHT + 30:
                powerups.remove(p_up)

        for bullet in bullets[:]:
            b_rect = bullet.get_rect()
            for enemy in enemies[:]:
                if b_rect.colliderect(enemy.get_rect()):
                    play_sfx(snd_explode)
                    for _ in range(18):
                        particles.append(Particle(enemy.x, enemy.y))
                    if random.random() < 0.35:
                        powerups.append(PowerUp(enemy.x, enemy.y))
                    if bullet in bullets:
                        bullets.remove(bullet)
                    if enemy in enemies:
                        enemies.remove(enemy)
                    score += 100
                    break

            if boss and b_rect.colliderect(boss.get_rect()):
                for _ in range(5):
                    particles.append(Particle(bullet.x, bullet.y, [PURPLE, CYAN, WHITE]))
                if bullet in bullets:
                    bullets.remove(bullet)
                bullet_dmg = 25 if player.triple_timer > 0 else 20
                if boss.take_damage(bullet_dmg):
                    play_sfx(snd_explode)
                    for _ in range(120):
                        particles.append(Particle(boss.x + random.randint(-80, 80), boss.y + random.randint(-30, 30), [GOLD, PURPLE, ORANGE, WHITE]))
                    boss = None
                    score += 2000
                    game_state = "VICTORY"
                break

        for e_bullet in enemy_bullets[:]:
            if player_rect.colliderect(e_bullet.get_rect()):
                if player.take_damage(15):
                    for _ in range(12):
                        particles.append(Particle(e_bullet.x, e_bullet.y, [CYAN, WHITE, BLUE]))
                if e_bullet in enemy_bullets:
                    enemy_bullets.remove(e_bullet)

        for enemy in enemies[:]:
            if player_rect.colliderect(enemy.get_rect()):
                for _ in range(25):
                    particles.append(Particle(enemy.x, enemy.y))
                player.take_damage(30)
                enemies.remove(enemy)

        if player.health <= 0:
            play_sfx(snd_explode)
            for _ in range(50):
                particles.append(Particle(player.x, player.y, [ORANGE, YELLOW, WHITE, CYAN]))
            game_state = "GAME_OVER"

    for particle in particles[:]:
        particle.update()
        particle.draw()
        if particle.lifetime <= 0:
            particles.remove(particle)

    # --------------------------
    # HUD ELEMENTS
    # --------------------------
    if game_state in ["PLAYING", "GAME_OVER", "VICTORY"]:
        score_surf = font_hud.render(f"SCORE: {score:05d}", True, CYAN)
        screen.blit(score_surf, (25, 20))

        if player.triple_timer > 0:
            buff_ratio = player.triple_timer / 480
            buff_surf = font_hud.render("TRIPLE LASER", True, YELLOW)
            screen.blit(buff_surf, (25, 52))
            pygame.draw.rect(screen, BAR_BG, (170, 56, 120, 12), border_radius=3)
            pygame.draw.rect(screen, YELLOW, (170, 56, int(120 * buff_ratio), 12), border_radius=3)

        bar_x, bar_y, bar_w, bar_h = WIDTH - 245, 22, 220, 18
        pygame.draw.rect(screen, BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        current_hp_w = int((player.health / player.max_health) * bar_w)
        hp_color = HEALTH_GREEN if player.health > 40 else (ORANGE if player.health > 20 else ENEMY_RED)
        if current_hp_w > 0:
            pygame.draw.rect(screen, hp_color, (bar_x, bar_y, current_hp_w, bar_h), border_radius=4)
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)
        screen.blit(font_hud.render("SHIELD", True, WHITE), (bar_x - 85, 20))

        if boss:
            boss_bar_w = 400
            boss_bar_x = WIDTH // 2 - boss_bar_w // 2
            boss_bar_y = 22
            pygame.draw.rect(screen, BAR_BG, (boss_bar_x, boss_bar_y, boss_bar_w, 20), border_radius=4)
            current_boss_hp = int((boss.health / boss.max_health) * boss_bar_w)
            if current_boss_hp > 0:
                pygame.draw.rect(screen, PURPLE, (boss_bar_x, boss_bar_y, current_boss_hp, 20), border_radius=4)
            pygame.draw.rect(screen, WHITE, (boss_bar_x, boss_bar_y, boss_bar_w, 20), 2, border_radius=4)
            boss_label = font_hud.render("WARNING: MOTHERSHIP", True, PURPLE)
            screen.blit(boss_label, (WIDTH // 2 - boss_label.get_width() // 2, 48))

    if game_state == "GAME_OVER":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 5, 20, 200))
        screen.blit(overlay, (0, 0))
        go_text = font_big.render("MISSION FAILED", True, ENEMY_RED)
        res_text = font_hud.render("Press 'R' to Respawn & Restart", True, CYAN)
        screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(res_text, (WIDTH // 2 - res_text.get_width() // 2, HEIGHT // 2 + 25))

    elif game_state == "VICTORY":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 5, 20, 190))
        screen.blit(overlay, (0, 0))
        vic_text = font_big.render("GALAXY SAVED! VICTORY", True, GOLD)
        res_text = font_hud.render("Press 'R' to Play Again", True, CYAN)
        screen.blit(vic_text, (WIDTH // 2 - vic_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(res_text, (WIDTH // 2 - res_text.get_width() // 2, HEIGHT // 2 + 25))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()