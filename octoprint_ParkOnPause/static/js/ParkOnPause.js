/*
 * View model for OctoPrint-ParkOnPause
 *
 * Author: Kestin Goforth
 * License: AGPLv3
 */
$(function () {
  function ParkOnPauseViewModel(parameters) {
    var self = this;

    self.settings = parameters[0];
    self.printerProfiles = parameters[1];
    
    self.enableParkOnPause = ko.observable();
    self.homeBeforeUnpark = ko.observable();
    self.parkLocation = ko.observable();
    self.parkPosX = ko.observable();
    self.parkPosY = ko.observable();
    self.parkLiftZ = ko.observable();
    self.parkSpeed = ko.observable();
    self.parkSpeedXY = ko.observable();
    self.parkSpeedZ = ko.observable();
    self.profileMode = ko.observable();
    self.selectedProfiles = ko.observableArray([]);

    self.onBeforeBinding = function () {
      self.enableParkOnPause(self.settings.settings.plugins.ParkOnPause.enableParkOnPause());
      self.homeBeforeUnpark(self.settings.settings.plugins.ParkOnPause.homeBeforeUnpark());
      self.parkLocation(self.settings.settings.plugins.ParkOnPause.parkLocation());
      self.parkPosX(self.settings.settings.plugins.ParkOnPause.parkPosX());
      self.parkPosY(self.settings.settings.plugins.ParkOnPause.parkPosY());
      self.parkLiftZ(self.settings.settings.plugins.ParkOnPause.parkLiftZ());
      self.parkSpeed(self.settings.settings.plugins.ParkOnPause.parkSpeed());
      self.parkSpeedXY(self.settings.settings.plugins.ParkOnPause.parkSpeedXY());
      self.parkSpeedZ(self.settings.settings.plugins.ParkOnPause.parkSpeedZ());
      self.profileMode(self.settings.settings.plugins.ParkOnPause.profileMode());
      self.selectedProfiles(self.settings.settings.plugins.ParkOnPause.selectedProfiles());
    };
  }

  OCTOPRINT_VIEWMODELS.push({
    construct: ParkOnPauseViewModel,
    dependencies: ["settingsViewModel", "printerProfilesViewModel"],
    elements: ["#settings_plugin_ParkOnPause"]
  });
});
