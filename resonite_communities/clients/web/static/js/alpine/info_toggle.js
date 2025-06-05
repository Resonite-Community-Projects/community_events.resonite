document.addEventListener('alpine:init', () => {
    Alpine.data('infoToggle', () => ({
        open: false,
        init() {
            this.checkScreenSize();
            window.addEventListener('resize', () => this.checkScreenSize());
        },
        checkScreenSize() {
            if (window.screen.availWidth < 1024) {
                this.open = false; // Collapse on small screens
            } else {
                this.open = true; // Expand on large screens
            }
        },
        toggle() {
            if (window.screen.availWidth < 1024) {
                this.open = !this.open;
            }
        }
    }));
});
