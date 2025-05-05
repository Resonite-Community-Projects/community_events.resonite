document.addEventListener('DOMContentLoaded', () => {

    const ModalManager = (() => {
        const modal = document.getElementById('generic-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalSaveButton = document.getElementById('modal-save-button');

        const openModal = (title, saveButtonText, content, saveCallback) => {
            modalTitle.textContent = title;
            modalBody.innerHTML = content;
            console.log(saveButtonText);
            modalSaveButton.textContent = saveButtonText;
            modalSaveButton.onclick = saveCallback || (() => {});
            modal.classList.add('is-active');
        };

        const closeModal = () => {
            modal.classList.remove('is-active');
        };

        const initModalTriggers = () => {
            document.querySelectorAll('[data-modal-action]').forEach((trigger) => {
                trigger.addEventListener('click', async () => {
                    const action = trigger.dataset.modalAction;
                    const communityId = trigger.dataset.communityId || null;
                    const communityType = trigger.dataset.communityType || null;

                    if (action === 'add') {
                        const formContent = await getCommunityForm(communityId, communityType);
                        openModal('Add ' + communityType + ' community', 'Create', formContent, () => {
                            console.log('Add action triggered');
                            closeModal();
                        });
                    } else if (action === 'edit') {
                        const formContent = await getCommunityForm(communityId, communityType);
                        openModal('Edit ' + communityType + ' Community', 'Save', formContent, () => {
                            console.log('Edit action triggered for ID:', communityId, communityType);
                            closeModal();
                        });
                    } else if (action === 'info') {
                        const infoContent = await getCommunityInfo(communityId, communityType);
                        openModal('Community ' + communityType + ' Info', 'OK', infoContent, '');
                    } else if (action === 'delete') {
                        openModal('Delete ' + communityType + ' community', 'Delete', null, () => {
                            console.log('Delete action triggered for ID:', communityId, communityType);
                            closeModal();
                        });
                    }
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
                        <input class="input" type="text" value="${privateRoleIdValue}" placeholder="Private Role ID">
                    </div>
                </div>
                <div class="field">
                    <label class="label">Private Channel ID</label>
                    <div class="control">
                        <input class="input" type="text" value="${privateChannelIdValue}" placeholder="Private Channel ID">
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
                        <input class="input" type="text" value="${nameValue}" placeholder="Community Name">
                    </div>
                </div>
                <div class="field">
                    <label class="label">Platform ID</label>
                    <div class="control">
                        <input class="input" type="text" value="${platformIdValue}" placeholder="Platform ID">
                    </div>
                </div>
                <div class="field">
                    <label class="label">Platform</label>
                    <div class="control">
                        <div class="select">
                            <select>
                                ${formOptions}
                            </select>
                        </div>
                    </div>
                </div>
                <div class="field">
                    <label class="label">URL</label>
                    <div class="control">
                        <input class="input" type="text" value="${urlValue}" placeholder="Community URL">
                    </div>
                </div>
                <div class="field">
                    <label class="label">Tags</label>
                    <div class="control">
                        <input class="input" type="text" value="${tagsValue}" placeholder="Tags (comma-separated)">
                    </div>
                    <p class="help">Tags are separated with a comma.</p>
                </div>
                <div class="field">
                    <label class="label">Description</label>
                    <div class="control">
                        <textarea class="textarea" placeholder="Description">${descriptionValue}</textarea>
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
