document.addEventListener('alpine:init', () => {
    Alpine.data('userStatusToggles', ({ user_id, initialSuperuser, initialModerator, isProtected }) => ({
        user_id,
        is_superuser: initialSuperuser,
        is_moderator: initialModerator,
        isProtected,

        async updateStatus() {
            try {
                const response = await fetch('/v2/admin/users/update_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: this.user_id,
                        is_superuser: this.is_superuser,
                        is_moderator: this.is_moderator,
                    })
                });

                if (response.ok) {
                    createNotification('Status updated successfully', 'is-success');
                } else {
                    createNotification(`Failed to update status: ${result.detail || 'Unknown error'}`, 'is-danger');
                }
            } catch (error) {
                console.error(error);
                createNotification('An unexpected error occurred. Please try again later.', 'is-danger');
            }
        }
    }));
});
