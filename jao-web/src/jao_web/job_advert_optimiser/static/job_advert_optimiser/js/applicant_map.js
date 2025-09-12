/**
 * Render the map of applicant % by region.
 */

import chroma from 'chroma-js';

/**
 * Returns the color based on the frequency value.
 * @param {number} frequency - The frequency value (percentage).
 * @param {number} min - The minimum frequency in the dataset.
 * @param {number} max - The maximum frequency in the dataset.
 * @returns {string} - The hex color code.
 */
export function getColorForFrequency(frequency, min, max) {
    if (frequency === undefined || frequency === null || isNaN(frequency)) {
        return '#ffffff'; // No data.
    }

    // Handle edge case where min equals max
    if (min === max) {
        // Just return a middle point in the color scale
        return chroma.scale('YlGn')(0.5).hex();
    }

    // Create a chroma.js scale based on YlGn (Yellow-Green) with normalized domain
    const scale = chroma.scale('YlGn').domain([0, 1]);

    // Normalize frequency to [0, 1] range based on min and max
    const normalizedFrequency = (frequency - min) / (max - min);

    // Return the color from the scale
    return scale(normalizedFrequency).hex();
}

/**
 * Return style object for a map feature based on frequency.
 *
 * @param {number} frequency - Frequency value.
 * @param {number} min - The minimum frequency in the dataset.
 * @param {number} max - The maximum frequency in the dataset.
 * @returns {object} - Style object for Leaflet.
 */
export function getFeatureStyle(frequency, min, max) {
    const hasData = frequency !== undefined && frequency !== null && !isNaN(frequency);

    return {
        fillColor: getColorForFrequency(frequency, min, max),
        color: '#000',  // Border color
        weight: 1,
        opacity: 1,
        fillOpacity: hasData ? 0.7 : 0.2,
        dashArray: hasData ? null : '5, 5', // Dashed borders for missing data
    };
}

/**
 * Calculates an array of equally spaced grades between min and max values.
 *
 * @param {number} min - Minimum value.
 * @param {number} max - Maximum value.
 * @param {number} count - Number of grades to generate.
 * @returns {number[]} - Array of equally spaced grades.
 */
export function calculateGrades(min, max, count) {
    // This is used by the map legend, colour squares are generated between each pair
    // of numbers.
    if (min === max) {
        // Create an array with count identical values
        return Array(count).fill(Math.round(min));
    }

    const step = (max - min) / (count - 1);
    return Array.from({ length: count }, (_, i) => {
        // Round to nearest integer for cleaner display
        return Math.round(min + i * step);
    });
}

/**
 * Creates a legend control for the map.
 *
 * @param {Array} areaFrequencies - Array of {area_name, frequency} objects.
 * @returns {object} - Leaflet control object.
 */
export function createLegend(areaFrequencies) {
    const legend = L.control({ position: 'topright' });

    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'applicant-map-legend-container');

        // Extract just the frequency values
        const frequencies = areaFrequencies.map(item => item.frequency).filter(freq =>
            freq !== undefined && freq !== null && !isNaN(freq)
        );

        // Find min and max frequencies
        let min = 0;
        let max = 100;

        if (frequencies.length > 0) {
            min = Math.min(...frequencies);
            max = Math.max(...frequencies);
        }

        // Generate 7 equally spaced grades from min to max
        const grades = calculateGrades(min, max, 7);

        // Get colors for all grades except the last one
        const colors = grades.slice(0, -1).map(grade => getColorForFrequency(grade, min, max));

        // Build the legend HTML
        div.innerHTML = `
            <div class="applicant-map-legend-bar-container">
                ${grades.map((grade, i) => `
                    <div class="applicant-map-legend-bar">
                        <div class="${i === grades.length - 1 ? 'applicant-map-legend-bar-label-right' : 'applicant-map-legend-bar-label-left'}">${grade}</div>
                        ${i < grades.length - 1 ? `<div class="applicant-map-legend-color" style="background-color:${colors[i]};"></div>` : ''}
                    </div>
                `).join('')}
            </div>
            <div class="applicant-map-legend-title">Percentage of applications received for similar job descriptions by region</div>
        `;

        return div;
    };

    return legend;
}

/**
 * Creates and initializes the applicant map.
 * @param {HTMLElement} containerElement - The DOM element to contain the map.
 * @param {object} mapData - Configuration and data for the map.
 * @returns {object} - The initialized Leaflet map instance.
 */
export function renderApplicantMap(containerElement, mapData) {
    // Use leaflet to create a Map inside the supplied element
    // If the element changes size then invalidateSize() should be called on the map object.
    const map = L.map(containerElement, mapData.map_options);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Get the frequencies and calculate min/max
    const frequencies = mapData.area_frequencies
        .map(item => item.frequency)
        .filter(freq => freq !== undefined && freq !== null && !isNaN(freq));

    // Set default min/max values
    let min = 0;
    let max = 100;

    if (frequencies.length > 0) {
        min = Math.min(...frequencies);
        max = Math.max(...frequencies);
    }

    // Add the legend to the map with area frequencies data
    createLegend(mapData.area_frequencies).addTo(map);

    // Get the GeoJSON data
    const geojsonData = mapData.geojson;

    // Create lookup of area info by name
    // TODO: use area code once backend provides it
    const areaFrequencies = Object.fromEntries(
        mapData.area_frequencies.map(({ area_name, frequency }) => [area_name, frequency])
    );

    // Add each layer from the map data
    mapData.layers.forEach(layer => {
        L.geoJson(geojsonData, {
            style: function(feature) {
                const areaName = feature.properties.areanm;
                const frequency = areaFrequencies[areaName];
                return getFeatureStyle(frequency, min, max);
            },
            onEachFeature: function(feature, layer) {
                const areaName = feature.properties.areanm;
                const frequency = areaFrequencies[areaName];
                const readableFrequency = frequency ? `${frequency}%` : 'No applicants';
                const tooltipOptions = mapData.tooltip_options;
                layer.bindTooltip(
                    `<div class="map-tooltip">
                        <strong>Region:</strong> ${areaName}<br>
                        <strong>Percentage of applications:</strong> ${readableFrequency}
                    </div>`,
                    tooltipOptions
                );
            }
        }).addTo(map);
    });

    return map;
}