require('dotenv').config();
const fetch = require('node-fetch');
const { NewCardTask } = require('../models/new-card-task.model');

class ApiRepo {
    constructor() {
        this.apiUrl = process.env.API_URL;
        this.apiToken = process.env.API_TOKEN;

        if (!this.apiUrl || !this.apiToken) {
            throw new Error('API_URL or API_TOKEN is missing from environment variables');
        }
    }

    async getExpansionNewCardsTask(game = "") {
        const url = `${this.apiUrl}/auto/task/process?game=${game}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.apiToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to get tasks: ${response.statusText}`);
        }

        const data = await response.json();

        // Handle empty response
        if (!data || Object.keys(data).length === 0) {
            return null;
        }

        return NewCardTask.fromJson(data);
    }

    async updateTask(taskId, newCards, logs = []) {
        const url = `${this.apiUrl}/auto/task/process`;
        const payload = {
            id: taskId,
            newCards: newCards,
            logs: logs
        };

        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${this.apiToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Failed to update task: ${response.statusText}`);
        }

        return await response.json();
    }
}

module.exports = ApiRepo;
