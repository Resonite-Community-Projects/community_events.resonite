document.addEventListener('alpine:init', () => {
    Alpine.data('communityModal', () => ({
        isOpen: false,
        modalTitle: '',
        modalBodyContent: '',
        modalActionButtonText: '',
        saveCallback: () => {},
        //activeTab: 'events',
        communities: [],

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
            this.modalBodyContent = '';
        },

        async reloadCommunityList() {
            const type = this.activeTab === 'events' ? 'event' : 'stream';

            try {
                const response = await fetch(`/v2/admin/communities/?type=${type}`);
                if (!response.ok) {
                    throw new Error(`Failed to fetch ${type} community list data: ${response.statusText}`);
                }
                const data = await response.json();
                this.communities = data;
                console.log(this.communities)
                console.log(`Reloaded ${type} community list data`);
            } catch (error) {
                console.error(`Error reloading community list:`, error);
                createNotification('Failed to reload community list', 'is-danger');
                this.communities = [];
            }
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
                    this.reloadCommunityList();
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
                    if (input.type === 'checkbox') {
                        if (!body[input.name]) body[input.name] = {};
                        body[input.name][input.value] = input.checked;
                    } else if (input.type === 'radio') {
                        if (input.checked) {
                            body[input.name] = input.value;
                        }
                    } else {
                        body[input.name] = input.value;
                    }
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

                case 'auto_add_discord':
                    title = `Select a ${communityType} community to add from Discord`;
                    actionButton = 'Create';
                    content = await getListDiscordCommunities();
                    saveFunc = async () => {
                        const body = serializeFormData();
                        if (!body) return;
                        if (!body.selectedCommunityId) {
                            createNotification('Please select a community before continuing.', 'is-warning');
                            return;
                        }

                        try {
                            const response = await fetch(`/v2/admin/setup/communities/discord/import/${body.selectedCommunityId || ''}`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({ id: body.selectedCommunityId, visibility: body.visibility })
                            });

                            if (!response.ok) {
                                throw new Error(`Import failed: ${response.statusText}`);
                            }

                            createNotification('Community successfully added from Discord.', 'is-success');
                            this.reloadCommunityList();
                        } catch (err) {
                            console.error('Import failed', err);
                            createNotification('Failed to add community from Discord.', 'is-danger');
                        }
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
                        this.closeModal();
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

async function getListDiscordCommunities() {
    let communitiesList = {};
    try {
        const response = await fetch(`/v2/admin/setup/communities/discord/`);
        if (!response.ok) {
            throw new Error(`Failed to fetch Discord community list: ${response.statusText}`);
        }
        communities = await response.json();
    } catch (error) {
        console.error("Error fetching Discord community list:", error);
        return [];
    }

    const formHTML = `
        <form id="discord-community-form" x-data="{ selected: null, visibility: 'PRIVATE' }">

            <div class="field mb-4">
                <label class="label">Visibility</label>
                <div class="buttons has-addons">
                    <label class="button" :class="{ 'is-primary': visibility === 'PUBLIC' }">
                        <input type="radio" name="visibility" value="PUBLIC" class="is-hidden" x-model="visibility">
                        PUBLIC
                    </label>
                    <label class="button" :class="{ 'is-primary': visibility === 'PRIVATE' }">
                        <input type="radio" name="visibility" value="PRIVATE" class="is-hidden" x-model="visibility">
                        PRIVATE
                    </label>
                </div>
            </div>


            <div class="">
                ${communities.map(c => `
                    <label class="box cursor-pointer" style="display: block">
                        <div class="columns is-vcentered">
                            <div class="column py-0 is-1">
                                <input type="radio" name="selectedCommunityId" value="${c.id}" class="mr-2" x-model="selected">
                            </div>
                            <div class="column py-0">
                                <div class="columns m-0">
                                    <div class="column py-0 is-one-third is-align-content-center">
                                        <img class="" src="${c.logo}" alt="Community logo">
                                    </div>
                                    <div class="column">
                                        <div class="columns m-0 is-flex-direction-column is-justify-content-space-between" style="height: 100%;">
                                            <strong>${c.name}</strong><br>
                                            <span class="has-text-grey">${c.default_description || 'No description available'}</span><br>
                                            <small><strong>ID:</strong> ${c.external_id}</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </label>
                `).join('')}
            </div>
        </form>
    `;
    return formHTML;
}

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
    const platformOnRemoteValue = communityData.platform_on_remote || '';
    const urlValue = communityData.url || '';
    const tagsValue = communityData.tags || '';
    const descriptionValue = communityData.description || '';
    const isCustomDescription = communityData.is_custom_description || '';
    const privateRoleIdValue = communityData.private_role_id || '';
    const privateChannelIdValue = communityData.private_channel_id || '';
    const eventsURLValue = communityData.events_url || '';

    let formOptions = '';
    let formCommunityConfiguration = '';

    if (communityType === 'event') {
        formOptions = `
        <option ${platformValue === 'DISCORD' ? 'selected' : ''}>Discord</option>
        <option ${platformValue === 'JSON' ? 'selected' : ''}>JSON</option>
        <option ${platformValue === 'JSON_COMMUNITY_EVENT' ? 'selected' : ''}>JSON Community Event</option>
        `

        if (platformValue === 'DISCORD' && !platformOnRemoteValue) {
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
        } else if (platformValue === 'JSON') {
            formCommunityConfiguration = `
            <div class="field">
                <label class="label">Server URL</label>
                <div class="control">
                    <input name="events_url" class="input" type="text" value="${eventsURLValue}" placeholder="Server URL">
                </div>
            </div>
            `
        } else if (platformValue === 'JSON_COMMUNITY_EVENT') {
            try {
                const local_response = await fetch(`/v2/communities`);
                if (!local_response.ok) {
                    throw new Error(`Failed to fetch community data: ${local_response.statusText}`);
                }
                local_communities = await local_response.json();
            } catch (error) {
                console.error("Error fetching community data:", error);
            }
            console.log(local_communities)
            try {
                const remote_response = await fetch(`${eventsURLValue}/v2/communities`);
                if (!remote_response.ok) {
                    throw new Error(`Failed to fetch community data: ${remote_response.statusText}`);
                }
                remote_communities = await remote_response.json();
            } catch (error) {
                console.error("Error fetching community data:", error);
            }
            formCommunityConfiguration = `
            <div class="field">
                <label class="label">Server URL</label>
                <div class="control">
                    <input name="events_url" class="input" type="text" value="${eventsURLValue}" placeholder="Server URL">
                </div>
                ${
                    eventsURLValue
                        ? `
                            <label class="label">Remote communities</label>
                            <p class="help">Select from this list all communities you want to follow.</p>
                            <div class="community-list">
                            ${remote_communities
                                .filter(c => c.configured === true && c.public === true)
                                .map(c => {
                                    const alreadyLocal = local_communities.some(lc => lc.external_id === c.external_id); // TODO: Update this code to match on external_id + platform instead
                                    return `
                                        <label class="box cursor-pointer" style="display: block; ${alreadyLocal ? 'background-color: #f5f5f5; color: #999;' : ''}">
                                            <div class="columns is-vcentered">
                                                <div class="column py-0 is-1">
                                                    <input 
                                                        type="checkbox" 
                                                        name="selected_community_external_ids" 
                                                        value="${c.id}" 
                                                        class="mr-2" 
                                                        ${alreadyLocal ? 'disabled' : ''}
                                                    >
                                                </div>
                                                <div class="column py-0">
                                                    <div class="columns m-0">
                                                        <div class="column py-0 is-one-third is-align-content-center">
                                                            <img src="${c.icon || 'https://cdn.alicorn.network/resonite-communities.com/community_discord_placeholder.png'}" alt="Community logo">
                                                        </div>
                                                        <div class="column">
                                                            <div class="columns m-0 is-flex-direction-column is-justify-content-space-between" style="height: 100%;">
                                                                <strong>${c.name}</strong><br>
                                                                <span class="has-text-grey">${c.description || 'No description available'}</span><br>
                                                                <small><strong>ID:</strong> ${c.id}</small><br>
                                                                ${alreadyLocal ? '<small class="has-text-warning">Already configured locally</small>' : ''}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </label>
                                    `;
                                }).join('')}
                            </div>
                        `
                        : ''
                }
            </div>
            `;
        }
    } else if (communityType === 'stream') {
        formOptions = `
        <option ${platformValue === 'Twitch' ? 'selected' : ''}>Twitch</option>
        `
    }

    if (isCustomDescription === true) {
        descriptionHelp = `
        <p class="help">This is the overwritten community description from Discord. You can reset the description to the default Discord description.</p>
        <fieldset>
        <div>
            <input type="checkbox" id="resetDescription" name="resetDescription" />
            <label for="resetDescription">Reset Description</label>
        </div>
        </fieldset>
        `
    } else {
        descriptionHelp = `
        <p class="help">This is the default description set from Discord, any update to this description can be reset later.</p>
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
            ${descriptionHelp}
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
