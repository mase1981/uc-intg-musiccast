"""
Yamaha MusicCast Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import ucapi
from ucapi.remote import Attributes, Features, Remote, States

from uc_intg_musiccast.client import YamahaMusicCastClient

_LOG = logging.getLogger(__name__)

class MusicCastRemote(Remote):
    """Remote entity for Yamaha MusicCast devices."""

    def __init__(self, device_id: str, device_name: str):
        """Initialize the remote entity."""
        features = [Features.SEND_CMD]
        attributes = {Attributes.STATE: States.ON}
        simple_commands, ui_pages = self._build_ui()

        super().__init__(
            identifier=f"{device_id}_remote",
            name=f"{device_name} Remote",
            features=features,
            attributes=attributes,
            simple_commands=simple_commands,
            ui_pages=ui_pages,
            cmd_handler=self._handle_command,
        )

        self._client: Optional[YamahaMusicCastClient] = None
        self._zone: str = "main"
        self._capabilities_initialized = False
        self._integration_api = None
        self._available_sources = []
        self._available_sound_programs = []
        self._has_tuner = False
        self._tuner_bands = []
        self._zone_capabilities = {}

    def set_client(self, client):
        """Set the MusicCast API client."""
        self._client = client

    async def initialize_capabilities(self):
        """Initialize remote capabilities from real device."""
        if self._capabilities_initialized:
            return
            
        _LOG.info("Initializing MusicCast remote capabilities")
        
        if self._client:
            try:
                # Get device capabilities
                available_inputs = await self._client.get_available_inputs(self._zone)
                self._available_sources = available_inputs
                
                sound_programs = await self._client.get_available_sound_programs(self._zone)
                self._available_sound_programs = sound_programs
                
                # Check for tuner
                self._has_tuner = await self._client.has_tuner()
                if self._has_tuner:
                    self._tuner_bands = await self._client.get_tuner_bands()
                    _LOG.info(f"Tuner detected with bands: {self._tuner_bands}")
                
                # Get zone capabilities
                self._zone_capabilities = await self._client.get_zone_capabilities(self._zone)
                
                # Rebuild UI with actual device capabilities
                simple_commands, ui_pages = self._build_enhanced_ui()
                
                # Update the entity options
                if hasattr(self, 'options') and self.options:
                    self.options["simple_commands"] = simple_commands
                    self.options["user_interface"] = {"pages": ui_pages}
                
                _LOG.info(f"Remote initialized with {len(self._available_sources)} sources, "
                         f"{len(sound_programs)} sound programs, tuner: {self._has_tuner}")
                
            except Exception as e:
                _LOG.error(f"Failed to initialize remote capabilities: {e}")
        
        self.attributes[Attributes.STATE] = States.ON
        self._force_integration_update()
        self._capabilities_initialized = True

    async def update_attributes(self):
        """Update remote attributes."""
        if not self._capabilities_initialized:
            await self.initialize_capabilities()
        self.attributes[Attributes.STATE] = States.ON
        self._force_integration_update()

    def _force_integration_update(self):
        """Force update to integration API."""
        if self._integration_api:
            try:
                self._integration_api.configured_entities.update_attributes(
                    self.id, self.attributes
                )
            except Exception as e:
                _LOG.debug("Could not update integration API: %s", e)

    def _build_ui(self) -> (List[str], List[Dict[str, Any]]):
        """Build basic UI for initial setup."""
        commands = [
            'play', 'pause', 'stop', 'next', 'previous', 'volume_up', 'volume_down',
            'mute_toggle', 'power_on', 'power_off', 'power_toggle', 'play_pause',
            'repeat_toggle', 'shuffle_toggle'
        ]

        pages = [
            {
                'page_id': 'main',
                'name': 'Main Controls',
                'grid': {'width': 4, 'height': 6},
                'items': [
                    {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'PREV', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'previous'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': 'PLAY/PAUSE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'play_pause'}}},
                    {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'NEXT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'next'}}},
                    {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'VOL-', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_down'}}},
                    {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'VOL+', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_up'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'MUTE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'mute_toggle'}}},
                    {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'STOP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'stop'}}},
                    {'type': 'text', 'location': {'x': 0, 'y': 2}, 'text': 'POWER', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'power_toggle'}}},
                    {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'REPEAT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'repeat_toggle'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 2}, 'text': 'SHUFFLE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'shuffle_toggle'}}},
                ]
            }
        ]
        return commands, pages

    def _build_enhanced_ui(self) -> (List[str], List[Dict[str, Any]]):
        """Build enhanced UI based on real device capabilities."""
        # Build comprehensive command list
        commands = [
            # Basic playback
            'play', 'pause', 'stop', 'next', 'previous', 'play_pause',
            # Power
            'power_on', 'power_off', 'power_toggle',
            # Volume
            'volume_up', 'volume_down', 'mute_toggle',
            # Repeat and shuffle with toggle support
            'repeat_off', 'repeat_one', 'repeat_all', 'repeat_toggle',
            'shuffle_off', 'shuffle_on', 'shuffle_toggle'
        ]

        # Add input commands for available sources
        for source in self._available_sources:
            commands.append(f"input_{source['id']}")

        # Add sound program commands
        for program in self._available_sound_programs:
            commands.append(f"sound_{program}")

        # Add NetUSB preset commands (1-40)
        for preset_num in range(1, 41):
            commands.append(f"preset_{preset_num}")
        
        # Add tuner preset commands if tuner available
        if self._has_tuner:
            for band in self._tuner_bands:
                for preset_num in range(1, 41):
                    commands.append(f"tuner_{band}_preset_{preset_num}")
            commands.extend(['tuner_preset_up', 'tuner_preset_down'])
        
        # Add scene commands (1-8)
        scene_num = self._zone_capabilities.get('scene_num', 8)
        for scene in range(1, scene_num + 1):
            commands.append(f"scene_{scene}")
        
        # Add audio enhancement commands
        func_list = self._zone_capabilities.get('func_list', [])
        if 'enhancer' in func_list:
            commands.extend(['enhancer_on', 'enhancer_off', 'enhancer_toggle'])
        if 'pure_direct' in func_list:
            commands.extend(['pure_direct_on', 'pure_direct_off', 'pure_direct_toggle'])
        if 'surround_ai' in func_list:
            commands.extend(['surround_ai_on', 'surround_ai_off', 'surround_ai_toggle'])
        if 'extra_bass' in func_list:
            commands.extend(['extra_bass_on', 'extra_bass_off', 'extra_bass_toggle'])
        if 'adaptive_drc' in func_list:
            commands.extend(['adaptive_drc_on', 'adaptive_drc_off', 'adaptive_drc_toggle'])
        if 'sleep' in func_list:
            commands.extend(['sleep_off', 'sleep_30', 'sleep_60', 'sleep_90', 'sleep_120'])
        
        # Add cursor/menu commands if available
        if 'cursor' in func_list:
            commands.extend(['cursor_up', 'cursor_down', 'cursor_left', 'cursor_right', 'cursor_select', 'cursor_return'])
        if 'menu' in func_list:
            commands.extend(['menu_on_screen', 'menu_top_menu', 'menu_menu', 'menu_option', 'menu_display', 'menu_home'])

        # Build enhanced UI pages
        pages = []

        # Main control page
        pages.append(self._build_main_page())

        # Sources page
        if self._available_sources:
            pages.append(self._build_sources_page())

        # Sound programs page
        if self._available_sound_programs:
            pages.append(self._build_sound_programs_page())

        # NetUSB favorites pages
        pages.extend(self._build_netusb_favorites_pages())
        
        # Tuner preset pages (if tuner available)
        if self._has_tuner:
            pages.extend(self._build_tuner_preset_pages())
        
        # Scene page
        if scene_num > 0:
            pages.append(self._build_scene_page(scene_num))
        
        # Audio enhancement page
        if any(f in func_list for f in ['enhancer', 'pure_direct', 'surround_ai', 'extra_bass', 'adaptive_drc', 'sleep']):
            pages.append(self._build_audio_enhancement_page(func_list))
        
        # Cursor/Menu page
        if 'cursor' in func_list or 'menu' in func_list:
            pages.append(self._build_cursor_menu_page(func_list))

        return commands, pages
    
    def _build_main_page(self) -> Dict[str, Any]:
        """Build main controls page."""
        return {
            'page_id': 'main',
            'name': 'Main Controls',
            'grid': {'width': 4, 'height': 6},
            'items': [
                {'type': 'text', 'location': {'x': 0, 'y': 0}, 'text': 'POWER', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'power_toggle'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'PREV', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'previous'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': 'PLAY/PAUSE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'play_pause'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'NEXT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'next'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'VOL-', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_down'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'VOL+', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_up'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'MUTE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'mute_toggle'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'STOP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'stop'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 2}, 'text': 'REPEAT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'repeat_toggle'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'SHUFFLE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'shuffle_toggle'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 2}, 'text': 'THUMBS+', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'thumbs_up'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 2}, 'text': 'THUMBS-', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'thumbs_down'}}},
            ]
        }
    
    def _build_sources_page(self) -> Dict[str, Any]:
        """Build sources page."""
        source_items = []
        x, y = 0, 0
        for i, source in enumerate(self._available_sources[:16]):  # Max 16 sources
            if x >= 4:
                x = 0
                y += 1
                if y >= 4:
                    break
            
            display_name = source['name'][:8] if len(source['name']) > 8 else source['name']
            
            source_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': display_name,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"input_{source['id']}"}}
            })
            x += 1

        return {
            'page_id': 'sources',
            'name': 'Sources',
            'grid': {'width': 4, 'height': 6},
            'items': source_items
        }
    
    def _build_sound_programs_page(self) -> Dict[str, Any]:
        """Build sound programs page."""
        sound_items = []
        x, y = 0, 0
        
        # Popular sound programs for main page
        popular_programs = ['2ch_stereo', 'all_ch_stereo', 'straight', 'standard', 
                          'munich', 'vienna', 'sports', 'music_video']
        
        available_popular = [p for p in popular_programs if p in self._available_sound_programs]
        other_programs = [p for p in self._available_sound_programs if p not in popular_programs]
        
        programs_to_show = (available_popular + other_programs)[:16]
        
        for program in programs_to_show:
            if x >= 4:
                x = 0
                y += 1
                if y >= 4:
                    break
            
            display_names = {
                '2ch_stereo': '2CH', 'all_ch_stereo': 'ALLCH', 'straight': 'STRAIGHT',
                'standard': 'STANDARD', 'munich': 'MUNICH', 'vienna': 'VIENNA',
                'sports': 'SPORTS', 'music_video': 'MUSIC', 'action_game': 'ACTION',
                'drama': 'DRAMA'
            }
            
            display_name = display_names.get(program, program[:6].upper())
            
            sound_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': display_name,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"sound_{program}"}}
            })
            x += 1

        return {
            'page_id': 'sound_programs',
            'name': 'Sound Programs',
            'grid': {'width': 4, 'height': 6},
            'items': sound_items
        }
    
    def _build_netusb_favorites_pages(self) -> List[Dict[str, Any]]:
        """Build NetUSB favorites pages (1-40)."""
        pages = []
        
        # Page 1: Favorites 1-16
        preset_items = []
        x, y = 0, 0
        for preset_num in range(1, 17):
            if x >= 4:
                x = 0
                y += 1
            preset_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': f"FAV{preset_num}",
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"preset_{preset_num}"}}
            })
            x += 1
        pages.append({
            'page_id': 'favorites',
            'name': 'Favorites 1-16',
            'grid': {'width': 4, 'height': 6},
            'items': preset_items
        })
        
        # Page 2: Favorites 17-32
        preset_items = []
        x, y = 0, 0
        for preset_num in range(17, 33):
            if x >= 4:
                x = 0
                y += 1
            preset_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': f"FAV{preset_num}",
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"preset_{preset_num}"}}
            })
            x += 1
        pages.append({
            'page_id': 'favorites2',
            'name': 'Favorites 17-32',
            'grid': {'width': 4, 'height': 6},
            'items': preset_items
        })
        
        # Page 3: Favorites 33-40
        preset_items = []
        x, y = 0, 0
        for preset_num in range(33, 41):
            if x >= 4:
                x = 0
                y += 1
            preset_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': f"FAV{preset_num}",
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"preset_{preset_num}"}}
            })
            x += 1
        pages.append({
            'page_id': 'favorites3',
            'name': 'Favorites 33-40',
            'grid': {'width': 4, 'height': 6},
            'items': preset_items
        })
        
        return pages
    
    def _build_tuner_preset_pages(self) -> List[Dict[str, Any]]:
        """Build tuner preset pages for each band."""
        pages = []
        
        for band in self._tuner_bands:
            band_upper = band.upper()
            
            # Page 1: Presets 1-16
            preset_items = []
            x, y = 0, 0
            for preset_num in range(1, 17):
                if x >= 4:
                    x = 0
                    y += 1
                preset_items.append({
                    'type': 'text',
                    'location': {'x': x, 'y': y},
                    'text': f"{band_upper}{preset_num}",
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f"tuner_{band}_preset_{preset_num}"}}
                })
                x += 1
            pages.append({
                'page_id': f'tuner_{band}_1',
                'name': f'{band_upper} Tuner 1-16',
                'grid': {'width': 4, 'height': 6},
                'items': preset_items
            })
            
            # Page 2: Presets 17-32
            preset_items = []
            x, y = 0, 0
            for preset_num in range(17, 33):
                if x >= 4:
                    x = 0
                    y += 1
                preset_items.append({
                    'type': 'text',
                    'location': {'x': x, 'y': y},
                    'text': f"{band_upper}{preset_num}",
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f"tuner_{band}_preset_{preset_num}"}}
                })
                x += 1
            pages.append({
                'page_id': f'tuner_{band}_2',
                'name': f'{band_upper} Tuner 17-32',
                'grid': {'width': 4, 'height': 6},
                'items': preset_items
            })
            
            # Page 3: Presets 33-40 + controls
            preset_items = []
            x, y = 0, 0
            for preset_num in range(33, 41):
                if x >= 4:
                    x = 0
                    y += 1
                preset_items.append({
                    'type': 'text',
                    'location': {'x': x, 'y': y},
                    'text': f"{band_upper}{preset_num}",
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f"tuner_{band}_preset_{preset_num}"}}
                })
                x += 1
            # Add preset up/down controls
            preset_items.extend([
                {'type': 'text', 'location': {'x': 0, 'y': 3}, 'text': 'PREV', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'tuner_preset_down'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 3}, 'text': 'NEXT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'tuner_preset_up'}}},
            ])
            pages.append({
                'page_id': f'tuner_{band}_3',
                'name': f'{band_upper} Tuner 33-40',
                'grid': {'width': 4, 'height': 6},
                'items': preset_items
            })
        
        return pages
    
    def _build_scene_page(self, scene_num: int) -> Dict[str, Any]:
        """Build scene page."""
        scene_items = []
        x, y = 0, 0
        
        for scene in range(1, min(scene_num + 1, 9)):  # Max 8 scenes
            if x >= 4:
                x = 0
                y += 1
            scene_items.append({
                'type': 'text',
                'location': {'x': x, 'y': y},
                'text': f"SCENE{scene}",
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f"scene_{scene}"}}
            })
            x += 1
        
        return {
            'page_id': 'scenes',
            'name': 'Scenes',
            'grid': {'width': 4, 'height': 6},
            'items': scene_items
        }
    
    def _build_audio_enhancement_page(self, func_list: List[str]) -> Dict[str, Any]:
        """Build audio enhancement page."""
        items = []
        x, y = 0, 0
        
        if 'enhancer' in func_list:
            items.append({'type': 'text', 'location': {'x': x, 'y': y}, 'text': 'ENHANCER', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'enhancer_toggle'}}})
            x += 1
        if 'pure_direct' in func_list:
            items.append({'type': 'text', 'location': {'x': x, 'y': y}, 'text': 'PURE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'pure_direct_toggle'}}})
            x += 1
        if 'surround_ai' in func_list:
            items.append({'type': 'text', 'location': {'x': x, 'y': y}, 'text': 'AI', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'surround_ai_toggle'}}})
            x += 1
        if 'extra_bass' in func_list:
            items.append({'type': 'text', 'location': {'x': x, 'y': y}, 'text': 'BASS', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'extra_bass_toggle'}}})
            x += 1
        
        if x > 0:
            x = 0
            y += 1
        
        if 'adaptive_drc' in func_list:
            items.append({'type': 'text', 'location': {'x': x, 'y': y}, 'text': 'DRC', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'adaptive_drc_toggle'}}})
            x += 1
        
        if 'sleep' in func_list:
            if x >= 4:
                x = 0
                y += 1
            items.extend([
                {'type': 'text', 'location': {'x': 0, 'y': y + 1}, 'text': 'SLEEP OFF', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'sleep_off'}}},
                {'type': 'text', 'location': {'x': 1, 'y': y + 1}, 'text': 'SLEEP 30', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'sleep_30'}}},
                {'type': 'text', 'location': {'x': 2, 'y': y + 1}, 'text': 'SLEEP 60', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'sleep_60'}}},
                {'type': 'text', 'location': {'x': 3, 'y': y + 1}, 'text': 'SLEEP 90', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'sleep_90'}}},
            ])
        
        return {
            'page_id': 'audio_enhancement',
            'name': 'Audio',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }
    
    def _build_cursor_menu_page(self, func_list: List[str]) -> Dict[str, Any]:
        """Build cursor and menu navigation page."""
        items = []
        
        if 'cursor' in func_list:
            items.extend([
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'UP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_up'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'LEFT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_left'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'SELECT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_select'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'RIGHT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_right'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'DOWN', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_down'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'RETURN', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'cursor_return'}}},
            ])
        
        if 'menu' in func_list:
            items.extend([
                {'type': 'text', 'location': {'x': 0, 'y': 3}, 'text': 'MENU', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'menu_menu'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 3}, 'text': 'TOP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'menu_top_menu'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 3}, 'text': 'OPTION', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'menu_option'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 3}, 'text': 'HOME', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'menu_home'}}},
            ])
        
        return {
            'page_id': 'cursor_menu',
            'name': 'Navigation',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    async def _handle_command(self, entity, cmd_id: str, params: dict = None) -> ucapi.StatusCodes:
        """Handle remote commands."""
        if not self._client:
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            command = params.get('command') if params else None
            if cmd_id == "send_cmd" and command:
                _LOG.info(f"Executing remote command: {command}")
                
                # Playback commands
                if command == 'play_pause':
                    await self._client.set_playback('play_pause')
                elif command == 'play':
                    await self._client.set_playback('play')
                elif command == 'pause':
                    await self._client.set_playback('pause')
                elif command == 'stop':
                    await self._client.set_playback('stop')
                elif command == 'next':
                    await self._client.set_playback('next')
                elif command == 'previous':
                    await self._client.set_playback('previous')
                
                # Power commands
                elif command == 'power_on':
                    await self._client.set_power(self._zone, 'on')
                elif command == 'power_off':
                    await self._client.set_power(self._zone, 'standby')
                elif command == 'power_toggle':
                    await self._client.set_power(self._zone, 'toggle')
                
                # Volume commands
                elif command == 'volume_up':
                    await self._client.set_volume(self._zone, direction="up", step=4)
                elif command == 'volume_down':
                    await self._client.set_volume(self._zone, direction="down", step=4)
                elif command == 'mute_toggle':
                    status = await self._client.get_status(self._zone)
                    if status.power == "standby":
                        await self._client.set_power(self._zone, 'on')
                        await asyncio.sleep(1)
                    current_mute = self._get_current_mute_state()
                    await self._client.set_mute(self._zone, enable=not current_mute)
                
                # Repeat/Shuffle commands
                elif command == 'repeat_off':
                    await self._client.set_repeat('off')
                elif command == 'repeat_one':
                    await self._client.set_repeat('one')
                elif command == 'repeat_all':
                    await self._client.set_repeat('all')
                elif command == 'repeat_toggle':
                    if hasattr(self._client, 'toggle_repeat'):
                        await self._client.toggle_repeat()
                    else:
                        current_repeat = self._get_current_repeat_state()
                        next_repeat = {'off': 'all', 'all': 'one', 'one': 'off'}.get(current_repeat, 'off')
                        await self._client.set_repeat(next_repeat)
                elif command == 'shuffle_off':
                    await self._client.set_shuffle('off')
                elif command == 'shuffle_on':
                    await self._client.set_shuffle('on')
                elif command == 'shuffle_toggle':
                    if hasattr(self._client, 'toggle_shuffle'):
                        await self._client.toggle_shuffle()
                    else:
                        current_shuffle = self._get_current_shuffle_state()
                        await self._client.set_shuffle('off' if current_shuffle else 'on')
                
                # Input commands
                elif command.startswith('input_'):
                    input_id = command[6:]
                    if any(src['id'] == input_id for src in self._available_sources):
                        await self._client.set_input(self._zone, input_id)
                    else:
                        _LOG.warning(f"Input not available: {input_id}")
                        return ucapi.StatusCodes.BAD_REQUEST
                
                # Sound program commands
                elif command.startswith('sound_'):
                    program_id = command[6:]
                    if program_id in self._available_sound_programs:
                        await self._client.set_sound_program(self._zone, program_id)
                    else:
                        _LOG.warning(f"Sound program not available: {program_id}")
                        return ucapi.StatusCodes.BAD_REQUEST
                
                # NetUSB preset commands
                elif command.startswith('preset_'):
                    preset_num_str = command[7:]
                    try:
                        preset_num = int(preset_num_str)
                        if 1 <= preset_num <= 40:
                            await self._client.recall_preset(self._zone, preset_num)
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                    except ValueError:
                        return ucapi.StatusCodes.BAD_REQUEST
                
                # Tuner preset commands
                elif command.startswith('tuner_') and '_preset_' in command:
                    parts = command.split('_')
                    if len(parts) >= 4:
                        band = parts[1]  # fm or dab
                        preset_num = int(parts[3])
                        if 1 <= preset_num <= 40:
                            await self._client.recall_tuner_preset(self._zone, band, preset_num)
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                elif command == 'tuner_preset_up':
                    await self._client.switch_tuner_preset('up')
                elif command == 'tuner_preset_down':
                    await self._client.switch_tuner_preset('down')
                
                # Scene commands
                elif command.startswith('scene_'):
                    scene_num = int(command[6:])
                    if 1 <= scene_num <= 8:
                        await self._client.set_scene(self._zone, scene_num)
                    else:
                        return ucapi.StatusCodes.BAD_REQUEST
                
                # Audio enhancement commands
                elif command == 'enhancer_on':
                    await self._client.set_enhancer(self._zone, True)
                elif command == 'enhancer_off':
                    await self._client.set_enhancer(self._zone, False)
                elif command == 'enhancer_toggle':
                    status = await self._client.get_status(self._zone)
                    await self._client.set_enhancer(self._zone, not status.enhancer)
                elif command == 'pure_direct_on':
                    await self._client.set_pure_direct(self._zone, True)
                elif command == 'pure_direct_off':
                    await self._client.set_pure_direct(self._zone, False)
                elif command == 'pure_direct_toggle':
                    status = await self._client.get_status(self._zone)
                    await self._client.set_pure_direct(self._zone, not status.pure_direct)
                elif command == 'surround_ai_on':
                    await self._client.set_surround_ai(self._zone, True)
                elif command == 'surround_ai_off':
                    await self._client.set_surround_ai(self._zone, False)
                elif command == 'surround_ai_toggle':
                    status = await self._client.get_status(self._zone)
                    await self._client.set_surround_ai(self._zone, not status.surround_ai)
                elif command == 'extra_bass_on':
                    await self._client.set_extra_bass(self._zone, True)
                elif command == 'extra_bass_off':
                    await self._client.set_extra_bass(self._zone, False)
                elif command == 'extra_bass_toggle':
                    status = await self._client.get_status(self._zone)
                    await self._client.set_extra_bass(self._zone, not status.extra_bass)
                elif command == 'adaptive_drc_on':
                    await self._client.set_adaptive_drc(self._zone, True)
                elif command == 'adaptive_drc_off':
                    await self._client.set_adaptive_drc(self._zone, False)
                elif command == 'adaptive_drc_toggle':
                    status = await self._client.get_status(self._zone)
                    await self._client.set_adaptive_drc(self._zone, not status.adaptive_drc)
                
                # Sleep timer commands
                elif command == 'sleep_off':
                    await self._client.set_sleep(self._zone, 0)
                elif command == 'sleep_30':
                    await self._client.set_sleep(self._zone, 30)
                elif command == 'sleep_60':
                    await self._client.set_sleep(self._zone, 60)
                elif command == 'sleep_90':
                    await self._client.set_sleep(self._zone, 90)
                elif command == 'sleep_120':
                    await self._client.set_sleep(self._zone, 120)
                
                # Cursor commands
                elif command == 'cursor_up':
                    await self._client.set_cursor(self._zone, 'up')
                elif command == 'cursor_down':
                    await self._client.set_cursor(self._zone, 'down')
                elif command == 'cursor_left':
                    await self._client.set_cursor(self._zone, 'left')
                elif command == 'cursor_right':
                    await self._client.set_cursor(self._zone, 'right')
                elif command == 'cursor_select':
                    await self._client.set_cursor(self._zone, 'select')
                elif command == 'cursor_return':
                    await self._client.set_cursor(self._zone, 'return')
                
                # Menu commands
                elif command == 'menu_on_screen':
                    await self._client.set_menu(self._zone, 'on_screen')
                elif command == 'menu_top_menu':
                    await self._client.set_menu(self._zone, 'top_menu')
                elif command == 'menu_menu':
                    await self._client.set_menu(self._zone, 'menu')
                elif command == 'menu_option':
                    await self._client.set_menu(self._zone, 'option')
                elif command == 'menu_display':
                    await self._client.set_menu(self._zone, 'display')
                elif command == 'menu_home':
                    await self._client.set_menu(self._zone, 'home')
                
                # Thumbs up/down commands
                elif command == 'thumbs_up':
                    await self._client.manage_play('thumbs_up')
                elif command == 'thumbs_down':
                    await self._client.manage_play('thumbs_down')
                
                # List navigation commands
                elif command == 'list_return':
                    await self._client.set_list_control('main', 'return', zone=self._zone)
                
                else:
                    _LOG.warning(f"Unhandled remote command: {command}")
                    return ucapi.StatusCodes.NOT_IMPLEMENTED
                
                asyncio.create_task(self._deferred_update())
                return ucapi.StatusCodes.OK
            else:
                return ucapi.StatusCodes.BAD_REQUEST

        except Exception as e:
            _LOG.error(f"Error executing command {params}: {e}")
            return ucapi.StatusCodes.SERVER_ERROR

    def _get_current_mute_state(self) -> bool:
        """Helper to safely get mute state from parent media player."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity:
                    return mp_entity.attributes.get('muted', False)
        except Exception as e:
            _LOG.debug(f"Could not get mute state: {e}")
        return False

    def _get_current_repeat_state(self) -> str:
        """Helper to get current repeat state."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity:
                    return mp_entity.attributes.get('repeat', 'off')
        except Exception as e:
            _LOG.debug(f"Could not get repeat state: {e}")
        return 'off'

    def _get_current_shuffle_state(self) -> bool:
        """Helper to get current shuffle state."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity:
                    return mp_entity.attributes.get('shuffle', False)
        except Exception as e:
            _LOG.debug(f"Could not get shuffle state: {e}")
        return False

    async def _deferred_update(self):
        """Force a state poll after a command."""
        await asyncio.sleep(0.5)
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity and hasattr(mp_entity, 'update_attributes'):
                    await mp_entity.update_attributes()
        except Exception as e:
            _LOG.error(f"Could not trigger deferred update for media player: {e}")