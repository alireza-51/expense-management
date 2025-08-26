// Ensure Jalali split datetime widgets default the time part to 12:00 ONLY when empty
(function () {
    function isEmpty(val) { return !val || String(val).trim() === ''; }

    function setNoonIfNeeded(dateInput, timeInput) {
        if (!timeInput) return;
        if (isEmpty(timeInput.value)) {
            timeInput.value = '12:00';
        }
    }

    function initForField(name) {
        // Django split fields usually become <name>_0 (date) and <name>_1 (time)
        var dateInput = document.querySelector('input[name$="' + name + '_0"]');
        var timeInput = document.querySelector('input[name$="' + name + '_1"]');
        if (!dateInput || !timeInput) return;

        // On load, set to noon if empty
        setNoonIfNeeded(dateInput, timeInput);

        // When date changes, set noon if time is empty (do not override user-entered times)
        dateInput.addEventListener('change', function () {
            setNoonIfNeeded(dateInput, timeInput);
        });
    }

    function init() {
        ['transacted_at'].forEach(initForField);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();


