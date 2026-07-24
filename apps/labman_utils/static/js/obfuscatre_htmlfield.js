$(document).ready(function() {
    function rot13(str) {
        return str.replace(/[A-Za-z]/g, function(c) {
            return String.fromCharCode(
                c.charCodeAt(0) + (c.toLowerCase() < 'n' ? 13 : -13)
            );
        });
    }

    function base64Encode(str) {
        return btoa(str);
    }

    function obfuscateHtmlContent() {
        var ret=false;
        $('.obfuscate_html').each(function() {
            if (this.hasAttribute("encoded")) {
                return true; }
            var originalText = $(this).val();
            var base64EncodedText = base64Encode(originalText);
            if (originalText.length > 8000) {
                alert("Your entry is too long ("+originalText.length+")- please shorten it and try again!\n Lots of formatting and images will very likely push you over the 8000 character limit.");
                ret=true;
                return true;
            }
            var rot13Text = "ROT13+B64:"+rot13(base64EncodedText);
            $(this).val(rot13Text);

            $(this).attr({"encoded":"True","original":originalText})
            console.log("obfuscator ret:"+originalText+" -> "+rot13Text);
        });

        return ret;
    }

    // Intercept form submission
    $('form').on('submit', function(event) {
        if ( obfuscateHtmlContent()) {
             $('.obfuscate_html').each(function() {
                 if (this.hasAttribute("original")) {
                     $(this).val($(this).attr("original"));
                     $(this).removeAttr("encoded")
                     $(this).removeAttr("original")
                     }
                     });

            event.preventDefault();
            event.stopPropagation();
        }
    });
});
