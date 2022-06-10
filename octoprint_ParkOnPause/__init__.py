# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from enum import Enum

import octoprint.plugin
import logging

class ParkOnPauseProfileModes(Enum):
    ALL = 0
    SELECT = 1

class ParkOnPauseParkLocations(Enum):
    CENTER = 0
    MIN_MIN = 1
    MIN_MAX = 2
    MAX_MIN = 3
    MAX_MAX = 4
    CUSTOM_ = 5

class ParkOnPauseParkSpeeds(Enum):
    AUTO = 0
    CUSTOM = 1

class ParkOnPausePlugin(octoprint.plugin.EventHandlerPlugin,
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.StartupPlugin):

    def __init__(self):
        self._logger = logging.getLogger(__name__)

        self.pausePosX = None
        self.pausePosY = None
        self.pausePosZ = None
        
        self._profileMode = ParkOnPauseProfileModes.ALL.name.lower()
        self._selectedProfiles = []
        self._enableParkOnPause = True
        self._homeBeforeUnpark = False
        self._parkLocation = ParkOnPauseParkLocations.CENTER.name.lower()
        self._parkSpeed = ParkOnPauseParkSpeeds.AUTO.name.lower()
        self._parkPosX = 0  # mm
        self._parkPosY = 0  # mm
        self._parkLiftZ = 5  # mm
        self._parkSpeedXY = 6000  # mm/m
        self._parkSpeedZ = 1200  # mm/m

    def initialize(self):
        self._profileMode = self._settings.get(["profileMode"])
        self._selectedProfiles = self._settings.get(["selectedProfiles"])
        self._enableParkOnPause = self._settings.get_boolean(["enableParkOnPause"])
        self._homeBeforeUnpark = self._settings.get_boolean(["homeBeforeUnpark"])
        self._parkLocation = self._settings.get(["parkLocation"])
        self._parkSpeed = self._settings.get(["parkSpeed"])
        self._parkPosX = self._settings.get(["parkPosX"])
        self._parkPosY = self._settings.get(["parkPosY"])
        self._parkLiftZ = self._settings.get(["parkLiftZ"])
        self._parkSpeedXY = self._settings.get(["parkSpeedXY"])
        self._parkSpeedZ = self._settings.get(["parkSpeedZ"])

    def set_pause_pos(self, x, y, z, *a, **k):
        self.pausePosX = x
        self.pausePosY = y
        self.pausePosZ = z

    def reset_pause_pos(self):
        self.pausePosX = None
        self.pausePosY = None
        self.pausePosZ = None
    
    def get_park_pos(self):
        if self._parkLocation == ParkOnPauseParkLocations.CUSTOM.lower():
            return self._parkPosX, self._parkPosY
        else:
            profile = self._printer_profile_manager.get_current()
            if self._parkLocation == ParkOnPauseParkLocations.CENTER.lower():
                return profile.volume.width / 2, profile.volume.depth / 2
            elif self._parkLocation == ParkOnPauseParkLocations.MIN_MIN.lower():
                return 0, 0
            elif self._parkLocation == ParkOnPauseParkLocations.MIN_MAX.lower():
                return 0, profile.volume.depth
            elif self._parkLocation == ParkOnPauseParkLocations.MAX_MIN.lower():
                return profile.volume.width, 0
            elif self._parkLocation == ParkOnPauseParkLocations.MAX_MAX.lower():
                return profile.volume.width, profile.volume.depth
            else:
                self._logger.error("Invalid Park Location = %s", self._parkLocation)
                return 0, 0

    def get_park_speeds(self):
        if self._parkSpeed == ParkOnPauseParkSpeeds.AUTO.lower():
            profile = self._printer_profile_manager.get_current()
            return min(profile.axes.x.speed, profile.axes.y.speed), profile.axes.z.speed
        else:
            return self._parkSpeedXY, self._parkSpeedZ

    def _enabled_for_current_profile(self):
        if self._profileMode == ParkOnPauseProfileModes.ALL.name:
            return True
        profile = self._printer_profile_manager.get_current()
        if not profile:
            return False
        profile_id = profile.get('id', False)
        if not profile_id:
            return False
        return profile_id in self._selectedProfiles

    ##~~ StartupPlugin
    def on_after_startup(self):
        self._logger.info("ParkOnPause Loaded")

    ##~~ AssetPlugin
    def get_assets(self):
        return dict(
            js=["js/ParkOnPause.js"],
        )

    ##~~ SettingsPlugin
    def get_settings_defaults(self):
        return {
            "profileMode": ParkOnPauseProfileModes.ALL.name.lower(),
            "selectedProfiles": [],
            "enableParkOnPause": True,
            "homeBeforeUnpark": False,
            "parkLocation": ParkOnPauseParkLocations.CENTER.name.lower(),
            "parkSpeed": ParkOnPauseParkSpeeds.AUTO.name.lower(),
            "parkPosX": 0,  # mm
            "parkPosY": 0,  # mm
            "parkLiftZ": 5,  # mm
            "parkSpeedXY": 100,  # mm/s
            "parkSpeedZ": 20,  # mm/s
        }

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.initialize()

    ##~~ TemplatePlugin
    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": "ParkOnPause",
                "template": "ParkOnPause_settings.jinja2",
                "custom_bindings": False,
            }
        ]
    
    # ~~ EventHandlerPlugin hook
    def on_event(self, event, payload):
        if self._enableParkOnPause and self._enabled_for_current_profile():
            if event == "PrintPaused":
                self.set_pause_pos(**payload['position'])
                self._logger.info("Parking Print Head")
                parkX, parkY = self.get_park_pos()
                speedXY, speedZ = self.get_park_speeds()
                cmds = [
                    'G91', # Relative positioning
                    f'G0 Z{self._parkLiftZ} F{speedZ}', # Lift Z-Axis
                    'G90', # Absolute positioning
                    f'G0 X{parkX} Y{parkY} F{speedXY}', # Park X/Y axes
                    'M400', # Finish Commands
                ]
                self._printer.commands(cmds)

            elif event == "PrintResumed":
                if any([e is None for e in [self.pausePosX, self.pausePosY, self.pausePosY]]):
                    self._logger.error(
                        'ParkOnPause is resuming but some of pausePos is invalid! [%s, %s, %s]',
                        self.pausePosX, self.pausePosY, self.pausePosZ
                    )
                    self._event_bus.fire("Error", {
                        "error": '\nParkOnPause cannot resume print! Some of the stored pause position is invalid.'
                    })
                    self._printer.cancel_print()
                    return False

                self._logger.info("Unparking Print Head")
                speedXY, speedZ = self.get_park_speeds()
                cmds = [
                    'G90', # Absolute positioning
                    f'G0 X{self.pausePosX} Y{self.pausePosY} F{speedXY}', # Unpark X/Y axes
                    f'G0 Z{self.pausePosZ} F{speedZ}', # Lower Z-Axis
                    'M400', # Finish Commands
                ]
                if self._homeBeforeUnpark:
                    cmds.insert(0, 'G28 X Y')  # Home X and Y axes only (if enabled)
                self.reset_pause_pos()
                self._printer.commands(cmds)

        return True

    ## Software Update Hook
    def get_update_information(self):
        return dict(
            ParkOnPause=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,
                type="github_release",
                user="kforth",
                repo="OctoPrint-ParkOnPause",
                current=self._plugin_version,
                stable_branch=dict(
                    name="Stable", branch="main", comittish=["main"]
                ),
                # update method: pip
                pip="https://github.com/kforth/OctoPrint-ParkOnPause/archive/{target_version}.zip",
            )
        )


__plugin_name__ = "ParkOnPause"
__plugin_version__ = "0.1.0"
__plugin_description__ = "Move the print head to a specific position when a print is paused."
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = ParkOnPausePlugin()
__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

