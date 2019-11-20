import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

var NUM_OF_REVISION_CELL = 50;

function RevInfos(sn, author, comment) {
    this.sn = sn;
    this.author = author;
    this.comment = comment;
}

function verRegister_main() {
    // Get collection of revision infos
    var infos = revisionInfos(null, NUM_OF_REVISION_CELL);
    // Create a group of radio by revision infos
    var radios = infos.map(radio_create);

    // Register scroll event handler to div
    var div = document.getElementById('verList');
    div.addEventListener('scroll', function() {
        var runOut = this.scrollHeight - this.scrollTop === this.clientHeight;

        if (runOut) {
            var bottomRev = this.lastChild.getAttribute('value');
            fillRevList('verList', bottomRev, NUM_OF_REVISION_CELL);
        }
    });

    return ok;
}

function fillRevList(listId, revBegin, numOfRevision) {
    var infos = revisionInfos(revBegin, numOfRevision);
    var radios = infos.map(radio_create);
    // Append radios onto revision list which id is 'listId'
    radios.map(function(radio) {
        radioAppend(listId, radio);
    });
}

/* Get Collection of revision infos over Http request
 * if there has enough revision infos on server then
 * this function will return 'numOfRevision' of revision
 * after 'beginRevision'
 *
 * Caution: If beginRevision is Null then the node before
 *          the last revision will see as the first
 *          be returned */
function revisionInfos(beginRevision, numOfRevision) {
    var xhr = new XMLHttpRequest();
    xhr.open('get', '...', true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4) {
            return revisionInfos.rawProcess(xhr.responseText);
        }
    };
    xhr.send(null);

    // fixme: complete this method after raw revision format is
    //        determined.
    revisionInfos.rawProcess = function(raw) {};
}

function radioAppend(element, radio) {
    var list = getElementById('verList');
    list.appendChild(radio);

    return ok;
}

function radio_create(revInfos) {
    var div = document.createElement("div");

    var content = comment + ":" + revision + ":" + author;

    var label = document.createElement("Label");
    label.setAttribute("for", "verChoice");
    label.innerHTML = content;

    var radio = document.createElement("input");
    radio.setAttribute("type", "radio");
    radio.setAttribute("name", "verChoice");
    radio.setAttribute("value", content);

    div.appendChild(radio);
    div.appendChild(label);

    return div;
}

verRegister_main();
