"use strict";

window.addEventListener("DOMContentLoaded", function() {
    const elem=document.querySelector("#modal");

    const defaultWidgetOptions = {
      icons: {
        time: 'bi-clock',
        date: 'bi-calendar',
        up: 'bi-chevron-up',
        down: 'bi-chevron-down',
        previous: 'bi-chevron-left',
        next: 'bi-chevron-right',
        today: 'bi-record-circle',
        clear: 'bi-trash',
        close: 'bi-x-lg'
      }
    }
    function getConfig(inputElement) {
      let /** @type {WidgetInputConfig} */ config;
      try {
        config = JSON.parse(inputElement.dataset.dbdpConfig);
      }
      catch (err) { throw Error("Invalid input config") }
      const optionKeyName = inputElement.name.replace(/^(.*-)?/, "dbdpOptions_")
      config.options = { ...defaultWidgetOptions, ...window.dbdpOptions, ...window[optionKeyName], ...config.options };
      config.events = { ...window.dbdpEvents, ...window[optionKeyName.replace("dbdpOptions_", "dbdpEvents_")] };
      return config;
    }
    htmx.on("htmx:afterSwap", (e) => {
        // Response targeting #dialog => show the modal
        if (e.detail.target.id == "dialog") {
            var modal = bootstrap.Modal.getOrCreateInstance(elem)
            modal.show()


            if (document.querySelector("#user__textinput")) {
                htmx.trigger("#user__textinput","focus");
                htmx.trigger("#user__textinput","mousedown");
            }
            var frm = document.querySelector("#booking");
            if (frm) {
                frm.addEventListener('keypress', function (event) {
                    if (event.keyCode === 13) {
                        event.preventDefault();
                        htmx.trigger("#submit_booking","focus");
                        htmx.trigger("#booking","submit");
                    }
                });
            }
        }
    });
  htmx.on("htmx:beforeSwap", (e) => {
    // Empty response targeting #dialog => hide the modal
    if (e.detail.target.id == "dialog" && e.detail.xhr.status==204) {
      var modal = bootstrap.Modal.getOrCreateInstance(elem)
      modal.hide()
      e.detail.shouldSwap = false
    }
  });

  // Remove dialog content after hiding
  htmx.on("hidden.bs.modal", () => {
    document.getElementById("dialog").innerHTML = ""
  });
});
