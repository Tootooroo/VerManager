import util from "./lib/util.js";
import { ok, error } from "./lib/type.js";

export { verRegister_main };

var NUM_OF_REVISION_CELL = 20;
var revSeperator = "__<?>__";
var revItemSeperator = "<:>";

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

    fillLogFrom(null);
    fillLogTo(null);

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
            var last = this.lastChild.previousSibling.getAttribute('value');
            var lastsn = last.split("<br>")[0];
            fillRevList('verList', lastsn, NUM_OF_REVISION_CELL);
        }
    });

    var selectFrom = document.getElementById('logFromSelect');
    selectFrom.addEventListener('scroll', function() {
        var runOut = this.scrollHeight - this.scrollTop === this.clientHeight;

        if (runOut) {
            var last = this.lastChild.getAttribute('value');
            fillLogFrom(last);
        }
    });

    var selectTo = document.getElementById('logToSelect');
    selectTo.addEventListener('scroll', function() {
        var runOut = this.scrollHeight - this.scrollTop === this.clientHeight;

        if (runOut) {
            var last = this.lastChild.getAttribute('value');
            fillLogTo(last);
        }
    });


    return ok;
}

function fillLog(beginRev, logId) {

    var select = document.getElementById(logId);

    var handler = function(responseText) {
        var infos = rawRevsParse(responseText);

        infos.map(function(rev) {
            var option = document.createElement("option");
            option.setAttribute("value", rev.sn);
            option.innerHTML = rev.sn;

            select.appendChild(option);
        });
    };

    revInfos(beginRev, NUM_OF_REVISION_CELL, handler);
}

function fillLogFrom(beginRev) {
    fillLog(beginRev, "logFromSelect");
}

function fillLogTo(beginRev) {
    fillLog(beginRev, "logToSelect");
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

    var select = document.getElementById(listId);

    var handler = function(responseText) {
        var infos = rawRevsParse(responseText);
        infos.map(function(rev) {
            var option = document.createElement("option");
            option.setAttribute("value", rev.sn);

            option.innerHTML = rev.sn + "<br>" + rev.comment + "<br>" + rev.author;

            var option_sep = document.createElement("option");
            option_sep.setAttribute("disabled", true);
            option_sep.innerHTML = "<br>";

            select.appendChild(option);
            select.appendChild(option_sep);
        });
    };

    revInfos(beginRevision, numOfRevision, handler);
}

function revInfos(beginRevision, numOfRevision, handler) {
    var csrftoken = util.getCookie('csrftoken');
    var data = {
        beginRev: beginRevision == null ? "null" : beginRevision,
        numOfRev: numOfRevision.toString()
    };

    var xhr = new XMLHttpRequest();
    xhr.open('post', 'verRegister/infos', true);

    // After revisions is retrived fill them into verList
    xhr.onload = function() {
        if (xhr.status == 200) {
            handler(xhr.responseText);
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
