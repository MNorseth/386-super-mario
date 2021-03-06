import math
import random
import pygame
from ..level_entity import LevelEntity
from entities import Entity
from util import world_to_screen
import entities.characters.behaviors.damage_mario as b
import config
from util import make_vector

import constants


class _FireBarLink(Entity):
    def __init__(self, animation, level, owner):
        super().__init__(animation.get_rect())

        self.level = level
        self.owner = owner
        self.animation = animation

        # offsets and hitbox size assuming UNSCALED values, but the graphics have already
        # been scalled.
        hitbox_size = animation.width / config.rescale_factor, animation.height / config.rescale_factor

        self.harm = b.DamageMario(level, self, (0, 0), hitbox_size, self.on_mario_invincible)

    def update(self, dt, view_rect):
        # note: no animation update: we're borrowing FireBar's so all chain links are synchronized
        self.harm.update(dt)

    def draw(self, screen, view_rect):
        screen.blit(self.animation.image, world_to_screen(self.position, view_rect))
        self.harm.draw(screen, view_rect)

    def destroy(self):
        if self.level.entity_manager.is_registered(self):
            self.level.entity_manager.unregister(self)

    def on_mario_invincible(self, collision):
        # self-destruct if starman hits this link
        if self.level.mario.is_starman:
            self.destroy()
            self.level.asset_manager.sounds['stomp'].play()

    @property
    def layer(self):
        return constants.Active


class FireBar(LevelEntity):
    NUM_LINKS = 6  # in addition to central one
    RADIANS_PER_SECOND = math.pi * 2 / 3.0

    def __init__(self, level):
        self.fireball = level.asset_manager.interactive_atlas.load_animation("fireball")

        super().__init__(self.fireball.get_rect())

        self.level = level

        self.angle = random.uniform(0., math.pi * 2.)
        self.direction = random.choice([-1., 1.])

        self.distance_per_link = (8 * config.rescale_factor)
        self.fb_dimensions = (self.distance_per_link, self.distance_per_link)

        self.preview = self._create_editor_sprite()
        self.fireballs = []

        self.update_child_positions(0.)  # set initial positions of fireballs

        # state
        self._spawned_fireballs = False

    def update(self, dt, view_rect):
        self.fireball.update(dt)

        if not self._spawned_fireballs:
            self.fireballs = self._create_fireballs()
            self._spawned_fireballs = True

        self.update_child_positions(dt)

    def update_child_positions(self, dt):
        self.angle += FireBar.RADIANS_PER_SECOND * dt * self.direction

        while self.angle < 0.:
            self.angle += math.pi * 2.
        while self.angle >= math.pi * 2.:
            self.angle -= math.pi * 2.

        vx, vy = math.cos(self.angle), math.sin(self.angle)

        # calc center position from spawner top-left position
        px, py = self.position[0] + self.fb_dimensions[0] // 2, self.position[1] + self.fb_dimensions[1] // 2

        for c, child in enumerate(self.fireballs):
            dist = self.distance_per_link * c
            child.position = make_vector(
                px + vx * dist - self.fb_dimensions[0] // 2,
                py + vy * dist - self.fb_dimensions[1] // 2)

    def draw(self, screen, view_rect):
        draw_pos = self.position

        screen.blit(self.preview, world_to_screen(draw_pos, view_rect))

    def _create_fireballs(self):
        fireballs = []

        for i in range(FireBar.NUM_LINKS):
            fb = _FireBarLink(self.fireball, self.level, self)
            self.level.entity_manager.register(fb)
            fireballs.append(fb)

        return fireballs

    def destroy(self):
        super().destroy()
        self.level.entity_manager.unregister(self)

        for ch in self.fireballs:
            if self.level.entity_manager.is_registered(ch):
                self.level.entity_manager.unregister(ch)

    def _create_editor_sprite(self):
        prototype = self.level.asset_manager.interactive_atlas.load_animation("fireball").image

        surf = pygame.Surface((prototype.get_width() * FireBar.NUM_LINKS, prototype.get_height()))

        for x in range(0, surf.get_width(), int(self.distance_per_link)):
            surf.blit(prototype, (x, 0))

        return surf.convert()

    def create_preview(self):
        return self.preview

    @property
    def layer(self):
        return constants.Spawner


LevelEntity.create_generic_factory(FireBar)
