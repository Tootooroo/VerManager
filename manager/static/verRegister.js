import util from "./lib/util.js";

var NUM_OF_REVISION_CELL = 50;

function verRegister_main() {
    // Get collection of revision infos
    var infos = revisionInfos(null, NUM_OF_REVISION_CELL);

    // Create a group of radio by revision infos
    var radios = infos.map(function () {});

    // Register register button event handler to register button

    // Register scroll event handler to div

    var male_radio = radio_create("Resolve: #1 AAAAAAA", "12345678", "Root", true);

    var verList = document.getElementById("verList");
    verList.appendChild(male_radio);

    var submitBtn = document.getElementById("tryBtn");
    console.log(submitBtn.getAttribute("value"));
    submitBtn.onclick = function () {
        var csrftoken = util.getCookie('csrftoken');

        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function () {
            if (xhr.readyState == 4)
                alert("Done");
        };

        xhr.open("post", "verRegister/register", true);
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        xhr.send("123456");
    };
}

/* Get Collection of revision infos over Http request
 * if there has enough revision infos on server then
 * this function will return 'numOfRevision' of revision
 * after 'beginRevision'
 * Caution: If beginRevision is Null then the node before
 *          the last revision will see as the first
 *          be returned */
function revisionInfos(beginRevision, numOfRevision) {}

function radio_create(comment, revision, author, checked) {
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
