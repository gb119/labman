if (!window.$) {

window.$ = window.django.jQuery;
}

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
        $('.obfuscate_html').each(function() {
            if (this.hasAttribute("encoded")) {
                return;
            }
            var originalText = $(this).val();
            var base64EncodedText = base64Encode(originalText);
            var rot13Text = rot13(base64EncodedText);
            $(this).val(rot13Text);
            $(this).attr({"encoded":"True"})
        });
    }

    // Intercept form submission
    $('form').on('submit', function(event) {
        obfuscateHtmlContent();
    });
});
