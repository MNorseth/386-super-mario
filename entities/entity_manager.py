from abc import ABC, abstractmethod
from .entity import Entity, Layer
from .characters import LevelEntity
from pygame.sprite import Rect
from enum import IntFlag
from util import copy_vector
from util import make_vector


class EntityManager:
    def __init__(self, layer_ordering: list):
        assert layer_ordering is not None and len(layer_ordering) > 0

        self.ordering = layer_ordering
        self.layers = dict(zip(layer_ordering, [list() for _ in range(len(layer_ordering))]))

        # include any missing layers
        have = set(layer_ordering)
        exist = set([x for x in Layer])

        for missing_layer in exist.difference(have):
            self.layers[missing_layer] = list()

    @staticmethod
    def create_default():
        # create a default entity manager. This is standard gameplay
        ordering = [Layer.Background, Layer.Block,
                    Layer.Enemy, Layer.Mario, Layer.Active, Layer.Interface, Layer.Overlay]

        return EntityManager(ordering)

    @staticmethod
    def create_editor():
        # create entity manager for editor. This has its own manager because the editor has layers that
        # won't typically be drawn during play, but are relevant while editing (spawners, triggers)
        ordering = [Layer.Background, Layer.Block, Layer.Spawner, Layer.Trigger,
                    Layer.Enemy, Layer.Mario, Layer.Active, Layer.Interface, Layer.Overlay]

        return EntityManager(ordering)

    def register(self, *args):
        try:
            iterator = iter(*args)

            for item in iterator:
                self._register_internal(item)

        except TypeError:
            for item in args:
                if isinstance(item, Entity):
                    self._register_internal(*args)
                else:
                    self.register(item)

    def _register_internal(self, entity):
        assert entity.layer in self.layers.keys()
        self.layers[entity.layer].append(entity)

    def unregister(self, entity):
        assert isinstance(entity, Entity)
        assert entity.layer in self.layers.keys()
        assert entity in self.layers[entity.layer]

        self.layers[entity.layer].remove(entity)

    def update(self, dt, view_rect):
        # todo: update only screen and a quarter
        def update_entity(entity, vr):
            entity.update(dt, vr)

        self._do_on_each_layer(update_entity, view_rect)

    def draw(self, screen, view_rect):
        # todo: draw only screen and a quarter
        def draw_entity(entity, vr):
            entity.draw(screen, vr)

        self._do_on_each_layer(draw_entity, view_rect)

    def _do_on_each_layer(self, fn, view_rect):
        for layer in self.ordering:
            entities = list(self.layers[layer])

            for entity in entities:
                if hasattr(entity, "enabled"):
                    if entity.enabled:
                        fn(entity, view_rect)

                else:
                    fn(entity, view_rect)

    def serialize(self):
        values = {"__class__": self.__class__.__name__}

        for layer in self.ordering:
            values[layer.name] = self._serialize_layer(layer)

        return values

    def _serialize_layer(self, layer):
        entity_values = []

        for entity in self.layers[layer]:
            if hasattr(entity, "serialize"):
                entity_values.append(entity.serialize())

        return entity_values

    def deserialize(self, level, values):
        assert values["__class__"] == self.__class__.__name__

        # clear any existing values and load new ones from disk
        for layer in self.layers:
            entity_list = self.layers[layer]

            for existing_entity in entity_list:
                if hasattr(existing_entity, "destroy"):
                    existing_entity.destroy()

            entity_list.clear()

            # find entries for this layer
            if layer.name not in values.keys():
                continue

            for entity_values in values[layer.name]:
                # create these entities
                entity = LevelEntity.build(level, entity_values)

                if entity is not None:
                    self.register(entity)

    def search_by_type(self, cls):
        found = []

        for layer in self.layers:
            for entity in self.layers[layer]:
                if isinstance(entity, cls):
                    found.append(entity)

        return found

    def get_entities_inside_region(self, rect: Rect):
        # return any entity, regardless of layer, that is intersecting with the given rect
        found = set()

        for layer in self.layers:
            for entity in self.layers[layer]:
                if rect.collidepoint(*entity.position) or rect.colliderect(entity.rect):
                    found.add(entity)

        return list(found)
