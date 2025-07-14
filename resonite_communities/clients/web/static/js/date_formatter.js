function formatDatesOnLoad() {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    const dates_tip = document.querySelectorAll(".date i");
    dates_tip.forEach((date_tip) => {
        date_tip.title = 'Dates are in ' + timezone + ' timezone';
    });

    const dates_start = document.querySelectorAll(".date .start");
    dates_start.forEach((date_start) => {
        const parsed_date = new Date(Date.parse(date_start.innerHTML + " " + new Date().getFullYear() + " UTC"));
        date_start.innerText = parsed_date.toLocaleDateString(
            'en-us', {
                weekday: "short",
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "numeric"
            });
    });

    const dates_end = document.querySelectorAll(".date .end");
    dates_end.forEach((date_end) => {
        const parsed_date = new Date(Date.parse(date_end.innerHTML + " " + new Date().getFullYear() + " UTC"));
        date_end.innerText = parsed_date.toLocaleDateString(
            'en-us', {
                weekday: "short",
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "numeric"
            });
    });
}

// Execute the function when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', formatDatesOnLoad);
