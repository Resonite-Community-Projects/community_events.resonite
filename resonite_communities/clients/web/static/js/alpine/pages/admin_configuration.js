document.addEventListener('alpine:init', () => {
    Alpine.data('adminConfiguration', () => ({
        domains: [],

        init() {
            if (this.$el.dataset.monitoredConfig) {
                this.domains = JSON.parse(this.$el.dataset.monitoredConfig);
            }

            document.getElementById('adminConfigForm').addEventListener('submit', async (event) => {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);

                try {
                    const response = await fetch(form.action, {
                        method: form.method,
                        body: formData,
                    });

                    if (response.ok) {
                        const result = await response.json();
                        createNotification(result.message || 'Configuration updated successfully!', 'is-success');
                    } else {
                        const errorData = await response.json();
                        createNotification(result.message || 'Failed to update configuration.', 'is-danger');
                    }
                } catch (error) {
                    createNotification('An error occurred: ' + error.message, 'is-danger');
                }
            });
        },

        addDomain() {
            this.domains.push({ id: null, url: '', status: '' });
        },

        removeDomain(index) {
            this.domains.splice(index, 1);
        }
    }));
});
