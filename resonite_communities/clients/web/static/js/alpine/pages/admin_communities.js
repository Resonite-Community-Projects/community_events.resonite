document.addEventListener('alpine:init', () => {
    Alpine.data('communityModal', () => ({
        isOpen: false,
        modalTitle: '',
        modalBodyContent: '',
        modalActionButtonText: '',
        saveCallback: () => {},

        openModal(title, actionButtonText, content, saveCallback) {
            this.modalTitle = title;
            this.modalBodyContent = content;
            this.modalActionButtonText = actionButtonText;
            this.saveCallback = saveCallback || (() => {});
            this.isOpen = true;
            document.documentElement.classList.add('no-scroll');
        },

        closeModal() {
            this.isOpen = false;
            document.documentElement.classList.remove('no-scroll');
            this.modalBodyContent = ''; // Clear content on close
        },

        async handleCommunityAction(action, communityId, communityType) {
            let title = '';
            let actionButton = '';
            let content = null;
            let saveFunc = null;

            const performBackendAction = async (method, body = null) => {
                try {
                    const response = await fetch(`/v2/admin/communities/${communityId || ''}`, {
                        method,
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: body ? JSON.stringify(body) : null,
                    });

                    if (!response.ok) {
                        createNotification('Community update failed', 'is-danger');
                        throw new Error(`Failed to ${action} community: ${response.statusText}`);
                    }

                    console.log(`${action} action successful`);
                    createNotification('Community update successfully', 'is-success');
                } catch (error) {
                    console.error(`Error during ${action} action:`, error);
                }
            };

            const serializeFormData = () => {
                const inputs = document.getElementById('modal-body').querySelectorAll('input, textarea, select');
                if (!inputs.length) {
                    console.error("No input, textarea, or select elements found in the modal body.");
                    return null;
                }
                const body = {};
                inputs.forEach(input => {
                    body[input.name] = input.value;
                });
                return body;
            };

            switch (action) {
                case 'add':
                    title = `Add ${communityType} community`;
                    actionButton = 'Create';
                    content = await getCommunityForm(null, communityType);
                    saveFunc = async () => {
                        const body = serializeFormData();
                        if (!body) return;
                        await performBackendAction('POST', body);
                        this.closeModal();
                    };
                    break;

                case 'edit':
                    title = `Edit ${communityType} Community`;
                    actionButton = 'Save';
                    content = await getCommunityForm(communityId, communityType);
                    saveFunc = async () => {
                        const body = serializeFormData();
                        if (!body) return;
                        await performBackendAction('PATCH', body);
                        this.closeModal();
                    };
                    break;

                case 'info':
                    title = `Community ${communityType} Info`;
                    actionButton = 'Close';
                    content = await getCommunityInfo(communityId, communityType);
                    saveFunc = () => this.closeModal();
                    break;

                case 'delete':
                    title = `Delete ${communityType} community`;
                    actionButton = 'Delete';
                    content = `<p>Are you sure you want to delete this community?</p>`;
                    saveFunc = async () => {
                        await performBackendAction('DELETE');
                    };
                    break;

                default:
                    console.error('Unknown action:', action);
                    return;
            }
            this.openModal(title, actionButton, content, saveFunc);
        }
    }));
});

// Helper functions (can remain outside Alpine.data if they don't need direct Alpine state)
async function getCommunityForm(communityId = null, communityType = null) {
    let communityData = {};
    if (communityId) {
        try {
            const response = await fetch(`/v2/admin/communities/${communityId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch community data: ${response.statusText}`);
            }
            communityData = await response.json();
        } catch (error) {
            console.error("Error fetching community data:", error);
        }
    }

    const nameValue = communityData.name || '';
    const platformIdValue = communityData.external_id || '';
    const platformValue = communityData.platform || '';
    const urlValue = communityData.url || '';
    const tagsValue = communityData.tags || '';
    const descriptionValue = communityData.description || '';
    const privateRoleIdValue = communityData.private_role_id || '';
    const privateChannelIdValue = communityData.private_channel_id || '';
    const eventsURLValue = communityData.events_url || '';

    let formOptions = '';
    let formCommunityConfiguration = '';

    if (communityType === 'event') {
        formOptions = `
        <option ${platformValue === 'Discord' ? 'selected' : ''}>Discord</option>
        <option ${platformValue === 'JSON' ? 'selected' : ''}>JSON</option>
        `
        formCommunityConfiguration = `
        <p style='font-size: 150%;'>Configuration</p>
        <div class="field">
            <label class="label">Private Role ID</label>
            <div class="control">
                <input name="private_role_id" class="input" type="text" value="${privateRoleIdValue}" placeholder="Private Role ID">
            </div>
        </div>
        <div class="field">
            <label class="label">Private Channel ID</label>
            <div class="control">
                <input name="private_channel_id" class="input" type="text" value="${privateChannelIdValue}" placeholder="Private Channel ID">
            </div>
        </div>`

        if (platformValue === 'JSON') {
            formCommunityConfiguration += `
            <div class="field">
                <label class="label">Server URL</label>
                <div class="control">
                    <input name="events_url" class="input" type="text" value="${eventsURLValue}" placeholder="Server URL">
                </div>
            </div>
            `
        }
    } else if (communityType === 'stream') {
        formOptions = `
        <option ${platformValue === 'Twitch' ? 'selected' : ''}>Twitch</option>
        `
    }

    return `
        <div class="field">
            <label class="label">Name</label>
            <div class="control">
                <input name="name" class="input" type="text" value="${nameValue}" placeholder="Community Name">
            </div>
        </div>
        <div class="field">
            <label class="label">Platform ID</label>
            <div class="control">
                <input name="external_id" class="input" type="text" value="${platformIdValue}" placeholder="Platform ID">
            </div>
        </div>
        <div class="field">
            <label class="label">Platform</label>
            <div class="control">
                <div class="select">
                    <select name="platform">
                        ${formOptions}
                    </select>
                </div>
            </div>
        </div>
        <div class="field">
            <label class="label">URL</label>
            <div class="control">
                <input name="url" class="input" type="text" value="${urlValue}" placeholder="Community URL">
            </div>
        </div>
        <div class="field">
            <label class="label">Tags</label>
            <div class="control">
                <input name="tags" class="input" type="text" value="${tagsValue}" placeholder="Tags (comma-separated)">
            </div>
            <p class="help">Tags are separated with a comma.</p>
        </div>
        <div class="field">
            <label class="label">Description</label>
            <div class="control">
                <textarea name="description" class="textarea" placeholder="Description">${descriptionValue}</textarea>
            </div>
        </div>
        ${formCommunityConfiguration}
    `;
}

async function getCommunityInfo(communityId = null, communityType = null) {
    let communityData = {};
    try {
        const response = await fetch(`/v2/admin/communities/${communityId}`);

        if (!response.ok) {
            throw new Error(`Failed to fetch community info: ${response.statusText}`);
        }

        communityData = await response.json();
    } catch (error) {
        console.error("Error fetching community info:", error);
    }

    let formCommunityConfiguration = '';

    if (communityType === 'event') {
        formCommunityConfiguration = `
        <p><strong>Private Role ID:</strong> ${communityData.private_role_id || 'N/A'}</p>
        <p><strong>Private Channel ID:</strong> ${communityData.private_channel_id || 'N/A'}</p>
        `
    } else if (communityType === 'stream') {
    }

    return `
        <p><strong>Name:</strong> ${communityData.name || 'N/A'}</p>
        <p><strong>Platform ID:</strong> ${communityData.external_id || 'N/A'}</p>
        <p><strong>Platform:</strong> ${communityData.platform || 'N/A'}</p>
        <p><strong>URL:</strong> <a href="${communityData.url || '#'}" target="_blank">${communityData.url || 'N/A'}</a></p>
        <p><strong>Tags:</strong> ${communityData.tags || 'N/A'}</p>
        <p><strong>Description:</strong> ${communityData.description || 'N/A'}</p>
        ${formCommunityConfiguration}
    `;
}
