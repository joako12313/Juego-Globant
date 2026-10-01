"""SHADOW: un plataformas de precision temporal, hecho con Pygame."""

from __future__ import annotations

import math
import random
import sys
from array import array
from collections import deque
from dataclasses import dataclass

import pygame

from settings import (
    COLORS, FPS, GRAVITY, HEIGHT, JUMP_SPEED, MAX_FALL_SPEED, PLAYER_ACCEL,
    PLAYER_SIZE, PLAYER_SPEED, SHADOW_DELAY, TITLE, WIDTH,
)


pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    AUDIO_READY = True
except pygame.error:
    AUDIO_READY = False

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption(TITLE)
CLOCK = pygame.time.Clock()
WORLD = pygame.Surface((WIDTH, HEIGHT)).convert()
FONTS = {
    "tiny": pygame.font.Font(None, 19),
    "small": pygame.font.Font(None, 24),
    "body": pygame.font.Font(None, 30),
    "title": pygame.font.Font(None, 88),
    "heading": pygame.font.Font(None, 48),
}


def sound_tone(frequency: int, duration: float, volume: float = 0.16) -> pygame.mixer.Sound | None:
    if not AUDIO_READY:
        return None
    sample_rate = 22050
    samples = array("h")
    for index in range(int(sample_rate * duration)):
        envelope = min(1.0, index / 160) * max(0.0, 1 - index / (sample_rate * duration))
        samples.append(int(32767 * volume * envelope * math.sin(math.tau * frequency * index / sample_rate)))
    return pygame.mixer.Sound(buffer=samples.tobytes())


SOUNDS = {
    "jump": sound_tone(470, 0.11),
    "switch": sound_tone(760, 0.16),
    "door": sound_tone(310, 0.25),
    "hurt": sound_tone(115, 0.24),
    "win": sound_tone(640, 0.42),
    "ui": sound_tone(520, 0.07, 0.1),
    "echo": sound_tone(880, 0.12),
}


def play_sound(name: str) -> None:
    sound = SOUNDS.get(name)
    if sound is not None:
        sound.play()


@dataclass
class EchoFrame:
    time: float
    x: float
    y: float
    vx: float
    vy: float
    facing: int
    grounded: bool
    action: str
    animation_time: float = 0.0


class EchoHistory:
    """Guarda estados por tiempo y consulta el estado exacto de t - retraso."""

    def __init__(self, delay: float):
        self.delay = delay
        self.frames: deque[EchoFrame] = deque()

    def reset(self, frame: EchoFrame) -> None:
        self.frames.clear()
        self.frames.append(frame)

    def record(self, frame: EchoFrame) -> None:
        self.frames.append(frame)
        cutoff = frame.time - self.delay - 0.12
        while len(self.frames) > 2 and self.frames[1].time < cutoff:
            self.frames.popleft()

    def sample(self, target_time: float) -> EchoFrame:
        if target_time <= self.frames[0].time:
            return self.frames[0]
        previous = self.frames[0]
        for following in list(self.frames)[1:]:
            if following.time >= target_time:
                span = following.time - previous.time
                blend = 0.0 if span <= 0 else (target_time - previous.time) / span
                chosen = previous if blend < 0.5 else following
                return EchoFrame(
                    target_time,
                    previous.x + (following.x - previous.x) * blend,
                    previous.y + (following.y - previous.y) * blend,
                    previous.vx + (following.vx - previous.vx) * blend,
                    previous.vy + (following.vy - previous.vy) * blend,
                    chosen.facing,
                    chosen.grounded,
                    chosen.action,
                    (previous.animation_time + (following.animation_time - previous.animation_time) * blend
                     if previous.action == following.action else chosen.animation_time),
                )
            previous = following
        return previous


@dataclass
class MovingPlatform:
    rect: pygame.Rect
    start: tuple[int, int]
    end: tuple[int, int]
    speed: float
    phase: float = 0.0

    def update(self, dt: float) -> None:
        self.phase = (self.phase + dt * self.speed / max(1, math.dist(self.start, self.end))) % 2.0
        amount = self.phase if self.phase <= 1 else 2 - self.phase
        self.rect.x = round(self.start[0] + (self.end[0] - self.start[0]) * amount)
        self.rect.y = round(self.start[1] + (self.end[1] - self.start[1]) * amount)


@dataclass
class Mechanism:
    rect: pygame.Rect
    target: str
    shadow_only: bool = False
    active: bool = False
    was_pressed: bool = False
    label: str = ""


LEVELS = [
    {
        "title": "EL PRIMER ECO",
        "subtitle": "Deja el eco a la izquierda de la cornisa; sube sobre el rastro y salta hacia la ruta alta.",
        "width": 3000,
        "spawn": (90, 568),
        "exit": (2830, 530),
        "platforms": [(0, 620, 450, 100), (570, 620, 1260, 100),
                      (1970, 620, 1030, 100), (920, 460, 230, 18),
                      (1180, 480, 175, 18), (1390, 430, 100, 18)],
        "hazards": [(450, 655, 120, 40), (1040, 608, 350, 52),
                (1830, 655, 140, 40)],
        "doors": {"gate": (1790, 450, 36, 170), "seal": (2660, 450, 36, 170)},
        "switches": [(1620, 584, "gate", True, "ECHO LANDING"),
                     (2380, 584, "seal", True, "ECHO")],
        "moving": [],
        "platform_groups": {},
        "checkpoints": [(2040, 570)],
        "objective": "El eco es tu escalon y la llave de dos cierres",
    },
    {
        "title": "EL PUENTE DE MEMORIA",
        "subtitle": "El primer foso se mueve; el segundo puente solo existe cuando llega tu eco.",
        "width": 4000,
        "spawn": (90, 568),
        "exit": (3820, 530),
        "platforms": [(0, 620, 400, 100), (730, 620, 600, 100),
                      (1600, 620, 560, 100), (2470, 620, 1530, 100)],
        "hazards": [(400, 655, 330, 40), (1330, 655, 270, 40),
                    (2160, 655, 310, 40)],
        "doors": {"airlock": (2110, 450, 36, 170), "exit_seal": (3670, 450, 36, 170)},
        "switches": [(1050, 584, "bridge_west", True, "ECHO BRIDGE"),
                     (1880, 584, "airlock", True, "ECHO LOCK"),
                     (3390, 584, "exit_seal", True, "ECHO LOCK")],
        "moving": [((420, 560, 160, 18), (420, 560), (560, 520), 100),
                   ((2180, 560, 160, 18), (2180, 560), (2350, 515), 105)],
        "platform_groups": {"bridge_west": [(1330, 545, 270, 18)]},
        "checkpoints": [(790, 570), (1660, 570), (2530, 570)],
        "objective": "Dos puentes moviles, un puente eco y dos cierres",
    },
    {
        "title": "LA CAMARA FINAL",
        "subtitle": "Prepara cada recorrido: dos puentes eco, dos ascensores y dos cierres separan la salida.",
        "width": 5500,
        "spawn": (90, 568),
        "exit": (5290, 530),
        "platforms": [(0, 620, 410, 100), (710, 620, 410, 100),
                  (1470, 620, 400, 100), (2200, 620, 380, 100),
                  (2910, 620, 400, 100), (3620, 620, 430, 100),
                  (4380, 620, 1120, 100), (3100, 475, 120, 18)],
        "hazards": [(410, 655, 300, 40), (1120, 655, 350, 40),
                (1870, 655, 330, 40), (2580, 655, 330, 40),
                (2950, 608, 210, 52), (3310, 655, 310, 40),
                (4050, 655, 330, 40)],
        "doors": {"mid_seal": (1840, 450, 36, 170),
                  "final_seal": (3270, 450, 36, 170)},
        "switches": [(930, 584, "bridge_alpha", True, "ECHO BRIDGE"),
                     (1660, 584, "mid_seal", True, "ECHO LOCK"),
                     (2440, 584, "bridge_beta", True, "ECHO BRIDGE"),
                     (3160, 439, "final_seal", True, "ECHO LOCK"),
                     (3870, 584, "bridge_gamma", True, "ECHO BRIDGE")],
        "moving": [((420, 560, 160, 18), (420, 560), (540, 520), 100),
                   ((1880, 560, 160, 18), (1880, 560), (2040, 510), 108),
                   ((3320, 560, 160, 18), (3320, 560), (3500, 510), 112)],
        "platform_groups": {"bridge_alpha": [(1120, 545, 350, 18)],
                            "bridge_beta": [(2580, 545, 330, 18)],
                            "bridge_gamma": [(4050, 545, 330, 18)]},
        "checkpoints": [(750, 570), (1510, 570), (2260, 570),
                (2910, 570), (3690, 570), (4440, 570)],
        "objective": "Cruza seis fosos y resuelve cinco mecanismos de eco",
    },
]


class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int], velocity: tuple[float, float], life: float, radius: int):
        self.x, self.y = x, y
        self.vx, self.vy = velocity
        self.color = color
        self.life = life
        self.max_life = life
        self.radius = radius

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 250 * dt
        self.life -= dt
        return self.life > 0


class Game:
    def __init__(self):
        self.state = "MAIN_MENU"
        self.level_index = 0
        self.sim_time = 0.0
        self.camera_x = 0.0
        self.particles: list[Particle] = []
        self.damage_timer = 0.0
        self.toast_timer = 0.0
        self._last_animation = "idle"
        self.buttons: list[tuple[str, pygame.Rect, str]] = []
        self.load_level(0)

    def load_level(self, index: int) -> None:
        self.level_index = index
        data = LEVELS[index]
        self.level = data
        self.platforms = [pygame.Rect(*item) for item in data["platforms"]]
        self.hazards = [pygame.Rect(*item) for item in data["hazards"]]
        self.doors = {name: pygame.Rect(*bounds) for name, bounds in data["doors"].items()}
        self.platform_groups = {
            name: [pygame.Rect(*bounds) for bounds in group]
            for name, group in data["platform_groups"].items()
        }
        self.platform_group_active = {name: False for name in self.platform_groups}
        self.checkpoints = [tuple(point) for point in data["checkpoints"]]
        self.active_checkpoint = -1
        self.door_open = {name: False for name in self.doors}
        self.mechanisms = [Mechanism(pygame.Rect(x, y, 36, 36), target, shadow_only, False, False, label)
                           for x, y, target, shadow_only, label in data["switches"]]
        self.moving = [MovingPlatform(pygame.Rect(*item[0]), item[1], item[2], item[3]) for item in data["moving"]]
        self.actor = pygame.Rect(*data["spawn"], *PLAYER_SIZE)
        self.x, self.y = float(self.actor.x), float(self.actor.y)
        self.vx = self.vy = 0.0
        self.facing = 1
        self.grounded = False
        self.animation = "idle"
        self.animation_time = 0.0
        self.sim_time = 0.0
        self.camera_x = 0.0
        self.damage_timer = 0.0
        self.particles.clear()
        self.history = EchoHistory(SHADOW_DELAY)
        self.history.reset(self.make_frame(0.0))
        self.echo = self.history.sample(0.0)
        self.echo_rect = pygame.Rect(round(self.echo.x), round(self.echo.y), *PLAYER_SIZE)
        self.previous_echo_rect = self.echo_rect.copy()
        self.echo_ready = False

    def make_frame(self, timestamp: float) -> EchoFrame:
        return EchoFrame(timestamp, self.x, self.y, self.vx, self.vy, self.facing,
                         self.grounded, self.animation, self.animation_time)

    def burst(self, x: float, y: float, color: tuple[int, int, int], count: int = 9) -> None:
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(45, 190)
            self.particles.append(Particle(x, y, color,
                                          (math.cos(angle) * speed, math.sin(angle) * speed - 35),
                                          random.uniform(0.22, 0.58), random.randint(2, 4)))

    def reset_level(self) -> None:
        self.load_level(self.level_index)
        self.state = "PLAYING"

    def respawn(self) -> None:
        checkpoint_index = self.active_checkpoint
        spawn = self.checkpoints[checkpoint_index] if checkpoint_index >= 0 else self.level["spawn"]
        self.load_level(self.level_index)
        self.active_checkpoint = checkpoint_index
        self.x, self.y = map(float, spawn)
        self.actor.topleft = (round(self.x), round(self.y))
        initial_frame = self.make_frame(0.0)
        self.history.reset(initial_frame)
        self.echo = initial_frame
        self.echo_rect = pygame.Rect(round(self.x), round(self.y), *PLAYER_SIZE)
        self.previous_echo_rect = self.echo_rect.copy()
        self.state = "PLAYING"

    def start_level(self, index: int) -> None:
        self.load_level(index)
        self.state = "PLAYING"

    def actor_solids(self) -> list[pygame.Rect]:
        solids = self.platforms + [item.rect for item in self.moving]
        for name, group in self.platform_groups.items():
            if self.platform_group_active[name]:
                solids.extend(group)
        solids += [rect for key, rect in self.doors.items() if not self.door_open[key]]
        return solids

    def activate_target(self, target: str) -> None:
        if target in self.door_open:
            self.door_open[target] = True
        elif target in self.platform_group_active:
            self.platform_group_active[target] = True

    def resolve_actor(
        self,
        allow_echo: bool,
        dt: float,
        carry_delta: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        """Barre el movimiento por ejes para resolver cruces aunque no haya solape final."""
        solids = self.actor_solids()
        width, height = PLAYER_SIZE
        start_x, start_y = self.x, self.y
        carry_x, carry_y = carry_delta
        moved_y = start_y + carry_y
        target_x = start_x + carry_x + self.vx * dt

        # Eje X: el rango vertical se evalua en la altura transportada por la plataforma.
        if target_x > start_x:
            for solid in solids:
                overlaps_y = moved_y < solid.bottom and moved_y + height > solid.top
                if overlaps_y and start_x < solid.left and target_x + width > solid.left:
                    target_x = min(target_x, float(solid.left - width))
        elif target_x < start_x:
            for solid in solids:
                overlaps_y = moved_y < solid.bottom and moved_y + height > solid.top
                if overlaps_y and start_x + width > solid.right and target_x < solid.right:
                    target_x = max(target_x, float(solid.right))
        if target_x != start_x + carry_x + self.vx * dt:
            self.vx = 0.0
        self.x = target_x
        self.actor.x = round(self.x)

        # Eje Y: se usa el borde anterior y el previsto para detectar impactos barridos.
        start_bottom = start_y + height
        target_y = moved_y + self.vy * dt
        was_grounded = self.grounded
        self.grounded = False
        if target_y >= start_y:
            landing_top: int | None = None
            for solid in solids:
                overlaps_x = self.actor.right > solid.left and self.actor.left < solid.right
                crosses_top = start_bottom <= solid.top and target_y + height >= solid.top
                if overlaps_x and crosses_top and (landing_top is None or solid.top < landing_top):
                    landing_top = solid.top
            if landing_top is not None:
                target_y = float(landing_top - height)
                self.vy = 0.0
                self.grounded = True
        elif target_y < start_y:
            ceiling_bottom: int | None = None
            for solid in solids:
                overlaps_x = self.actor.right > solid.left and self.actor.left < solid.right
                crosses_bottom = start_y >= solid.bottom and target_y <= solid.bottom
                if overlaps_x and crosses_bottom and (ceiling_bottom is None or solid.bottom > ceiling_bottom):
                    ceiling_bottom = solid.bottom
            if ceiling_bottom is not None:
                target_y = float(ceiling_bottom)
                self.vy = 0.0

        # El eco funciona como plataforma unidireccional, sin alterar su trayectoria grabada.
        if allow_echo and self.sim_time >= SHADOW_DELAY and self.vy >= 0:
            echo_rect = self.echo_rect
            overlaps_echo = self.actor.right > echo_rect.left + 4 and self.actor.left < echo_rect.right - 4
            crosses_echo = (start_bottom <= self.previous_echo_rect.top
                            and target_y + height >= echo_rect.top)
            if overlaps_echo and crosses_echo:
                target_y = float(echo_rect.top - height)
                self.vy = 0.0
                self.grounded = True

        if carry_delta != (0.0, 0.0) and was_grounded:
            for platform in self.moving:
                overlaps_platform = self.actor.right > platform.rect.left and self.actor.left < platform.rect.right
                if overlaps_platform and abs(target_y + height - platform.rect.top) <= 1:
                    target_y = float(platform.rect.top - height)
                    self.vy = 0.0
                    self.grounded = True
                    break

        echo_was_supporting = (
            allow_echo
            and self.sim_time >= SHADOW_DELAY
            and was_grounded
            and abs(start_bottom - self.previous_echo_rect.top) <= 2
            and start_x + width > self.previous_echo_rect.left
            and start_x < self.previous_echo_rect.right
        )
        if echo_was_supporting:
            overlaps_echo = self.actor.right > self.echo_rect.left and self.actor.left < self.echo_rect.right
            if overlaps_echo and abs(target_y + height - self.echo_rect.top) <= 2:
                target_y = float(self.echo_rect.top - height)
                self.vy = 0.0
                self.grounded = True

        self.y = target_y
        self.actor.y = round(self.y)
        if self.grounded and not was_grounded:
            self.burst(self.actor.centerx, self.actor.bottom, COLORS["cyan"], 5)

    def update_echo(self) -> None:
        self.previous_echo_rect = self.echo_rect.copy()
        self.echo = self.history.sample(self.sim_time - SHADOW_DELAY)
        self.echo_rect = pygame.Rect(round(self.echo.x), round(self.echo.y), *PLAYER_SIZE)
        if self.sim_time >= SHADOW_DELAY and not self.echo_ready:
            self.echo_ready = True
            play_sound("echo")

    def update_mechanisms(self) -> None:
        for mechanism in self.mechanisms:
            player_press = not mechanism.shadow_only and self.actor.colliderect(mechanism.rect)
            echo_press = mechanism.shadow_only and self.sim_time >= SHADOW_DELAY and self.echo_rect.colliderect(mechanism.rect)
            pressed = player_press or echo_press
            if pressed and not mechanism.was_pressed and not mechanism.active:
                mechanism.active = True
                self.activate_target(mechanism.target)
                play_sound("switch")
                play_sound("door")
                self.burst(mechanism.rect.centerx, mechanism.rect.centery, COLORS["cyan"], 16)
                self.toast_timer = 1.15
            mechanism.was_pressed = pressed

    def update(self, dt: float, jump_pressed: bool) -> None:
        if self.state != "PLAYING":
            return
        dt = min(dt, 1 / 30)
        previous = self.actor.copy()
        was_grounded = self.grounded
        self.sim_time += dt
        self.update_echo()
        carry_delta = (0.0, 0.0)
        for platform in self.moving:
            old_rect = platform.rect.copy()
            platform.update(dt)
            touching_platform = (previous.bottom <= old_rect.top + 6
                                 and previous.bottom >= old_rect.top - 6
                                 and previous.right > old_rect.left
                                 and previous.left < old_rect.right)
            if was_grounded and touching_platform:
                carry_delta = (platform.rect.x - old_rect.x, platform.rect.y - old_rect.y)
        echo_supporting = (
            was_grounded
            and self.sim_time >= SHADOW_DELAY
            and abs(previous.bottom - self.previous_echo_rect.top) <= 2
            and previous.right > self.previous_echo_rect.left
            and previous.left < self.previous_echo_rect.right
        )
        if echo_supporting and carry_delta == (0.0, 0.0):
            carry_delta = (self.echo_rect.x - self.previous_echo_rect.x,
                           self.echo_rect.y - self.previous_echo_rect.y)

        keys = pygame.key.get_pressed()
        horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        target_speed = horizontal * PLAYER_SPEED
        acceleration = PLAYER_ACCEL * dt
        if self.vx < target_speed:
            self.vx = min(target_speed, self.vx + acceleration)
        elif self.vx > target_speed:
            self.vx = max(target_speed, self.vx - acceleration)
        if horizontal:
            self.facing = horizontal
        if jump_pressed and self.grounded:
            self.vy = -JUMP_SPEED
            self.grounded = False
            self.animation = "jump"
            play_sound("jump")
            self.burst(self.actor.centerx, self.actor.bottom, COLORS["gold"], 7)

        self.vy = min(MAX_FALL_SPEED, self.vy + GRAVITY * dt)
        self.resolve_actor(True, dt, carry_delta)
        if self.actor.left < 0:
            self.actor.left = 0
            self.x = float(self.actor.x)
        if self.actor.right > self.level["width"]:
            self.actor.right = self.level["width"]
            self.x = float(self.actor.x)
        if self.grounded:
            self.animation = "walk" if abs(self.vx) > 35 else "idle"
        else:
            self.animation = "jump" if self.vy < 0 else "fall"
        if self.animation != self._last_animation:
            self.animation_time = 0
        self.animation_time += dt
        self._last_animation = self.animation

        self.history.record(self.make_frame(self.sim_time))
        self.update_mechanisms()
        for checkpoint_index, (checkpoint_x, checkpoint_y) in enumerate(self.checkpoints):
            checkpoint_rect = pygame.Rect(checkpoint_x - 12, checkpoint_y - 8, 58, 64)
            if self.actor.colliderect(checkpoint_rect) and checkpoint_index > self.active_checkpoint:
                self.active_checkpoint = checkpoint_index
                self.toast_timer = 1.4
                play_sound("switch")
                self.burst(checkpoint_x + 12, checkpoint_y + 20, COLORS["gold"], 12)
        self.particles = [particle for particle in self.particles if particle.update(dt)]
        self.damage_timer = max(0.0, self.damage_timer - dt)
        self.toast_timer = max(0.0, self.toast_timer - dt)
        target_camera = max(0, min(self.level["width"] - WIDTH, self.actor.centerx - WIDTH * 0.42))
        self.camera_x += (target_camera - self.camera_x) * min(1, dt * 4.5)

        if self.actor.top > HEIGHT + 180 or any(self.actor.colliderect(hazard) for hazard in self.hazards):
            self.damage_timer = 0.2
            play_sound("hurt")
            self.respawn()
            self.damage_timer = 0.3
            return
        exit_rect = pygame.Rect(*self.level["exit"], 42, 90)
        if self.actor.colliderect(exit_rect):
            self.state = "GAME_COMPLETE" if self.level_index == 2 else "LEVEL_COMPLETE"
            play_sound("win")
            self.burst(exit_rect.centerx, exit_rect.centery, COLORS["gold"], 30)

    def _draw_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                   color: tuple[int, int, int], position: tuple[int, int], center: bool = False) -> pygame.Rect:
        image = font.render(text, True, color)
        rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
        surface.blit(image, rect)
        return rect

    def background(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["ink"])
        palette = [(14, 31, 52), (20, 26, 54), (11, 39, 50)]
        tint = palette[self.level_index]
        for y in range(0, HEIGHT, 4):
            ratio = y / HEIGHT
            color = tuple(int(COLORS["ink"][i] * (1 - ratio) + tint[i] * ratio) for i in range(3))
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))
        for layer, count, size, speed, alpha in [(0, 22, 3, 0.08, 70), (1, 15, 5, 0.17, 95)]:
            for index in range(count):
                x = int((index * 173 - self.camera_x * speed) % (WIDTH + 80))
                y = 86 + (index * 83 + layer * 39) % 455
                glow = pygame.Surface((size * 5, size * 5), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*COLORS["cyan"], alpha), (size * 2, size * 2), size * 2)
                surface.blit(glow, (x - size * 2, y - size * 2))
        # Siluetas arquitectonicas con paralaje lento.
        offset = int(self.camera_x * 0.24) % 360
        for index in range(-1, 6):
            x = index * 360 - offset
            height = 160 + (index * 61 % 150)
            pygame.draw.rect(surface, (12, 24, 40), (x, 570 - height, 190, height))
            pygame.draw.rect(surface, (21, 42, 60), (x + 23, 570 - height + 25, 5, height - 25))
            for window_y in range(590 - height, 550, 38):
                pygame.draw.line(surface, (28, 54, 72), (x + 12, window_y), (x + 174, window_y), 2)

    def draw_player(self, surface: pygame.Surface, rect: pygame.Rect, is_echo: bool = False,
                    frame: EchoFrame | None = None, alpha: int = 255) -> None:
        if not is_echo and self.damage_timer > 0 and int(self.damage_timer * 18) % 2 == 0:
            return

        animation = frame.action if is_echo and frame is not None else self.animation
        animation_time = frame.animation_time if is_echo and frame is not None else self.animation_time
        facing = frame.facing if is_echo and frame is not None else self.facing
        x, y = 3, 3
        target = pygame.Surface((42, 56), pygame.SRCALPHA)
        bob = math.sin(animation_time * 12) * 2 if animation == "walk" else 0
        body = pygame.Rect(x + 5, round(y + 19 + bob), 25, 29)

        if is_echo:
            shadow_alpha = min(225, alpha)
            shadow = (4, 4, 9, shadow_alpha)
            hood = (8, 7, 15, shadow_alpha)
            seam = (17, 15, 30, shadow_alpha)
            eye = (35, 29, 52, shadow_alpha)
            outline = (37, 31, 57, shadow_alpha)
            pygame.draw.ellipse(target, (3, 4, 11, shadow_alpha // 3), (x + 3, y + 43, 30, 9))
        else:
            shadow = (17, 37, 52)
            hood = (232, 198, 148)
            seam = (133, 244, 222)
            eye = (15, 33, 45)
            outline = (25, 47, 63)
            pygame.draw.ellipse(target, (3, 8, 18), (x + 3, y + 43, 30, 9))

        # Una unica silueta y una unica animacion para el personaje y su eco.
        pygame.draw.polygon(target, shadow, [(body.left, body.top + 8), (body.centerx, body.top),
                                              (body.right, body.top + 7), (body.right - 3, body.bottom),
                                              (body.left + 3, body.bottom)])
        pygame.draw.ellipse(target, hood, (x + 7, y + 2 + bob, 21, 23))
        pygame.draw.arc(target, outline, (x + 5, y, 25, 28), math.pi, math.tau, 5)
        eye_x = x + (22 if facing > 0 else 11)
        pygame.draw.circle(target, eye, (eye_x, y + 13 + round(bob)), 2)
        pygame.draw.line(target, seam, (body.centerx, body.top + 6),
                         (body.centerx, body.bottom - 3), 2)
        stride = 0
        if animation == "walk":
            stride = round(math.sin(animation_time * 17) * 4)
        elif animation in ("jump", "fall"):
            stride = -2 if animation == "jump" else 3
        pygame.draw.line(target, shadow, (x + 13, y + 44), (x + 12 + stride, y + 50), 4)
        pygame.draw.line(target, shadow, (x + 24, y + 44), (x + 24 - stride, y + 50), 4)
        pygame.draw.line(target, hood, (body.right - 1, body.top + 13),
                         (body.right + 4, body.top + 19), 3)
        surface.blit(target, (rect.x - 3, rect.y - 3))

    def draw_world(self, surface: pygame.Surface) -> None:
        self.background(surface)
        cam = int(self.camera_x)
        for x, y, width, height in self.platforms:
            rect = pygame.Rect(x - cam, y, width, height)
            pygame.draw.rect(surface, (25, 43, 61), rect)
            pygame.draw.line(surface, (94, 133, 153), rect.topleft, (rect.right, rect.top), 4)
            for tile_x in range(rect.left + 12, rect.right, 42):
                pygame.draw.line(surface, (35, 59, 78), (tile_x, y + 8),
                                 (tile_x - 15, rect.bottom - 3), 1)
        for group_name, group in self.platform_groups.items():
            for platform in group:
                rect = platform.move(-cam, 0)
                if self.platform_group_active[group_name]:
                    pygame.draw.rect(surface, (32, 91, 100), rect, border_radius=3)
                    pygame.draw.line(surface, COLORS["cyan"], rect.topleft, (rect.right, rect.top), 3)
                else:
                    guide = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(guide, (75, 176, 185, 45), guide.get_rect(), border_radius=3)
                    pygame.draw.rect(guide, (90, 194, 200, 130), guide.get_rect(), 1, border_radius=3)
                    surface.blit(guide, rect.topleft)
                    for marker_x in range(rect.left + 8, rect.right, 24):
                        pygame.draw.circle(surface, (117, 193, 196), (marker_x, rect.top + rect.height // 2), 2)
        for platform in self.moving:
            rect = platform.rect.move(-cam, 0)
            pygame.draw.rect(surface, (40, 81, 103), rect, border_radius=4)
            pygame.draw.line(surface, COLORS["cyan"], (rect.left + 8, rect.top), (rect.right - 8, rect.top), 3)
            pygame.draw.circle(surface, (115, 218, 221), (rect.centerx, rect.centery), 4)
            for anchor in (platform.start, platform.end):
                pygame.draw.circle(surface, (44, 79, 94), (anchor[0] - cam, anchor[1] - 16), 5, 1)
        for hazard in self.hazards:
            rect = hazard.move(-cam, 0)
            pygame.draw.rect(surface, (48, 20, 43), rect)
            for spike_x in range(rect.left, rect.right, 22):
                pygame.draw.polygon(surface, COLORS["coral"],
                                    [(spike_x, rect.top + 6), (spike_x + 11, rect.top - 12),
                                     (spike_x + 22, rect.top + 6)])
            pygame.draw.line(surface, (255, 148, 145), rect.topleft, (rect.right, rect.top), 2)
        for checkpoint_index, (checkpoint_x, checkpoint_y) in enumerate(self.checkpoints):
            color = COLORS["gold"] if checkpoint_index <= self.active_checkpoint else (94, 117, 132)
            flag_x = checkpoint_x - cam
            pygame.draw.line(surface, color, (flag_x, checkpoint_y - 25), (flag_x, checkpoint_y + 30), 2)
            pygame.draw.polygon(surface, color, [(flag_x, checkpoint_y - 24),
                                                  (flag_x + 23, checkpoint_y - 17),
                                                  (flag_x, checkpoint_y - 9)])
        for mechanism in self.mechanisms:
            r = mechanism.rect.move(-cam, 0)
            glow = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*COLORS["cyan"], 27 if not mechanism.active else 65), (35, 35), 33)
            surface.blit(glow, (r.centerx - 35, r.centery - 35))
            base = (36, 124, 132) if mechanism.active else (48, 73, 92)
            pygame.draw.rect(surface, base, r, border_radius=5)
            pygame.draw.rect(surface, COLORS["cyan"] if mechanism.active else (118, 164, 179), r, 2, border_radius=5)
            pygame.draw.circle(surface, COLORS["gold"] if mechanism.active else COLORS["cyan"], r.center, 7)
            if mechanism.shadow_only:
                pygame.draw.circle(surface, COLORS["violet"], (r.centerx, r.top - 9), 4)
            self._draw_text(surface, mechanism.label, FONTS["tiny"], COLORS["muted"], (r.centerx, r.top - 23), True)
        for name, door in self.doors.items():
            r = door.move(-cam, 0)
            if self.door_open[name]:
                pygame.draw.rect(surface, (57, 183, 158), (r.left, r.bottom - 7, r.width, 7), border_radius=3)
                pygame.draw.line(surface, (81, 216, 186), (r.centerx, r.top + 9), (r.centerx, r.bottom - 14), 2)
            else:
                pygame.draw.rect(surface, (58, 73, 92), r, border_radius=4)
                pygame.draw.rect(surface, (240, 182, 100), r, 3, border_radius=4)
                for stripe_y in range(r.top + 12, r.bottom, 23):
                    pygame.draw.line(surface, (99, 120, 136), (r.left + 6, stripe_y), (r.right - 6, stripe_y), 2)
                pygame.draw.circle(surface, COLORS["gold"], (r.centerx, r.centery), 4)
        exit_rect = pygame.Rect(*self.level["exit"], 42, 90).move(-cam, 0)
        pygame.draw.ellipse(surface, (46, 173, 156), (exit_rect.left - 15, exit_rect.top - 7, 72, 108), 2)
        pygame.draw.rect(surface, (20, 94, 99), exit_rect, border_radius=18)
        pygame.draw.rect(surface, COLORS["cyan"], exit_rect, 2, border_radius=18)
        pygame.draw.circle(surface, (217, 255, 233), exit_rect.center, 5)

        echo_rect = self.echo_rect.move(-cam, 0)
        ready = self.sim_time >= SHADOW_DELAY
        self.draw_player(surface, echo_rect, True, self.echo, 175 if ready else 65)
        player_rect = self.actor.move(-cam, 0)
        self.draw_player(surface, player_rect)
        for particle in self.particles:
            alpha = int(255 * particle.life / particle.max_life)
            pygame.draw.circle(surface, particle.color, (round(particle.x - cam), round(particle.y)), particle.radius)
            if alpha < 140:
                pygame.draw.circle(surface, (20, 38, 54), (round(particle.x - cam), round(particle.y)), particle.radius + 2, 1)

    def draw_hud(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (7, 13, 25), (0, 0, WIDTH, 77))
        pygame.draw.line(surface, (48, 79, 99), (0, 76), (WIDTH, 76), 1)
        self._draw_text(surface, f"{self.level_index + 1:02d} / 03", FONTS["small"], COLORS["cyan"], (28, 14))
        self._draw_text(surface, self.level["title"], FONTS["body"], COLORS["white"], (112, 11))
        self._draw_text(surface, self.level["objective"], FONTS["tiny"], COLORS["muted"], (113, 43))
        self._draw_text(surface, self.level["subtitle"], FONTS["tiny"], (114, 139, 158), (113, 59))
        bar = pygame.Rect(WIDTH - 264, 25, 220, 9)
        pygame.draw.rect(surface, (36, 53, 70), bar, border_radius=5)
        ratio = min(1.0, self.sim_time / SHADOW_DELAY)
        if ratio:
            pygame.draw.rect(surface, COLORS["violet"], (bar.x, bar.y, round(bar.width * ratio), bar.height), border_radius=5)
        self._draw_text(surface, "ECO 3.0s" if ratio >= 1 else "ECO SINCRONIZANDO", FONTS["tiny"],
                        COLORS["violet"] if ratio >= 1 else COLORS["muted"], (bar.centerx, bar.y - 12), True)
        self._draw_text(surface, "A/D o flechas: mover     ESPACIO: saltar     R: reiniciar     ESC: pausa",
                        FONTS["tiny"], (162, 185, 199), (WIDTH // 2, HEIGHT - 17), True)
        if self.toast_timer > 0:
            label = "UMBRAL ABIERTO" if any(self.door_open.values()) else "MECANISMO ACTIVADO"
            toast = pygame.Surface((260, 38), pygame.SRCALPHA)
            toast.fill((17, 46, 56, 218))
            surface.blit(toast, (WIDTH - 282, 93))
            self._draw_text(surface, label, FONTS["tiny"], COLORS["cyan"], (WIDTH - 152, 112), True)

    def button(self, surface: pygame.Surface, label: str, center: tuple[int, int], width: int = 290) -> pygame.Rect:
        rect = pygame.Rect(0, 0, width, 52)
        rect.center = center
        mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse)
        color = (32, 79, 89) if hovered else (19, 37, 54)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, COLORS["cyan"] if hovered else (62, 91, 111), rect, 1, border_radius=4)
        self._draw_text(surface, label, FONTS["body"], COLORS["white"] if hovered else COLORS["muted"], rect.center, True)
        return rect

    def overlay(self, surface: pygame.Surface) -> None:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 10, 20, 205))
        surface.blit(shade, (0, 0))
        heading = "PAUSA" if self.state == "PAUSED" else "NIVEL COMPLETADO" if self.state == "LEVEL_COMPLETE" else "SHADOW"
        self._draw_text(surface, heading, FONTS["heading"], COLORS["white"], (WIDTH // 2, 196), True)
        labels = ["CONTINUAR", "REINTENTAR", "MENU PRINCIPAL"] if self.state == "PAUSED" else ["CONTINUAR", "REINTENTAR", "MENU PRINCIPAL"]
        self.buttons = [("overlay", self.button(surface, label, (WIDTH // 2, 302 + i * 69)), str(i))
                        for i, label in enumerate(labels)]

    def draw_menu(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["ink"])
        for y in range(0, HEIGHT, 3):
            value = 10 + int(17 * y / HEIGHT)
            pygame.draw.line(surface, (value, value + 12, value + 26), (0, y), (WIDTH, y))
        for i in range(9):
            x = (i * 177 + 30) % WIDTH
            pygame.draw.line(surface, (21, 44, 63), (x, 0), (x - 90, HEIGHT), 1)
        self._draw_text(surface, "SHADOW", FONTS["title"], COLORS["white"], (WIDTH // 2, 170), True)
        pygame.draw.line(surface, COLORS["cyan"], (WIDTH // 2 - 80, 220), (WIDTH // 2 + 80, 220), 2)
        subtitle = "¿DONDE ESTARA TU SOMBRA DENTRO DE 3 SEGUNDOS?"
        self._draw_text(surface, subtitle, FONTS["small"], COLORS["muted"], (WIDTH // 2, 251), True)
        self.buttons = []
        if self.state == "MAIN_MENU":
            labels = ["JUGAR", "SELECCIONAR NIVEL", "CONTROLES", "SALIR"]
            for i, label in enumerate(labels):
                self.buttons.append(("main", self.button(surface, label, (WIDTH // 2, 342 + i * 65)), str(i)))
        elif self.state == "LEVEL_SELECT":
            for i, level in enumerate(LEVELS):
                rect = self.button(surface, f"0{i + 1}    {level['title']}", (WIDTH // 2, 335 + i * 72), 370)
                self.buttons.append(("level", rect, str(i)))
            self.buttons.append(("back", self.button(surface, "VOLVER", (WIDTH // 2, 572), 220), ""))
        else:
            self._draw_text(surface, "A / D o flechas    Mover", FONTS["body"], COLORS["white"], (WIDTH // 2 - 170, 332))
            self._draw_text(surface, "ESPACIO / W / ARRIBA    Saltar", FONTS["body"], COLORS["white"], (WIDTH // 2 - 170, 379))
            self._draw_text(surface, "R    Reiniciar nivel", FONTS["body"], COLORS["white"], (WIDTH // 2 - 170, 426))
            self._draw_text(surface, "ESC    Pausar", FONTS["body"], COLORS["white"], (WIDTH // 2 - 170, 473))
            self.buttons.append(("back", self.button(surface, "VOLVER", (WIDTH // 2, 570), 220), ""))

    def draw(self) -> None:
        if self.state in ("MAIN_MENU", "LEVEL_SELECT", "CONTROLS"):
            self.draw_menu(WORLD)
        else:
            self.draw_world(WORLD)
            self.draw_hud(WORLD)
            if self.state in ("PAUSED", "LEVEL_COMPLETE", "GAME_COMPLETE"):
                if self.state == "GAME_COMPLETE":
                    WORLD.fill((5, 10, 20))
                    self._draw_text(WORLD, "SHADOW", FONTS["title"], COLORS["white"], (WIDTH // 2, 205), True)
                    self._draw_text(WORLD, "DEMO COMPLETADA", FONTS["heading"], COLORS["cyan"], (WIDTH // 2, 285), True)
                    self._draw_text(WORLD, "El presente y su eco han encontrado el mismo camino.", FONTS["small"], COLORS["muted"], (WIDTH // 2, 330), True)
                    self.buttons = [("complete", self.button(WORLD, "VOLVER AL MENU", (WIDTH // 2, 424), 300), "")]
                else:
                    self.overlay(WORLD)
                    if self.state == "LEVEL_COMPLETE":
                        self._draw_text(WORLD, "El eco abrio un camino hacia el siguiente umbral.", FONTS["small"], COLORS["muted"], (WIDTH // 2, 247), True)
        window = pygame.display.get_surface()
        window.fill(COLORS["ink"])
        viewport = min(window.get_width() / WIDTH, window.get_height() / HEIGHT)
        size = (round(WIDTH * viewport), round(HEIGHT * viewport))
        scaled = pygame.transform.smoothscale(WORLD, size)
        window.blit(scaled, ((window.get_width() - size[0]) // 2, (window.get_height() - size[1]) // 2))
        pygame.display.flip()

    def handle_click(self, position: tuple[int, int]) -> None:
        window = pygame.display.get_surface()
        scale = min(window.get_width() / WIDTH, window.get_height() / HEIGHT)
        offset_x = (window.get_width() - WIDTH * scale) / 2
        offset_y = (window.get_height() - HEIGHT * scale) / 2
        point = ((position[0] - offset_x) / scale, (position[1] - offset_y) / scale)
        for kind, rect, value in self.buttons:
            if not rect.collidepoint(point):
                continue
            play_sound("ui")
            if kind == "main":
                if value == "0":
                    self.start_level(0)
                elif value == "1":
                    self.state = "LEVEL_SELECT"
                elif value == "2":
                    self.state = "CONTROLS"
                else:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif kind == "level":
                self.start_level(int(value))
            elif kind == "back":
                self.state = "MAIN_MENU"
            elif kind == "overlay":
                if value == "0":
                    if self.state == "PAUSED":
                        self.state = "PLAYING"
                    else:
                        self.start_level(self.level_index + 1)
                elif value == "1":
                    self.reset_level()
                else:
                    self.state = "MAIN_MENU"
            elif kind == "complete":
                self.state = "MAIN_MENU"
            return

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.VIDEORESIZE:
            pygame.display.set_mode((max(640, event.w), max(360, event.h)), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "PLAYING":
                    self.state = "PAUSED"
                elif self.state == "PAUSED":
                    self.state = "PLAYING"
                elif self.state in ("CONTROLS", "LEVEL_SELECT"):
                    self.state = "MAIN_MENU"
            elif self.state == "PLAYING" and event.key == pygame.K_r:
                self.reset_level()
            elif self.state == "PLAYING" and event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.jump_requested = True
            elif self.state in ("MAIN_MENU", "LEVEL_SELECT", "CONTROLS") and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.state == "MAIN_MENU":
                    self.start_level(0)
                elif self.state == "LEVEL_SELECT":
                    self.start_level(0)
                else:
                    self.state = "MAIN_MENU"
        return True

    def run(self) -> None:
        self._last_animation = "idle"
        self.jump_requested = False
        running = True
        while running:
            dt = CLOCK.tick(FPS) / 1000.0
            self.jump_requested = False
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.update(dt, self.jump_requested)
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()