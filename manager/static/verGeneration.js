import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

export { verGeneration_main };

const verSeperator = "__<?>__";

// Definitions
function verGeneration_main() {
    fillVerList();

    let submit = document.getElementById('generationBtn');
    submit.addEventListener('click', function() {
        let vSelect = document.getElementById('verSelect');

        generate();

        vSelect.setAttribute('disabled', true);
        submit.setAttribute('disabled', true);
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

    var verIdent = formData.get("verSelect");
    waitGenerateDone.prototype.verSelect = verIdent;

    xhr.send(formData);

    return ok;
}

function waitGenerateDone() {
    var csrftoken = util.getCookie('csrftoken');
    var xhr = new XMLHttpRequest();

    xhr.onload = function(event) {
        // Generation is done
        if (xhr.status == 200) {
            var submit = document.getElementById('generationBtn');
            var vSelect = document.getElementById('verSelect');
            submit.setAttribute('disabled', false);
            vSelect.setAttribute('disabled', false);

            // Download file via returned url
            location.assign(xhr.responseText);
        } else if (xhr.status == 304) {
            // Pending
            waitGenerateDone.prototype.timer = setTimeout(waitGenerateDone, 1000);
        } else if (xhr.status == 400) {
            // Generation failed
            alert("Generation failed");
            clearTimeout(waitGenerateDone.prototype.timer);
        }
    };

    xhr.open('post', 'verRegister/isGenerateDone', true);
    xhr.setRequestHeader('X-CSRFToken', csrftoken);

    var form = document.getElementById('genForm');
    var formData = new FormData(form);
    formData.append("verSelect", waitGenerateDone.prototype.verSelect);

    xhr.send(formData);

}

function fillVerList() {
    var csrftoken = util.getCookie('csrftoken');

    var xhr = new XMLHttpRequest();
    xhr.open('post', 'verRegister/verInfos', true);

    xhr.onload = function() {

        if (xhr.status != 200)
            return null;

        var vers = xhr.responseText.split(verSeperator);
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

        return null;
    };

    xhr.setRequestHeader('X-CSRFToken', csrftoken);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send();
}
