document.addEventListener('alpine:init', () => {
    Alpine.data('eventsPage', () => ({
        events: [],
        selectedCommunity: '',

        init() {
            const urlParams = new URLSearchParams(window.location.search);
            const communityId = urlParams.get('community_id');
            if (communityId) {
                this.selectedCommunity = communityId;
            }
            this.loadEvents(this.selectedCommunity, false);
        },

        async loadEvents(communityId = '', changeURL = true) {
            this.selectedCommunity = communityId;
            let url = '/v2/admin/events';
            if (this.selectedCommunity) {
                url += `?community_id=${this.selectedCommunity}`;
            }

            if (changeURL) {
                let pageUrl = '/admin/events';
                if (this.selectedCommunity) {
                    pageUrl += `?community_id=${this.selectedCommunity}`;
                }
                history.replaceState({}, '', pageUrl);
            }

            try {
                const response = await fetch(url, {
                    credentials: 'include'
                });
                if (!response.ok) {
                    throw new Error(`Failed to fetch events: ${response.statusText}`);
                }
                this.events = await response.json();
                console.log('Events loaded:', this.events);
            } catch (error) {
                console.error('Error loading events:', error);
                createNotification('Failed to load events', 'is-danger');
                this.events = [];
            }
        }
    }));

    Alpine.data('eventStatusDropdown', () => ({
        async updateStatus(event_id, status) {
            console.log('Status selected: ', status);
            console.log('For event: ', event_id);

            try {
                const response = await fetch('/v2/admin/events/update_status', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: event_id,
                        status: status,
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log('Status updated successfully', result);
                    createNotification('Status update successfully', 'is-success');
                    const statusSpan = this.$refs.statusText;

                    const processedStatus = result.status ? String(result.status).trim().toUpperCase() : null;

                    if (statusSpan && processedStatus && ['CANCELED', 'ACTIVE', 'PENDING', 'READY', 'COMPLETED'].includes(processedStatus)) {
                        statusSpan.textContent = processedStatus;
                    } else {
                        console.log('Invalid status received or status span not found:', result.status);
                        createNotification(`Failed to update status: Invalid status '${result.status || 'None'}' or UI update failed`, 'is-danger');
                    }
                } else {
                    const result = await response.json();
                    console.log('Failed to update status:', result);

                    if (result.detail && Array.isArray(result.detail)) {
                        const errorMessages = result.detail.map(error => {
                            if (typeof error === 'string') {
                                return error;
                            } else if (error.msg) {
                                return error.msg;
                            } else {
                                return JSON.stringify(error);
                            }
                        });
                        createNotification(`Failed to update status:`, 'is-danger', errorMessages);
                    } else {
                        createNotification(`Failed to update status: ${result.detail || 'Unknown error'}`, 'is-danger');
                    }
                }
            } catch (error) {
                console.log(error)
                createNotification('An unexpected error occurred. Please try again later.', 'is-danger');
            }
        }
    }));
});
