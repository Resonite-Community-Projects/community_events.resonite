document.addEventListener('alpine:init', () => {
    Alpine.data('copyFacetUrl', () => ({
        init() {
            // Show the button if JavaScript is enabled
            document.querySelector('.js-copy-facet-url').style.display = 'block';
            document.querySelector('.nojs-copy-facet-url').style.display = 'none';
        },
        copyToClipboard(text) {
            var textArea = document.createElement("textarea");

            textArea.style.position = 'fixed';
            textArea.style.top = 0;
            textArea.style.left = 0;
            textArea.style.width = '2em';
            textArea.style.height = '2em';
            textArea.style.padding = 0;
            textArea.style.border = 'none';
            textArea.style.outline = 'none';
            textArea.style.boxShadow = 'none';
            textArea.style.background = 'transparent';

            textArea.value = text;

            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            const CopyFacetResoniteDBUrl = document.querySelector('.js-copy-facet-url');

            function resetCopyBtn(oldStatus) {
                CopyFacetResoniteDBUrl.classList.remove(oldStatus);
                CopyFacetResoniteDBUrl.classList.add('is-dark');
                CopyFacetResoniteDBUrl.querySelector('span').innerHTML = 'Copy facet folder url';
            }

            function setStatusCopyBtn(msg, status) {
                CopyFacetResoniteDBUrl.querySelector('span').innerHTML = msg;
                CopyFacetResoniteDBUrl.classList.remove('is-dark');
                CopyFacetResoniteDBUrl.classList.add(status);
                setTimeout(function () { resetCopyBtn(status); }, 3000);
            }

            try {
                var successful = document.execCommand('copy');
                setStatusCopyBtn('Successfully copied url', 'is-success');
            } catch (err) {
                setStatusCopyBtn('Error copying url', 'is-danger');
            }

            document.body.removeChild(textArea);
        }
    }));
});
