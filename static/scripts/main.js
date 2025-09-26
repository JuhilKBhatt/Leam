// ./static/scripts/main.js

function addField() {
    const container = document.getElementById('subreddits');
    const div = document.createElement('div');
    div.className = 'subreddit-input';
    div.innerHTML = `
        <input type="text" name="subreddit[]" placeholder="e.g., gaming" required>
        <button type="button" onclick="removeField(this)">-</button>
    `;
    container.appendChild(div);
}

function removeField(button) {
    const div = button.parentNode;
    div.parentNode.removeChild(div);
}