"""Utility modules for HardInfo.
"""

from hardinfo.utils.activation import WindowsActivationThread
from hardinfo.utils.drivers import DriverDownloadThread
from hardinfo.utils.helpers import clean_system_string
from hardinfo.utils.logging import QtLogSignaller, QtLoggingHandler, setup_logging
from hardinfo.utils.privileges import is_admin, require_admin
from hardinfo.utils.registry import SafeRegistryBackup, apply_tweak, revert_tweak

__all__ = [
    "clean_system_string",
    "QtLogSignaller",
    "QtLoggingHandler",
    "setup_logging",
    "is_admin",
    "require_admin",
    "SafeRegistryBackup",
    "apply_tweak",
    "revert_tweak",
    "WindowsActivationThread",
    "DriverDownloadThread",
]
