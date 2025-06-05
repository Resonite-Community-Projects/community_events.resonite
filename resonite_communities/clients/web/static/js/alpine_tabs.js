document.addEventListener('alpine:init', () => {
    Alpine.data('tabManager', () => ({
        activeTab: 'Events',
        init() {
            const path = window.location.pathname;
            if (path === '/streams') {
                this.activeTab = 'Streams';
            } else if (path === '/about') {
                this.activeTab = 'About';
            } else {
                this.activeTab = 'Events';
            }
            this.$watch('activeTab', value => {
                const url = value.toLowerCase() === 'events' ? '/' : '/' + value.toLowerCase();
                window.history.pushState(null, '', url);
            });
        }
    }));
});
