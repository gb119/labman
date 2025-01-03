window.addEventListener("DOMContentLoaded", function() {
const elem=document.querySelector("#modal");

  htmx.on("htmx:afterSwap", (e) => {
    // Response targeting #dialog => show the modal
    if (e.detail.target.id == "dialog") {
    var modal = bootstrap.Modal.getOrCreateInstance(elem)
    modal.show()
    htmx.trigger("#user__textinput","focus");
    htmx.trigger("#user__textinput","mousedown");

    var frm = document.querySelector("#booking");

    frm.addEventListener('keypress', function (event) {
        if (event.keyCode === 13) {
            event.preventDefault();
            htmx.trigger("#submit_booking","focus");
            htmx.trigger("#booking","submit");
        }

    });
    }
  })

  htmx.on("htmx:beforeSwap", (e) => {
    // Empty response targeting #dialog => hide the modal
    if (e.detail.target.id == "dialog" && e.detail.xhr.status==204) {
      var modal = bootstrap.Modal.getOrCreateInstance(elem)
      modal.hide()
      e.detail.shouldSwap = false
    }
  })

  // Remove dialog content after hiding
  htmx.on("hidden.bs.modal", () => {
    document.getElementById("dialog").innerHTML = ""
  })




}, false);