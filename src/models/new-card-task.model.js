class Expansion {
    /**
     * @param {number} iid
     * @param {string} name
     * @param {string} game
     * @param {string[]} cards
     */
    constructor(iid, name, game, cards) {
        this.iid = iid;
        this.name = name;
        this.game = game;
        this.cards = cards;
    }
}

class NewCardTask {
    /**
     * @param {string} id
     * @param {string} name
     * @param {boolean} active
     * @param {Expansion} expansion
     * @param {any[]} newCards
     * @param {any[]} logs
     * @param {string} updatedAt
     * @param {number} runEvery
     * @param {string} nextRun
     */
    constructor(id, name, active, expansion, newCards, logs, updatedAt, runEvery, nextRun) {
        this.id = id;
        this.name = name;
        this.active = active;
        this.expansion = expansion;
        this.newCards = newCards;
        this.logs = logs;
        this.updatedAt = updatedAt;
        this.runEvery = runEvery;
        this.nextRun = nextRun;
    }

    /**
     * Creates a NewCardTask instance from a JSON object
     * @param {Object} json
     * @returns {NewCardTask}
     */
    static fromJson(json) {
        const expansion = new Expansion(
            json.expansion.iid,
            json.expansion.name,
            json.expansion.game,
            json.expansion.cards
        );

        return new NewCardTask(
            json.id,
            json.name,
            json.active,
            expansion,
            json.newCards,
            json.logs,
            json.updatedAt,
            json.runEvery,
            json.nextRun
        );
    }
}

module.exports = { NewCardTask, Expansion };
