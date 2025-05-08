document.addEventListener('DOMContentLoaded', () => {

    const ModalManager = (() => {
        const modal = document.getElementById('generic-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalSaveButton = document.getElementById('modal-save-button');

        const openModal = (title, actionButtonText, content, saveCallback) => {
            modalTitle.textContent = title;
            modalBody.innerHTML = content;
            modalSaveButton.textContent = actionButtonText;
            modalSaveButton.onclick = saveCallback || (() => {});
            modal.classList.add('is-active');
        };

        const closeModal = () => {
            modal.classList.remove('is-active');
        };

        const handleCommunityAction = async (action, communityId, communityType) => {
            let modalTitle = '';
            let actionButtonText = '';
            let content = null;
            //let saveCallback = null;

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
                        throw new Error(`Failed to ${action} community: ${response.statusText}`);
                    }

                    console.log(`${action} action successful`);
                } catch (error) {
                    console.error(`Error during ${action} action:`, error);
                }
            };

            const serializeFormData = () => {
                const inputs = modalBody.querySelectorAll('input, textarea, select');
                console.log(inputs);
                if (!inputs.length) {
                    console.error("No input, textarea, or select elements found in the modal body.");
                    return null;
                }
                const body = {};
                inputs.forEach(input => {
                    console.log(input.value);
                    console.log(input.name)
                    body[input.name] = input.value;
                });
                return body;
            };


            switch (action) {
                case 'add':
                    modalTitle = `Add ${communityType} community`;
                    actionButtonText = 'Create';
                    content = await getCommunityForm(communityId, communityType);
                    /*saveCallback = async () => {
                        const formData = new FormData(modalBody.querySelector('form'));
                        const body = Object.fromEntries(formData.entries());
                        await performBackendAction('POST', body);
                        closeModal();
                    };*/
                    break;

                case 'edit':
                    modalTitle = `Edit ${communityType} Community`;
                    actionButtonText = 'Save';
                    content = await getCommunityForm(communityId, communityType);
                    /*saveCallback = async () => {
                        const formData = new FormData(modalBody.querySelector('form'));
                        const body = Object.fromEntries(formData.entries());
                        await performBackendAction('PATCH', body);
                        closeModal();
                    };*/
                    break;

                case 'info':
                    modalTitle = `Community ${communityType} Info`;
                    actionButtonText = 'Close';
                    content = await getCommunityInfo(communityId, communityType);
                    //openModal(modalTitle, actionButtonText, content, null);
                    break;

                case 'delete':
                    modalTitle = `Delete ${communityType} community`;
                    actionButtonText = 'Delete';
                    content = `<p>Are you sure you want to delete this community?</p>`;
                    /*saveCallback = async () => {
                        await performBackendAction('DELETE');
                        closeModal();
                    };*/
                    break;

                default:
                    console.error('Unknown action:', action);
                    return;
            }

            const saveCallback = async () => {
                if (action === 'delete') {
                    await performBackendAction('DELETE');
                } else if (action === 'add' || action === 'edit') {
                    const body = serializeFormData();
                    if (!body) return;

                    const method = action === 'add' ? 'POST' : 'PATCH';
                    await performBackendAction(method, body);
                }
                closeModal();
            };

            openModal(modalTitle, actionButtonText, content, saveCallback);
        };

        const initModalTriggers = () => {
            document.querySelectorAll('[data-modal-action]').forEach((trigger) => {
                trigger.addEventListener('click', async () => {
                    const action = trigger.dataset.modalAction;
                    const communityId = trigger.dataset.communityId || null;
                    const communityType = trigger.dataset.communityType || null;

                    await handleCommunityAction(action, communityId, communityType);
                });
            });

            modal.querySelector('.delete').addEventListener('click', closeModal);
            modal.querySelector('#modal-cancel-button').addEventListener('click', closeModal);
        };

        const getCommunityForm = async (communityId = null, communityType = null) => {
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
                </div>
                `
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
        };

        const getCommunityInfo = async (communityId = null, communityType = null) => {
            let communityData = {};
            try {
                const response = await fetch(`http://resonite-communities.local/v2/admin/communities/${communityId}`);

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
        };

        return { initModalTriggers };
    })();

    const TabManager = (() => {
        const switchTab = (activeTabId, inactiveTabId, activeContentId, inactiveContentId) => {
            document.getElementById(activeTabId).classList.add('is-active');
            document.getElementById(inactiveTabId).classList.remove('is-active');
            document.getElementById(activeContentId).style.display = 'table';
            document.getElementById(inactiveContentId).style.display = 'none';
        };

        const initTabSwitching = () => {
            document.getElementById('events_communities_tab').addEventListener('click', () => {
                switchTab('events_communities_tab', 'streams_communities_tab', 'events_communities', 'streams_communities');
            });

            document.getElementById('streams_communities_tab').addEventListener('click', () => {
                switchTab('streams_communities_tab', 'events_communities_tab', 'streams_communities', 'events_communities');
            });
        };

        return { initTabSwitching };
    })();

    ModalManager.initModalTriggers();
    TabManager.initTabSwitching();
});
