# -*- coding: utf-8 -*-
from __future__ import absolute_import

import octoprint.plugin
import logging

class ProfileMode:
    ALL = "all"
    SELECT = "select"

class ParkLocation:
    CENTER = "center"
    MIN_MIN = "min"
    MAX_MAX = "max"
    MIN_MAX = "min_max"
    MAX_MIN = "max_min"
    CUSTOM = "custom"

class ParkSpeed:
    AUTO = "auto"
    CUSTOM = "custom"

class ParkOnPausePlugin(
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin
):

    def __init__(self):
        # self._logger = logging.getLogger(__name__)

        self.pausePosX = None
        self.pausePosY = None
        self.pausePosZ = None
        
        self._profileMode = ProfileMode.ALL
        self._selectedProfiles = []
        self._enableParkOnPause = True
        self._homeBeforeUnpark = False
        self._parkLocation = ParkLocation.CENTER
        self._parkSpeed = ParkSpeed.AUTO
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
        if self._parkLocation == ParkLocation.CUSTOM:
            return self._parkPosX, self._parkPosY
        else:
            profile = self._printer_profile_manager.get_current()
            if self._parkLocation == ParkLocation.CENTER:
                return profile['volume']['width'] / 2, profile['volume']['depth'] / 2
            elif self._parkLocation == ParkLocation.MIN_MIN:
                return 0, 0
            elif self._parkLocation == ParkLocation.MIN_MAX:
                return 0, profile['volume']['depth']
            elif self._parkLocation == ParkLocation.MAX_MIN:
                return profile['volume']['width'], 0
            elif self._parkLocation == ParkLocation.MAX_MAX:
                return profile['volume']['width'], profile['volume']['depth']
            else:
                self._logger.error("Invalid Park Location = %s", self._parkLocation)
                return 0, 0

    def get_park_speeds(self):
        if self._parkSpeed == ParkSpeed.AUTO:
            profile = self._printer_profile_manager.get_current()
            return min(profile['axes']['x']['speed'], profile['axes']['y']['speed']), profile['axes']['z']['speed']
        else:
            return self._parkSpeedXY, self._parkSpeedZ

    def _enabled_for_current_profile(self):
        if self._profileMode == ProfileMode.ALL:
            return True
        profile = self._printer_profile_manager.get_current()
        if not profile:
            return False
        profile_id = profile.get('id', False)
        if not profile_id:
            return False
        return profile_id in self._selectedProfiles

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            "profileMode": ProfileMode.ALL,
            "selectedProfiles": [],
            "enableParkOnPause": True,
            "homeBeforeUnpark": False,
            "parkLocation": ParkLocation.CENTER,
            "parkSpeed": ParkSpeed.AUTO,
            "parkPosX": 0,  # mm
            "parkPosY": 0,  # mm
            "parkLiftZ": 5,  # mm
            "parkSpeedXY": 100,  # mm/s
            "parkSpeedZ": 20,  # mm/s
        }

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.initialize()

    ##~~ AssetPlugin mixin
    def get_assets(self):
        return dict(
            js=["js/ParkOnPause.js"],
        )

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": "ParkOnPause Plugin",
                "template": "ParkOnPause_settings.jinja2",
                "custom_bindings": True,
            }
        ]

    def get_template_vars(self):
        return dict(
            enableParkOnPause=self._settings.get(["enableParkOnPause"]),
            homeBeforeUnpark=self._settings.get(["homeBeforeUnpark"]),
            parkLocation=self._settings.get(["parkLocation"]),
            parkPosX=self._settings.get(["parkPosX"]),
            parkPosY=self._settings.get(["parkPosY"]),
            parkLiftZ=self._settings.get(["parkLiftZ"]),
            parkSpeed=self._settings.get(["parkSpeed"]),
            parkSpeedXY=self._settings.get(["parkSpeedXY"]),
            parkSpeedZ=self._settings.get(["parkSpeedZ"]),
            profileMode=self._settings.get(["profileMode"]),
            selectedProfiles=self._settings.get(["selectedProfiles"])
        )
    
    # ~~ EventHandlerPlugin hook

    def on_event(self, event, payload):
        if event not in ("PrintPaused", "PrintResumed"):
            return
        self._logger.error(event)
        if not self._enableParkOnPause or not self._enabled_for_current_profile():
            return

        if event == "PrintPaused":
            self.set_pause_pos(**payload['position'])
            self._logger.info("Parking Print Head")
            parkX, parkY = self.get_park_pos()
            speedXY, speedZ = self.get_park_speeds()

            self._printer.jog({'z': self._parkLiftZ}, True, speedZ)
            self._printer.jog({'x': parkX, 'y': parkY}, False, speedXY)
            self._printer.commands("M400")

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

            if self._homeBeforeUnpark:
                self._printer.home(['x', 'y'])
            self._printer.jog({'x': self.pausePosX, 'y': self.pausePosY}, False, speedXY)
            self._printer.jog({'z': self.pausePosZ}, False, speedZ)
            self._printer.commands("M400")
            self.reset_pause_pos()

        return True

    ## Softwareupdate Hook

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


__plugin_name__ = "ParkOnPause Plugin"
__plugin_version__ = "0.1.0"
__plugin_description__ = "Move the print head to a specific position when a print is paused."
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = ParkOnPausePlugin()
__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

