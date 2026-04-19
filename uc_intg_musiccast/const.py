"""
Constants for Yamaha MusicCast integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

POLL_INTERVAL = 5
POLL_INTERVAL_STANDBY = 15
MAX_CONSECUTIVE_FAILURES = 5
RECONNECT_INTERVAL = 30
DEFAULT_PORT = 80

SOUND_MODE_MAPPING = {
    "munich": "Munich Hall",
    "vienna": "Vienna Hall",
    "amsterdam": "Amsterdam Concert Hall",
    "freiburg": "Freiburg Cathedral",
    "royaumont": "Royaumont Abbey",
    "chamber": "Chamber Music",
    "village_vanguard": "Village Vanguard Jazz Club",
    "warehouse_loft": "Warehouse Loft",
    "cellar_club": "Cellar Club",
    "roxy_theatre": "Roxy Theatre",
    "bottom_line": "Bottom Line",
    "sports": "Sports",
    "action_game": "Action Game",
    "roleplaying_game": "RPG Game",
    "music_video": "Music Video",
    "recital_opera": "Recital/Opera",
    "standard": "Standard",
    "spectacle": "Spectacle",
    "sci-fi": "Sci-Fi",
    "adventure": "Adventure",
    "drama": "Drama",
    "mono_movie": "Mono Movie",
    "enhanced": "Enhanced",
    "2ch_stereo": "2-Channel Stereo",
    "all_ch_stereo": "All Channel Stereo",
    "surr_decoder": "Surround Decoder",
    "straight": "Straight",
}

SOUND_MODE_REVERSE = {v: k for k, v in SOUND_MODE_MAPPING.items()}
