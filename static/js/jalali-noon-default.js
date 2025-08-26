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

// Gorgeous time picker for transacted_at time input (no dependencies)
(function () {
    const STYLE_ID = 'gorgeous-time-picker-style';

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
        .gtp-container{position:absolute;z-index:10000;background:#fff;border:2px solid #999;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:12px;min-width:260px;max-width:320px}
        .gtp-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;color:#111}
        .gtp-title{font-weight:700;font-size:14px}
        .gtp-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:10px}
        .gtp-hour,.gtp-minute{padding:8px 6px;border:2px solid #ddd;border-radius:8px;cursor:pointer;text-align:center;background:#f8fafc;color:#111}
        .gtp-hour:hover,.gtp-minute:hover{border-color:#3b82f6;background:#eef5ff}
        .gtp-hour.active,.gtp-minute.active{border-color:#2563eb;background:#e0ecff}
        .gtp-actions{display:flex;justify-content:space-between;gap:8px}
        .gtp-btn{flex:1;padding:8px 10px;border:2px solid #3b82f6;background:#3b82f6;color:#fff;border-radius:8px;cursor:pointer;font-weight:600}
        .gtp-btn.secondary{background:#fff;color:#1f2937;border-color:#cbd5e1}
        .gtp-btn:hover{filter:brightness(1.05)}
        `;
        document.head.appendChild(style);
    }

    function getInputs(baseName){
        const time = document.querySelector('input[name$="'+baseName+'_1"]');
        const date = document.querySelector('input[name$="'+baseName+'_0"]');
        return {time,date};
    }

    function parseHHMM(value){
        const m = /^\s*(\d{1,2}):(\d{2})\s*$/.exec(value||'');
        if(!m) return {h:12,m:0};
        let h = Math.max(0,Math.min(23,parseInt(m[1],10)));
        let mm = Math.max(0,Math.min(59,parseInt(m[2],10)));
        return {h, m:mm};
    }

    function formatHHMM(h,m){
        const hh = String(h).padStart(2,'0');
        const mm = String(m).padStart(2,'0');
        return hh+':'+mm;
    }

    function buildPicker(anchorInput){
        ensureStyles();
        const existing = document.querySelector('.gtp-container');
        if (existing) existing.remove();

        const {h:curH,m:curM} = parseHHMM(anchorInput.value);
        const container = document.createElement('div');
        container.className = 'gtp-container';

        const header = document.createElement('div');
        header.className = 'gtp-header';
        const title = document.createElement('div');
        title.className = 'gtp-title';
        title.textContent = 'Pick a Time';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'gtp-btn secondary';
        closeBtn.style.width = 'auto';
        closeBtn.textContent = 'Close';
        closeBtn.addEventListener('click', () => container.remove());
        header.appendChild(title); header.appendChild(closeBtn);

        const hoursGrid = document.createElement('div');
        hoursGrid.className = 'gtp-grid';
        let selectedHour = curH;
        for (let h=0; h<24; h++){
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'gtp-hour'+(h===curH?' active':'');
            b.textContent = String(h).padStart(2,'0');
            b.addEventListener('click', ()=>{
                hoursGrid.querySelectorAll('.gtp-hour.active').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                selectedHour = h;
            });
            hoursGrid.appendChild(b);
        }

        const minutesGrid = document.createElement('div');
        minutesGrid.className = 'gtp-grid';
        let selectedMinute = curM;
        const minuteOptions = [0,5,10,15,20,25,30,35,40,45,50,55];
        minuteOptions.forEach(m=>{
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'gtp-minute'+(m===curM?' active':'');
            b.textContent = String(m).padStart(2,'0');
            b.addEventListener('click', ()=>{
                minutesGrid.querySelectorAll('.gtp-minute.active').forEach(x=>x.classList.remove('active'));
                b.classList.add('active');
                selectedMinute = m;
            });
            minutesGrid.appendChild(b);
        });

        const actions = document.createElement('div');
        actions.className = 'gtp-actions';
        const nowBtn = document.createElement('button');
        nowBtn.type = 'button'; nowBtn.className = 'gtp-btn secondary'; nowBtn.textContent = 'Now';
        nowBtn.addEventListener('click', ()=>{
            const d = new Date();
            selectedHour = d.getHours();
            selectedMinute = d.getMinutes();
            anchorInput.value = formatHHMM(selectedHour, selectedMinute);
        });
        const setBtn = document.createElement('button');
        setBtn.type = 'button'; setBtn.className = 'gtp-btn'; setBtn.textContent = 'Set Time';
        setBtn.addEventListener('click', ()=>{
            anchorInput.value = formatHHMM(selectedHour, selectedMinute);
            anchorInput.dispatchEvent(new Event('input', {bubbles:true}));
            anchorInput.dispatchEvent(new Event('change', {bubbles:true}));
            container.remove();
        });
        actions.appendChild(nowBtn); actions.appendChild(setBtn);

        container.appendChild(header);
        const hLabel = document.createElement('div'); hLabel.textContent = 'Hours'; hLabel.style.margin = '6px 0 4px 2px'; hLabel.style.fontWeight='600'; hLabel.style.color='#111';
        container.appendChild(hLabel);
        container.appendChild(hoursGrid);
        const mLabel = document.createElement('div'); mLabel.textContent = 'Minutes'; mLabel.style.margin = '6px 0 4px 2px'; mLabel.style.fontWeight='600'; mLabel.style.color='#111';
        container.appendChild(mLabel);
        container.appendChild(minutesGrid);
        container.appendChild(actions);

        // Position below input
        const rect = anchorInput.getBoundingClientRect();
        container.style.top = (window.scrollY + rect.bottom + 6) + 'px';
        container.style.left = (window.scrollX + rect.left) + 'px';
        document.body.appendChild(container);

        const onDoc = (e)=>{ if (!container.contains(e.target)) { container.remove(); document.removeEventListener('mousedown', onDoc);} };
        setTimeout(()=> document.addEventListener('mousedown', onDoc), 0);
    }

    function attach(baseName){
        const {time} = getInputs(baseName);
        if (!time) return;
        if (time.dataset.gtpBound==='1') return;
        time.dataset.gtpBound='1';
        const pickerBtn = document.createElement('button');
        pickerBtn.type = 'button';
        pickerBtn.textContent = '⏱';
        pickerBtn.title = 'Pick time';
        pickerBtn.style.marginLeft = '6px';
        pickerBtn.style.border = '2px solid #cbd5e1';
        pickerBtn.style.background = '#fff';
        pickerBtn.style.borderRadius = '8px';
        pickerBtn.style.cursor = 'pointer';
        pickerBtn.style.padding = '4px 8px';
        pickerBtn.addEventListener('click', function(e){ e.preventDefault(); buildPicker(time); });
        time.insertAdjacentElement('afterend', pickerBtn);
        // Open on focus for convenience
        time.addEventListener('focus', function(){ buildPicker(time); });
    }

    function init(){ attach('transacted_at'); }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();


