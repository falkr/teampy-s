$(document).ready(function() {
  $(window).resize(refreshAsides);

  // Since we may not have the height correct for the images, adjust the asides
  // too when an image is loaded.
  $('img').on('load', function() {
    refreshAsides();
  });

  // On the off chance the browser supports the new font loader API, use it.
  if (document.fontloader) {
    document.fontloader.notifyWhenFontsReady(function() {
      refreshAsides();
    });
  }

  // Lame. Just do another refresh after a second when the font is *probably*
  // loaded to hack around the fact that the metrics changed a bit.
  window.setTimeout(refreshAsides, 200);

  refreshAsides();
});

function refreshAsides() {
  // Don't position them if they're inline.
  if ($(document).width() < 800) return;

  // Vertically position the asides next to the span they annotate.
  $("aside").each(function() {
    var aside = $(this);

    // Find the span the aside should be anchored next to.
    var name = aside.attr("name");
    var span = $("span[name='" + name + "']");
    if (span == null) {
      window.console.log("Could not find span for '" + name + "'");
      return;
    }

    aside.offset({top: span.position().top - 3 + 80 - 80});
  });
}


$(document).ready(function() {
    var coll = document.getElementsByClassName("w3collapsible");
    var i;
    
    for (i = 0; i < coll.length; i++) {
      coll[i].addEventListener("mousedown", function() {
        var content = this.nextElementSibling;
        content.style.filter = "none";
      });
      coll[i].addEventListener("mouseup", function() {
        var content = this.nextElementSibling;
        content.style.filter = "blur(3px)";
      });
    }

    //For fancy numbered lists starting at start AKA :steps: 
    $(".steps ol").each(function(idx, el) {
        var index = parseInt($(el).attr("start"))-1;
          if (!isNaN(index)) {
              $(el).css({'counter-reset':'li ' + index});    
          }
    });

});


