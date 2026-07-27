// dataFetcher.js

/**
 * Lädt die meta.json vom Server
 * @param {string} url - Pfad zur meta.json
 * @returns {Promise<Object>} Das geparste JSON-Objekt
 */
export async function fetchMetaData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP Fehler! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Fehler beim Abrufen der meta.json:", error);
        throw error;
    }
}
