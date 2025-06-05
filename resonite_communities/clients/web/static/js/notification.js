function createNotification(message, type = 'is-info', result_detail = []) {
    const notificationsContainer = document.getElementById('notifications');

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;

    const deleteButton = document.createElement('button')
    deleteButton.className = 'delete';
    deleteButton.addEventListener('click', () => {
        notification.remove();
    });

    notification.appendChild(deleteButton);

    notification.appendChild(document.createTextNode(message));

    if (result_detail && Array.isArray(result_detail)) {
        const errorList = document.createElement('ul');

        result_detail.forEach(error => {
            console.log(error)
            const listItem = document.createElement('li');
            listItem.textContent = error;
            errorList.appendChild(listItem);
        });
        notification.appendChild(errorList);
    }

    notificationsContainer.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}