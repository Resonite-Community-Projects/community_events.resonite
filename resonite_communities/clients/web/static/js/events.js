// Event status dropdown control
document.addEventListener('DOMContentLoaded', () => {
    const dropdownTriggers = document.querySelectorAll('.dropdown-trigger')

    dropdownTriggers.forEach(trigger => {
        const dropdown = trigger.closest('.dropdown');

        // Toggle dropdown
        trigger.addEventListener('click', () => {
            dropdown.classList.toggle('is-active');
        });
    });

    // Exit dropdown
    document.addEventListener('click', (event) => {
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target)) {
                dropdown.classList.remove('is-active');
            }
        });
    });
})

// Handle event status change

document.addEventListener('DOMContentLoaded', () => {
    (document.querySelectorAll('.dropdown-item[data-status]') || []).forEach(($item) => {
        $item.addEventListener('click', async () => {
            const status = $item.dataset.status;
            const event_id =$item.dataset.event_id;

            console.log('Status selected: ', status);
            console.log('For event: ', event_id);

            const dropdown = $item.closest('.dropdown');

            dropdown.classList.remove('is-active');

            try {
                const response = await fetch('/v2/admin/events/update_status', {
                    method: 'POST',
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
                    const statusSpan = dropdown.querySelector('.dropdown-trigger span')

                    if (['CANCELED', 'ACTIVE', 'PENDING', 'READY', 'COMPLETED'].includes(result.status)) {
                        statusSpan.textContent = result.status;
                    } else {
                        console.log('Invalid status received:', result.status);
                        createNotification(`Failed to update status: Invalid status '${result.status || 'None'}'`, 'is-danger');
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
                createNotification('An unexpected error occurred. Please try again later.', 'is-danger');
            }
        });
    });
});