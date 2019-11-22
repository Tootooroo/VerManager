import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

var NUM_OF_REVISION_CELL = 10;
var revSeperator = "__<?>__";
var revItemSeperator = "<:>";

// Main
verRegister_main();

// Defitions
function RevInfos(sn, author, comment) {
    this.sn = sn;
    this.author = author;
    this.comment = comment;

    this.stringify = function() {
        return "SN:" + this.sn + "<br>Author:" + this.author + "<br>Comment:" + this.comment;
    };
}

function verRegister_main() {
    // Fill revisions into verList
    fillRevList('verList', null, NUM_OF_REVISION_CELL);

    var submit = document.getElementById('registerBtn');
    submit.addEventListener('click', function() {
        var csrftoken = util.getCookie('csrftoken');
        var xhr = new XMLHttpRequest();

        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4) {
                switch(xhr.status) {
                case 200:
                    alert("Registered");
                    break;
                case 304:
                    alert("Already registered");
                    break;
                }
            }
        };

        xhr.open('post', 'verRegister/register', true);
        xhr.setRequestHeader('X-CSRFToken', csrftoken);

        var form = document.getElementById('regForm');
        var formData = new FormData(form);
        xhr.send(formData);
    });

    // Register scroll event handler to div
    var div = document.getElementById('verList');
    div.addEventListener('scroll', function() {
        var runOut = this.scrollHeight - this.scrollTop === this.clientHeight;

        if (runOut) {
            var lastRadioVal = this.lastChild.firstChild.getAttribute('value');
            fillRevList('verList', lastRadioVal, NUM_OF_REVISION_CELL);
        }
    });

    return ok;
}

/* Get Collection of revision infos over Http request
 * if there has enough revision infos on server then
 * this function will return 'numOfRevision' of revision
 * after 'beginRevision'
 *
 * Caution: If beginRevision is Null then the node before
 *          the last revision will see as the first
 *          be returned */
function fillRevList(listId, beginRevision, numOfRevision) {

    var csrftoken = util.getCookie('csrftoken');
    var data = {
        beginRev: beginRevision == null ? "null" : beginRevision,
        numOfRev:numOfRevision.toString()
    };

    var xhr = new XMLHttpRequest();
    xhr.open('post', 'verRegister/infos', true);

    // After revisions is retrived fill them into verList
    xhr.onreadystatechange = function() {

        if (xhr.readyState == 4 && xhr.status == 200) {
            var infos = rawRevsParse(xhr.responseText);
            var radios = infos.map(radio_create);
            radios.map(function(radio) {
                radioAppend(listId, radio);
            });
        }
    };

    xhr.setRequestHeader('X-CSRFToken', csrftoken);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify(data));
}

/* Format of raw revisions: SN<:>AUTHOR<:>COMMENT__<?>__SN<:>...
 * after parsed a list of Object RevInfos will be returned */
function rawRevsParse(revisions) {
    var revs = revisions.split(revSeperator);
    revs = revs.map(function (rev) {
        var rev_ = rev.split(revItemSeperator);
        return new RevInfos(rev_[0], rev_[1], rev_[2]);
    });

    return revs;
}

function radioAppend(element, radio) {
    var list = document.getElementById('verList');
    list.appendChild(radio);

    return ok;
}

function radio_create(revInfos) {
    var content = revInfos.stringify();

    var div = document.createElement("div");

    var label = document.createElement("Label");
    label.setAttribute("for", "verChoice");
    label.innerHTML = content;

    var radio = document.createElement("input");
    radio.setAttribute("type", "radio");
    radio.setAttribute("name", "verChoice");
    radio.setAttribute("value", revInfos.sn);

    div.appendChild(radio);
    div.appendChild(label);

    return div;
}
