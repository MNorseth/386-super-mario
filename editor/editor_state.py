import copy
from state.game_state import GameState, state_stack
from state.run_level import RunLevel
from editor.dialogs import TilePickerDialog, ModeDialog, LevelConfigDialog, EntityPickerDialog, EntityToolDialog
from entities import EntityManager
from assets.asset_manager import AssetManager
from util import make_vector, bind_callback_parameters
from assets import Level
from event import EventHandler
from .place_mode import PlaceMode
from .passable_mode import PassableMode
from .config_mode import ConfigMode
from .entity_mode import EntityMode
from state.performance_measurement import PerformanceMeasurement
from assets.gui_helper import *
from assets.statistics import Statistics
from scoring import Labels
import constants


class _ModeDrawHelper(Element):
    """Exists only as a way to get a callback just before the first UI elements are drawn"""
    def __init__(self, draw_callback):
        super().__init__(make_vector(0, 0), None, Anchor.TOP_LEFT)

        self.draw_callback = draw_callback

    def draw(self, screen, view_rect):
        self.draw_callback(screen)


class EditorState(GameState, EventHandler):
    def __init__(self, assets):
        super().__init__()

        self.assets = assets  # type: AssetManager
        self.entity_manager = EntityManager([constants.Interface], [constants.Interface])  # own manager for interface

        # create a level to edit
        self.level = Level(assets, EntityManager.create_editor(), Statistics(Labels()))

        # shim to create a callback before UI draws
        self.entity_manager.register(_ModeDrawHelper(self.on_pre_ui_draw))

        # frame to contain all other windows
        self.frame = Frame(make_vector(0, 0), config.screen_rect.size)
        self.entity_manager.register(self.frame)

        # scrollbars to move map
        self.scroll_map_horizontal = create_slider(self.assets.gui_atlas,
                                                   make_vector(*config.screen_rect.bottomleft) + make_vector(10, -20),
                                                   config.screen_rect.width - 20, 0,
                                                   self.level.tile_map.width * self.level.tile_map.tileset.tile_width,
                                                   on_value_changed=bind_callback_parameters(self.on_horizontal_scroll),
                                                   thumb=self.assets.gui_atlas.load_static("sb_thumb"),
                                                   thumb_mo=self.assets.gui_atlas.load_static("sb_thumb_light"),
                                                   sb_type=ScrollbarType.HORIZONTAL)

        self.scroll_map_vertical = create_slider(self.assets.gui_atlas,
                                                 make_vector(*config.screen_rect.topright) + make_vector(-20, 10),
                                                 config.screen_rect.height - 40, 0,
                                                 self.level.tile_map.height * self.level.tile_map.tileset.tile_height,
                                                 on_value_changed=bind_callback_parameters(self.on_vertical_scroll),
                                                 thumb=self.assets.gui_atlas.load_static("sb_thumb"),
                                                 thumb_mo=self.assets.gui_atlas.load_static("sb_thumb_light"),
                                                 sb_type=ScrollbarType.VERTICAL)

        self.frame.add_child(self.scroll_map_horizontal)
        self.frame.add_child(self.scroll_map_vertical)

        # ... the various dialogs used by editor
        self.entity_tool_dialog = EntityToolDialog(self.assets.gui_atlas)
        self.frame.add_child(self.entity_tool_dialog)

        self.tile_dialog = TilePickerDialog(self.assets)
        self.frame.add_child(self.tile_dialog)

        self.config_dialog = LevelConfigDialog(self.level, self.assets.gui_atlas)
        self.frame.add_child(self.config_dialog)

        self.entity_dialog = EntityPickerDialog(self.level)
        self.frame.add_child(self.entity_dialog)

        self.entity_tools = EntityToolDialog
        # editor states to handle relevant actions
        self.current_mode = None

        self.place_mode = PlaceMode(self.tile_dialog, self.level)
        self.passable_mode = PassableMode(self.level)
        self.config_mode = ConfigMode()
        self.entity_mode = EntityMode(self.entity_dialog, self.entity_tool_dialog, self.level)

        self.set_mode(self.place_mode)

        self.mode_dialog = ModeDialog(self.assets.gui_atlas,
                                      on_tile_mode_callback=bind_callback_parameters(self.set_mode, self.place_mode),
                                      on_passable_mode_callback=bind_callback_parameters(
                                          self.set_mode, self.passable_mode),
                                      on_config_mode_callback=bind_callback_parameters(self.set_mode, self.config_mode),
                                      on_entity_mode_callback=bind_callback_parameters(self.set_mode, self.entity_mode))

        self.frame.add_child(self.mode_dialog)

        self._finished = False

    def draw(self, screen):
        screen.fill(self.level.background_color)
        self.level.draw(screen)
        self.entity_manager.draw(screen, self.level.view_rect, False)

    def set_mode(self, new_mode):
        if new_mode is self.place_mode:
            # turn on/off relevant dialogs
            self.tile_dialog.enabled = True
            self.entity_tool_dialog.enabled = False
            self.config_dialog.enabled = False
            self.entity_dialog.enabled = False
        elif new_mode is self.passable_mode:
            self.tile_dialog.enabled = False
            self.entity_tool_dialog.enabled = False
            self.config_dialog.enabled = False
            self.entity_dialog.enabled = False
        elif new_mode is self.config_mode:
            self.tile_dialog.enabled = False
            self.entity_tool_dialog.enabled = False
            self.config_dialog.enabled = True
            self.entity_dialog.enabled = False
        elif new_mode is self.entity_mode:
            self.tile_dialog.enabled = False
            self.entity_tool_dialog.enabled = True
            self.config_dialog.enabled = False
            self.entity_dialog.enabled = True
        else:
            raise NotImplementedError  # unknown mode

        self.current_mode = new_mode

    def update(self, dt):
        self.entity_manager.update(dt, self.level.view_rect, False)

    @property
    def finished(self):
        return self._finished

    def on_pre_ui_draw(self, screen):
        self.current_mode.draw(screen)

    def activated(self):
        self.game_events.register(self)

    def deactivated(self):
        self.game_events.unregister(self)

    def handle_event(self, evt, game_events):
        if evt.type == pygame.QUIT or (evt.type == pygame.KEYDOWN and evt.key == pygame.K_ESCAPE):
            self.consume(evt)
            self._finished = True
            return

        self.frame.handle_event(evt, game_events)

        # if absolutely nothing handled the event, the user has tried to do some kind of interaction
        # with the map itself
        if not self.is_consumed(evt):
            if evt.type == pygame.MOUSEBUTTONDOWN:
                self.consume(evt)
                self.current_mode.on_map_mousedown(evt, pygame.mouse.get_pos())
            elif evt.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                self.consume(evt)
                self.current_mode.on_map_motion(evt, pygame.mouse.get_pos())

            elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_t:
                # copy level state -> we don't want the actual movement and deaths of entities to be reflected
                # in our copy of the level

                # easiest way to handle this is to serialize our level, then load it rather than some
                # complicated deepcopy incomplementation
                stats = copy.copy(self.level.stats)

                test_level = Level(self.assets, EntityManager.create_default(), stats)
                test_level.deserialize(self.level.serialize())
                test_level.position = self.level.position

                state_stack.push(PerformanceMeasurement(state_stack, self.game_events,
                                                        RunLevel(self.game_events, self.assets, test_level, stats)))

        if evt.type == pygame.MOUSEBUTTONUP:
            self.current_mode.on_map_mouseup(evt, pygame.mouse.get_pos())
            # don't consume this event

    def on_horizontal_scroll(self, new_val):
        existing = self.level.position
        existing.x = new_val
        self.level.position = existing

        self.scroll_map_horizontal.max_value = self.level.tile_map.width * self.level.tile_map.tile_width

    def on_vertical_scroll(self, new_val):
        existing = self.level.position
        existing.y = new_val
        self.level.position = existing

        self.scroll_map_vertical.max_value = self.level.tile_map.height * self.level.tile_map.height
