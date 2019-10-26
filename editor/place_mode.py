import pygame
import pygame.gfxdraw
from .editor_mode import EditorMode
from .grid_functions import draw_grid, draw_selection_square
from .dialogs.tile_picker_dialog import TilePickerDialog
from util import pixel_coords_to_tile_coords, tile_coords_to_pixel_coords
import config


class PlaceMode(EditorMode):
    """Editor is in tile-placement mode"""
    def __init__(self, tile_dialog, level_map):
        super().__init__()

        self.picker_dialog = tile_dialog  # type: TilePickerDialog
        self.level_map = level_map

    def on_map_click(self, evt, screen_mouse_pos):
        pass

    def on_map_mousedown(self, evt, screen_mouse_pos):
        tile_coords = pixel_coords_to_tile_coords(screen_mouse_pos, self.level_map.tileset)

        if self.level_map.is_in_bounds(tile_coords):
            self.level_map.set_tile(self.picker_dialog.selected_tile_idx)

    def draw(self, screen):
        # todo: check for option
        # for now, assume grid lines wanted

        draw_grid(screen, config.editor_grid_color,
                  (self.level_map.tileset.tile_width, self.level_map.tileset.tile_height))

        # also draw a square around current selected point, if within map bounds
        draw_selection_square(screen, self.level_map, config.editor_grid_overlay_color)