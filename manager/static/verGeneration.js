import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

var verSeperator = "__<?>__";

// Main
verGeneration_main();

// Definitions
function verGeneration_main() {
    fillVerList();

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

function fillVerList() {
    var csrftoken = util.getCookie('csrftoken');

    var xhr = new XMLHttpRequest();
    xhr.open('post', 'verRegister/verInfos', true);

    xhr.onload = function() {

        console.log(xhr.responseText);
        if (xhr.status != 200)
            return null;

        var vers = xhr.responseText.split(verSeperator);
        console.log(vers);
        var ver_options = vers.map(function(ver) {
            var ver_option = document.createElement("option");
            ver_option.setAttribute("value", ver);
            ver_option.innerHTML = ver;

            return ver_option;
        });

        var select = document.getElementById('verSelect');
        ver_options.map(function(option) {
            select.appendChild(option);
        });
    };

    xhr.setRequestHeader('X-CSRFToken', csrftoken);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send();
}
