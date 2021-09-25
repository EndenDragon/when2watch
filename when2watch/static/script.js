(function () {
    window.addEventListener("load", init);

    function init() {
        fetchAPI();

        let day = moment().local().isoWeekday();
        id("weekday-card-" + day).classList.add("border-primary");
        id("weekday-card-" + day).querySelector(".card-title").id = "today";

        id("profile-picture").addEventListener("click", openMAL);

        $("[data-toggle=popover]").popover();
        id("date-btn").addEventListener("inserted.bs.popover", initDatePicker);
    }

    function initDatePicker() {
        let popoverEl = bootstrap.Popover.getInstance(id("date-btn")).tip;
        if (popoverEl.querySelector(".calendar") == null) {
            let dateDiv = gen("div");
            dateDiv.classList.add("calendar");
            popoverEl.appendChild(dateDiv);
            $(dateDiv).datepicker();

            let searchParams = new URLSearchParams(window.location.search);
            let date = moment(searchParams.get("date"), "MM-DD-YYYY");
            if (date.isValid()) {
                date = date.toDate();
            } else {
                date = Date();
            }
            $(dateDiv).datepicker("setDate", date);
            $(dateDiv).on("changeDate", updateDate);
        }
    }

    function updateDate(event) {
        let date = moment(event.date);
        let searchParams = new URLSearchParams(window.location.search);
        searchParams.set("date", date.format("MM-DD-YYYY"));
        window.location.search = searchParams.toString();
    }

    function openMAL() {
        window.open("https://myanimelist.net/animelist/" + id("profile-picture").getAttribute("username"));
    }

    function fetchAPI() {
        let url = "api";
        let date = new URLSearchParams(window.location.search).get('date');
        if (date) {
            url = "api?date=" + date;
        }
        fetch(url)
            .then(checkStatus)
            .then(JSON.parse)
            .then(handleResponse)
            .catch(handleError);
    }

    function handleError(error) {
        id("loading").classList.add("d-none");
        id("welcome").classList.remove("d-none");
        console.error(error);
    }

    function getDay(day) {
        let dayINeed = -1;
        if (day == "sunday") {
            dayINeed = 7;
        } else if (day == "monday") {
            dayINeed = 1;
        } else if (day == "tuesday") {
            dayINeed = 2;
        } else if (day == "wednesday") {
            dayINeed = 3;
        } else if (day == "thursday") {
            dayINeed = 4;
        } else if (day == "friday") {
            dayINeed = 5;
        } else if (day == "saturday") {
            dayINeed = 6;
        }

        if (dayINeed < 0) {
            return null;
        }

        let today = moment().tz("Asia/Tokyo").isoWeekday();
        // if we haven't yet passed the day of the week that I need:
        if (today <= dayINeed) { 
            // then just give me this week's instance of that day
            return moment().tz("Asia/Tokyo").isoWeekday(dayINeed);
        } else {
            // otherwise, give me *next week's* instance of that same day
            return moment().tz("Asia/Tokyo").add(1, 'weeks').isoWeekday(dayINeed);
        }
    }

    function handleResponse(response) {
        id("profile-picture").src = response.user.picture;
        id("profile-picture").setAttribute("username", response.user.name);

        for (let i = 0; i < response.animelist.watching.length; i++) {
            
            insertAnime(response.animelist.watching[i], "watching");
        }

        for (let i = 0; i < response.animelist.plan_to_watch.length; i++) {
            insertAnime(response.animelist.plan_to_watch[i], "plan_to_watch");
        }

        id("loading").classList.add("d-none");
        id("user-corner").classList.remove("invisible");
        id("weekdays").classList.remove("d-none");
        id("today-btn").classList.remove("invisible");
        id("date-btn").classList.remove("invisible");
    }

    function insertAnime(anime, type) {
        let time = null;
        let local = null;
        let weekday = 0;
        if (anime.broadcast) {
            time = getDay(anime.broadcast.day_of_the_week)
        }
        if (time !== null) {
            if (anime.broadcast.start_time) {
                let broadcastTimeSplit = anime.broadcast.start_time.split(":");
                time.set("hour", broadcastTimeSplit[0]);
                time.set("minute", broadcastTimeSplit[1]);
            } else {
                time.set("hour", 12); // middle of the day to be correct within 50/50
                time.set("minute", 0);
            }
            local = time.local();
            weekday = local.isoWeekday();
        }

        let card = gen("div");
        card.classList.add("card", "col-xs-12", "col-sm-6", "col-md-3", "col-lg-2");

        let img = gen("img");
        img.classList.add("card-img-top");
        img.src = anime.main_picture.large;
        card.appendChild(img);

        let cardBody = gen("div");
        card.appendChild(cardBody);

        let cardTitle = gen("h5");
        cardBody.appendChild(cardTitle);

        let cardTitleLink = gen("a");
        cardTitleLink.href = "https://myanimelist.net/anime/" + anime.id + "/" + anime.title.replace(/[\!\"\#\%\'\(\)\*\,\.\@\[\]\~\;]/g, "").replace(/[^a-zA-Z0-9\-]/g, "_");
        cardTitleLink.target = "_blank";
        cardTitleLink.textContent = anime.title;
        cardTitle.appendChild(cardTitleLink);

        let cardText = gen("p");
        cardBody.appendChild(cardText);
        if (local !== null) {
            cardText.textContent = local.format("hh:mm A ");
        }

        let edit = gen("a");
        edit.href = "https://myanimelist.net/ownlist/anime/" + anime.id + "/edit"
        edit.textContent = "(edit)";
        edit.target = "_blank";
        cardText.appendChild(edit);

        cardText.appendChild(gen("br"));
        let badge = gen("span");
        if (type == "watching") {
            badge.classList.add("badge", "bg-success");
            badge.textContent = "Watching";
        } else if (type == "plan_to_watch") {
            badge.classList.add("badge", "bg-info");
            badge.textContent = "Plan to Watch";
        }
        cardText.appendChild(badge);

        if (anime.status == "not_yet_aired" || anime.status == "finished_airing") {
            let airbadge = gen("span");
            if (anime.status == "not_yet_aired") {
                airbadge.classList.add("badge", "bg-danger");
                airbadge.textContent = "Not Yet Aired";
            } else if (anime.status == "finished_airing") {
                airbadge.classList.add("badge", "bg-primary");
                airbadge.textContent = "Finished Airing";
            }
            cardText.appendChild(document.createTextNode(" "));
            cardText.appendChild(airbadge);
        }

        id("weekday-card-" + weekday).querySelector(".anime-grid").appendChild(card);
        if (weekday == 0) {
            id("weekday-card-0").classList.remove("d-none");
        }
    }

    function checkStatus(response) {
        if (response.status >= 200 && response.status < 300) {
            return response.text();
        } else {
            return Promise.reject(new Error(response.status + ": " + response.statusText));
        }
    }

    function id(elementId) {
        return document.getElementById(elementId);
    }

    function gen(element) {
        return document.createElement(element);
    }
})();
