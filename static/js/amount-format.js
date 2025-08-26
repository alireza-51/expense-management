// Lightweight amount input formatter with thousand separators while typing
// Applies to inputs with class "amount-input" (including Django admin forms)

(function () {
    function formatAmount(raw) {
        if (raw == null) return '';

        // Normalize digits, allow optional leading minus and single dot for decimals
        var value = String(raw).replace(/[^0-9.\-]/g, '');
        var negative = false;
        if (value.startsWith('-')) {
            negative = true;
            value = value.slice(1);
        }

        var parts = value.split('.');
        var intPart = parts[0].replace(/\D/g, '');
        var decPart = parts.length > 1 ? parts[1].replace(/\D/g, '') : '';

        // Add thousand separators to integer part
        intPart = intPart.replace(/^0+(?=\d)/, '');
        if (intPart.length === 0) intPart = '0';
        var withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

        var result = (negative ? '-' : '') + withCommas;
        if (decPart.length > 0) {
            result += '.' + decPart;
        }
        return result;
    }

    function setCaretByDigits(input, prevDigitsBeforeCaret) {
        // Place caret so that the same number of digits remain before the caret
        var val = input.value;
        var pos = 0;
        var digitsSeen = 0;
        while (pos < val.length && digitsSeen < prevDigitsBeforeCaret) {
            if (/\d/.test(val.charAt(pos))) {
                digitsSeen++;
            }
            pos++;
        }
        try {
            input.setSelectionRange(pos, pos);
        } catch (e) {
            // ignore
        }
    }

    function bindInput(el) {
        if (!el || el.dataset.amountFormatterBound === '1') return;
        el.dataset.amountFormatterBound = '1';

        el.addEventListener('input', function (e) {
            var input = e.target;
            var prev = input.value;
            var caret = input.selectionStart || 0;
            var prevDigitsBeforeCaret = (prev.slice(0, caret).match(/\d/g) || []).length;

            input.value = formatAmount(prev);
            setCaretByDigits(input, prevDigitsBeforeCaret);
        });

        el.addEventListener('blur', function (e) {
            var input = e.target;
            input.value = formatAmount(input.value);
        });

        // On form submit, strip commas so server receives a clean decimal
        var form = el.form;
        if (form && !form.dataset.amountFormatterSubmitBound) {
            form.dataset.amountFormatterSubmitBound = '1';
            form.addEventListener('submit', function () {
                var fields = form.querySelectorAll('input.amount-input');
                fields.forEach(function (f) {
                    if (typeof f.value === 'string') {
                        f.value = f.value.replace(/,/g, '');
                    }
                });
            });
        }
    }

    function init() {
        document.querySelectorAll('input.amount-input').forEach(bindInput);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();


