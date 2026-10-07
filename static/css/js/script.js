function scrollToMentors() {
    document.getElementById("mentors").scrollIntoView({
        behavior: "smooth"
    });
}

function scrollToCareers() {
    document.getElementById("careers").scrollIntoView({
        behavior: "smooth"
    });
}

function connectMentor(name) {

    document.getElementById("popupTitle").innerText =
        "Connect with " + name;

    document.getElementById("popupText").innerText =
        "Mentor connection request is ready. This feature will allow students to send mentorship requests and start conversations.";

    document.getElementById("popup").style.display = "flex";
}

function showCareer(career) {

    document.getElementById("popupTitle").innerText =
        career;

    document.getElementById("popupText").innerText =
        "Career roadmap: Explore required skills, recommended learning resources, projects, internships and suitable alumni mentors for this career.";

    document.getElementById("popup").style.display = "flex";
}

function showLogin() {

    document.getElementById("popupTitle").innerText =
        "Welcome to AlumniConnect";

    document.getElementById("popupText").innerText =
        "Student and alumni authentication will be available here.";

    document.getElementById("popup").style.display = "flex";
}

function closePopup() {
    document.getElementById("popup").style.display = "none";
}


function filterMentors() {

    const search =
        document.getElementById("mentorSearch")
        .value
        .toLowerCase();

    const cards =
        document.querySelectorAll(".mentor-card");

    cards.forEach(card => {

        const text =
            card.innerText.toLowerCase();

        if (text.includes(search)) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }

    });
}


window.onclick = function(event) {

    const popup =
        document.getElementById("popup");

    if (event.target === popup) {
        closePopup();
    }

};