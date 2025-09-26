"""
Unfolded Circle Integration for Yamaha MusicCast.

This integration provides control of Yamaha MusicCast audio devices
through the Unfolded Circle Remote Two/Three system.

:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

try:
    from ._version import version as __version__
    from ._version import version_tuple
except ImportError:
    __version__ = "unknown version"
    version_tuple = (0, 0, "unknown version")

__all__ = ["__version__", "version_tuple"]