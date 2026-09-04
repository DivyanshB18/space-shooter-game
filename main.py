import asyncio
import math
import random
import sys
import pygame

# ==============================
# INITIALIZE PYGAME (SAFE WEB MODE)
# ==============================
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

WIDTH = 900
HEIGHT = 650

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Space Shooter - Apex Edition")

clock = pygame.time.Clock()
font_hud = pygame.font.SysFont("consolas", 20, bold=True)
font_big = pygame.font.SysFont("consolas", 48, bold=True)
font_sub = pygame.font.SysFont("consolas", 18)

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

# Stars Background
stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 2), random.uniform(0.5, 2.0)] for _ in range(90)]

class Particle:
    def __init__(self, x, y, palette=None):
        self.x, self.y = x, y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.lifetime = random.randint(12, 22)
        self.color = random.choice(palette or [YELLOW, ORANGE, ENEMY_RED, WHITE])
        self.radius = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Bullet:
    def __init__(self, x, y, vx=0, vy=-14, color=NEON_GREEN, is_enemy=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.width, self.height = 4, 14
        self.color, self.is_enemy = color, is_enemy

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x - 2, self.y - 2, self.width + 4, self.height + 4), border_radius=2)

    def get_rect(self):
        return pygame.Rect(self.x - 2, self.y - 2, self.width + 4, self.height + 4)

class PowerUp:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.type = random.choice(["TRIPLE", "HEALTH"])
        self.color = YELLOW if self.type == "TRIPLE" else HEALTH_GREEN
        self.vy = 2.0
        self.radius = 12

    def update(self):
        self.y += self.vy

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius, 2)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 5)

    def get_rect(self):
        return pygame.Rect(self.x - 12, self.y - 12, 24, 24)

class Enemy:
    def __init__(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-120, -30)
        self.speed_y = random.uniform(2.0, 3.0)
        self.shoot_timer = random.randint(50, 110)

    def update(self, enemy_bullets):
        self.y += self.speed_y
        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and 50 < self.y < HEIGHT - 150:
            enemy_bullets.append(Bullet(self.x, self.y + 20, vy=6, color=ENEMY_RED, is_enemy=True))
            self.shoot_timer = random.randint(90, 160)

    def draw(self):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(screen, ENEMY_RED, [(x, y + 20), (x - 20, y - 12), (x, y - 5), (x + 20, y - 12)])

    def get_rect(self):
        return pygame.Rect(self.x - 18, self.y - 10, 36, 30)

class Boss:
    def __init__(self):
        self.x, self.y = WIDTH // 2, -150
        self.target_y, self.speed_x = 90, 3.0
        self.max_health, self.health = 800, 800
        self.shoot_timer = 0

    def update(self, enemy_bullets):
        if self.y < self.target_y:
            self.y += 2.0
            return
        self.x += self.speed_x
        if self.x < 120 or self.x > WIDTH - 120:
            self.speed_x *= -1
        self.shoot_timer += 1
        if self.shoot_timer >= 50:
            self.shoot_timer = 0
            for vx in [-2.5, 0, 2.5]:
                enemy_bullets.append(Bullet(self.x, self.y + 35, vx=vx, vy=5, color=PURPLE, is_enemy=True))

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        return self.health <= 0

    def draw(self):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(screen, ENEMY_DARK, [(x, y + 50), (x - 100, y - 15), (x + 100, y - 15)])
        pygame.draw.circle(screen, PURPLE, (x, y + 5), 14)

    def get_rect(self):
        return pygame.Rect(self.x - 90, self.y - 20, 180, 65)

class Player:
    def __init__(self):
        self.x, self.y = WIDTH // 2, HEIGHT - 90
        self.speed, self.shoot_cooldown = 5.5, 0
        self.max_health, self.health = 100, 100
        self.invulnerable = 0
        self.triple_timer = 0

    def move(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.x -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.x += self.speed
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.y -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.y += self.speed
        self.x = max(35, min(WIDTH - 35, self.x))
        self.y = max(60, min(HEIGHT - 40, self.y))

    def shoot(self, bullets_list):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and self.shoot_cooldown == 0:
            if self.triple_timer > 0:
                bullets_list.append(Bullet(self.x, self.y - 12, vx=0, vy=-14, color=YELLOW))
                bullets_list.append(Bullet(self.x - 18, self.y, vx=-2.5, vy=-13, color=YELLOW))
                bullets_list.append(Bullet(self.x + 18, self.y, vx=2.5, vy=-13, color=YELLOW))
            else:
                bullets_list.append(Bullet(self.x - 16, self.y, vx=0, vy=-14, color=NEON_GREEN))
                bullets_list.append(Bullet(self.x + 16, self.y, vx=0, vy=-14, color=NEON_GREEN))
            self.shoot_cooldown = 9

        if self.shoot_cooldown > 0: self.shoot_cooldown -= 1
        if self.invulnerable > 0: self.invulnerable -= 1
        if self.triple_timer > 0: self.triple_timer -= 1

    def take_damage(self, amount):
        if self.invulnerable <= 0:
            self.health = max(0, self.health - amount)
            self.invulnerable = 20
            return True
        return False

    def draw(self):
        if self.invulnerable > 0 and (self.invulnerable // 3) % 2 == 0:
            return
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(screen, YELLOW if self.triple_timer > 0 else BLUE, [(x, y - 28), (x - 35, y + 20), (x + 35, y + 20)])
        pygame.draw.polygon(screen, WHITE, [(x, y - 35), (x - 12, y + 20), (x + 12, y + 20)])

    def get_rect(self):
        return pygame.Rect(self.x - 20, self.y - 25, 40, 50)

def reset_game():
    return Player(), [], [], [], [], [], None, 0, "PLAYING"

async def main():
    player, bullets, enemy_bullets, enemies, powerups, particles, boss, score, game_state = reset_game()
    game_state = "MENU"
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

        for star in stars:
            star[1] += star[3]
            if star[1] > HEIGHT:
                star[1] = 0
                star[0] = random.randint(0, WIDTH)
            pygame.draw.circle(screen, (170, 190, 230), (int(star[0]), int(star[1])), star[2])

        if game_state == "MENU":
            t_surf = font_big.render("AI SPACE SHOOTER", True, CYAN)
            screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, HEIGHT // 3 - 30))
            sub = font_sub.render("WASD / Arrows to Move | SPACEBAR to Shoot", True, WHITE)
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 3 + 35))
            st_surf = font_hud.render("[ PRESS SPACEBAR TO PLAY ]", True, YELLOW)
            screen.blit(st_surf, (WIDTH // 2 - st_surf.get_width() // 2, HEIGHT // 2 + 60))

        elif game_state == "PLAYING":
            if score >= 1200 and boss is None:
                boss = Boss()
                enemies.clear()

            if boss is None and len(enemies) < 5:
                enemies.append(Enemy())

            player.move()
            player.shoot(bullets)
            player.draw()

            for b in bullets[:]:
                b.update()
                b.draw()
                if b.y < -20: bullets.remove(b)

            for e in enemies[:]:
                e.update(enemy_bullets)
                e.draw()
                if e.y > HEIGHT + 30: enemies.remove(e)

            if boss:
                boss.update(enemy_bullets)
                boss.draw()

            for eb in enemy_bullets[:]:
                eb.update()
                eb.draw()
                if eb.y > HEIGHT + 20: enemy_bullets.remove(eb)

            p_rect = player.get_rect()
            for p_up in powerups[:]:
                p_up.update()
                p_up.draw()
                if p_rect.colliderect(p_up.get_rect()):
                    if p_up.type == "TRIPLE": player.triple_timer = 400
                    elif p_up.type == "HEALTH": player.health = min(100, player.health + 30)
                    powerups.remove(p_up)
                elif p_up.y > HEIGHT + 20: powerups.remove(p_up)

            for b in bullets[:]:
                br = b.get_rect()
                for e in enemies[:]:
                    if br.colliderect(e.get_rect()):
                        for _ in range(12): particles.append(Particle(e.x, e.y))
                        if random.random() < 0.35: powerups.append(PowerUp(e.x, e.y))
                        if b in bullets: bullets.remove(b)
                        if e in enemies: enemies.remove(e)
                        score += 100
                        break
                if boss and br.colliderect(boss.get_rect()):
                    if b in bullets: bullets.remove(b)
                    if boss.take_damage(20):
                        boss = None
                        score += 2000
                        game_state = "VICTORY"
                    break

            for eb in enemy_bullets[:]:
                if p_rect.colliderect(eb.get_rect()):
                    player.take_damage(15)
                    if eb in enemy_bullets: enemy_bullets.remove(eb)

            for e in enemies[:]:
                if p_rect.colliderect(e.get_rect()):
                    player.take_damage(25)
                    enemies.remove(e)

            if player.health <= 0:
                game_state = "GAME_OVER"

        for pt in particles[:]:
            pt.update()
            pt.draw()
            if pt.lifetime <= 0: particles.remove(pt)

        if game_state in ["PLAYING", "GAME_OVER", "VICTORY"]:
            screen.blit(font_hud.render(f"SCORE: {score:05d}", True, CYAN), (20, 15))
            hp_w = int((player.health / 100) * 180)
            pygame.draw.rect(screen, BAR_BG, (WIDTH - 210, 20, 180, 15), border_radius=3)
            if hp_w > 0: pygame.draw.rect(screen, HEALTH_GREEN if player.health > 35 else ENEMY_RED, (WIDTH - 210, 20, hp_w, 15), border_radius=3)

        if game_state == "GAME_OVER":
            go = font_big.render("MISSION FAILED", True, ENEMY_RED)
            rs = font_hud.render("Press 'R' to Restart", True, CYAN)
            screen.blit(go, (WIDTH // 2 - go.get_width() // 2, HEIGHT // 2 - 40))
            screen.blit(rs, (WIDTH // 2 - rs.get_width() // 2, HEIGHT // 2 + 20))

        elif game_state == "VICTORY":
            vic = font_big.render("GALAXY SAVED!", True, GOLD)
            rs = font_hud.render("Press 'R' to Play Again", True, CYAN)
            screen.blit(vic, (WIDTH // 2 - vic.get_width() // 2, HEIGHT // 2 - 40))
            screen.blit(rs, (WIDTH // 2 - rs.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(60)

        # Critical: Hand over execution to browser event loop
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())