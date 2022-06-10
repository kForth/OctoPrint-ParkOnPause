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

    self.initializeSettings = function () {

      // Callback function to show/hide custom park location.
      self.onParkLocationChange = function () {
        $("#parkOnPause-custom-park-position").toggleClass('hidden',
          $(this).children('option:selected').val() != "custom"
        );
      };
      $("#parkOnPause-park-location").on('change', self.onParkLocationChange);

      // Callback function to show/hide custom park speed.
      self.onParkSpeedChange = function () {
        $("#parkOnPause-custom-park-speed").toggleClass('hidden',
          $(this).children('option:selected').val() != "custom"
        );
      };
      $("#parkOnPause-park-speed").on('change', self.onParkSpeedChange);

      // Callback function to enable/disable profile list based on radio buttons.
      self.onProfileModeChange = function () {
        let val = $("input[name='parkOnPauseProfileModeGroup']:checked").val();
        $("#parkOnPause-profile-list").attr('disabled', val == "all");
      };
      $("#parkOnPause-profile-mode").on('change', self.onProfileModeChange);

      // Update elements when the settings page is opened.
      $("#settings_plugin_ParkOnPause_link").on('click', () => {
        $("#parkOnPause-park-location").trigger('change');
        $("#parkOnPause-park-speed").trigger('change');
        $("#parkOnPause-profile-mode").trigger('change');
      });
    };

    self.initializeSettings();
  }

  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: ParkOnPauseViewModel,
    dependencies: ["settingsViewModel"],
    elements: []
  });
});
