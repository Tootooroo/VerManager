import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

// Main
verGeneration_main();

// Definitions
function verGeneration_main() {
    var submit = document.getElementById('generationBtn');
    submit.addEventListener('click', function() {
        generate();
    });
}

function generate() {
    var csrftoken = util.getCookie('csrftoken');
    var xhr = new XMLHttpRequest();

    xhr.onload = function(event) {
        setTimeout(waitGenerateDone, 5000);
    };

    xhr.open('post', 'verRegister/generation', true);
    xhr.setRequestHeader('X-CSRFToken', csrftoken);

    var form = document.getElementById('genForm');
    var formData = new FormData(form);
    xhr.send(formData);

    return ok;
}

function waitGenerateDone() {
    var csrftoken = util.getCookie('csrftoken');
    var xhr = new XMLHttpRequest();

    xhr.onload = function(event) {
        // Generation is done
        if (xhr.status == 200) {
            // Download file via returned url
            location.assign(xhr.responseText);
        } else if (xhr.status == 304) {
            // Pending
            waitGenerateDone.prototype.timer = setTimeout(waitGenerateDone, 1000);
        } else if (xhr.status == 400) {
            // Generation failed
            clearTimeout(waitGenerateDone.prototype.timer);
        }
    };

    xhr.open('post', 'verRegister/isGenerateDone', true);
    xhr.setRequestHeader('X-CSRFToken', csrftoken);

    var form = document.getElementById('genForm');
    var formData = new FormData(form);

    xhr.send(formData);

    console.log("waitGenerationDone");
}
