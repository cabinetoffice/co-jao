let ws = null;

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + window.location.host + '/ws/job_advert/';
    
    console.log('Connecting to:', wsUrl);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log('Received:', data);
        
        if (data.type === 'status') {
            showStatus(data.message);
        } else if (data.type === 'advice_chunk') {
            appendAdviceChunk(data.data);
        } else if (data.type === 'advice_complete') {
            console.log('Advice streaming complete');
            hideStatus();
        } else if (data.type === 'similar_vacancies') {
            displaySimilarVacancies(data.data);
        } else if (data.type === 'error') {
            showError(data.service || 'general', data.message);
        } else if (data.type === 'complete') {
            hideStatus();
            showTabs();
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        showError('connection', 'Connection error occurred');
    };
    
    ws.onclose = function() {
        console.log('WebSocket closed');
    };
}

function showStatus(message) {
    const statusElement = document.getElementById('loading-status');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.style.display = 'block';
    }
}

function hideStatus() {
    const statusElement = document.getElementById('loading-status');
    if (statusElement) {
        statusElement.style.display = 'none';
    }
}

function appendAdviceChunk(chunk) {
    const adviceContent = document.querySelector('.advice-content');
    if (adviceContent) {
        adviceContent.innerHTML += chunk;
    }
    
    const tabs = document.getElementById('tabs-1');
    if (tabs) {
        tabs.style.display = 'block';
    }
}

function displaySimilarVacancies(vacancies) {
    const similarTab = document.getElementById('similar-adverts');
    if (!similarTab) {
        console.error('Similar adverts tab not found');
        return;
    }
    
    const existingAccordion = document.getElementById('accordion-1');
    if (existingAccordion) {
        existingAccordion.remove();
    }
    
    const container = document.createElement('div');
    container.id = 'accordion-1';
    
    vacancies.forEach((vacancy) => {
        const section = document.createElement('div');
        section.style.borderBottom = '1px solid #b1b4b6';
        section.style.padding = '15px 0';
        
        const heading = document.createElement('h3');
        heading.style.cursor = 'pointer';
        heading.style.margin = '0';
        heading.textContent = '▶ ' + vacancy.job_title;
        
        const content = document.createElement('div');
        content.style.display = 'none';
        content.style.paddingTop = '10px';
        content.innerHTML = decodeHtml(vacancy.full_job_desc);
        
        heading.onclick = function() {
            if (content.style.display === 'none') {
                content.style.display = 'block';
                heading.textContent = '▼ ' + vacancy.job_title;
            } else {
                content.style.display = 'none';
                heading.textContent = '▶ ' + vacancy.job_title;
            }
        };
        
        section.appendChild(heading);
        section.appendChild(content);
        container.appendChild(section);
    });
    
    similarTab.appendChild(container);
}

function decodeHtml(html) {
    const txt = document.createElement('textarea');
    txt.innerHTML = html;
    let decoded = txt.value;
    decoded = decoded.replace(/\[br\/\]/g, '<br>');
    decoded = decoded.replace(/\[br\]/g, '<br>');
    return decoded;
}

function showTabs() {
    const tabsElement = document.getElementById('tabs-1');
    if (!tabsElement) return;
    
    tabsElement.style.display = 'block';
    
    // Initialize GOV.UK tabs component
    if (window.GOVUKFrontend && window.GOVUKFrontend.Tabs) {
        const tabsModule = tabsElement.querySelector('[data-module="govuk-tabs"]');
        if (tabsModule) {
            new window.GOVUKFrontend.Tabs(tabsModule).init();
        }
    }
}

function showError(service, message) {
    const container = document.querySelector('.govuk-width-container');
    if (!container) return;
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'govuk-error-summary';
    errorDiv.setAttribute('role', 'alert');
    errorDiv.innerHTML = `
        <h2 class="govuk-error-summary__title">Error in ${service}</h2>
        <div class="govuk-error-summary__body">
            <p>${message}</p>
        </div>
    `;
    container.insertBefore(errorDiv, container.firstChild);
}

function ensureWebSocketOpen() {
    return new Promise((resolve) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            resolve();
        } else {
            initWebSocket();
            ws.addEventListener('open', function() {
                resolve();
            }, { once: true });
        }
    });
}

function initializePage() {
    console.log('Initializing page');
    
    initWebSocket();
    
    // Use event delegation on document body for advice dropdown
    document.body.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'advice-option') {
            console.log('Advice option changed to:', e.target.value);
            const selectedType = e.target.value;
            const genderRatioGroup = document.getElementById('gender-ratio-group');
            const disabilityRatioGroup = document.getElementById('disability-ratio-group');
            
            if (selectedType === 'gender') {
                if (genderRatioGroup) genderRatioGroup.style.display = 'block';
                if (disabilityRatioGroup) disabilityRatioGroup.style.display = 'none';
            } else if (selectedType === 'disability') {
                if (genderRatioGroup) genderRatioGroup.style.display = 'none';
                if (disabilityRatioGroup) disabilityRatioGroup.style.display = 'block';
            } else {
                if (genderRatioGroup) genderRatioGroup.style.display = 'none';
                if (disabilityRatioGroup) disabilityRatioGroup.style.display = 'none';
            }
        }
    });
    
    // Use event delegation for slider inputs
    document.body.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'gender-ratio') {
            const genderRatioValue = document.getElementById('gender-ratio-value');
            if (genderRatioValue) {
                genderRatioValue.textContent = e.target.value;
            }
        }
        if (e.target && e.target.id === 'disability-ratio') {
            const disabilityRatioValue = document.getElementById('disability-ratio-value');
            if (disabilityRatioValue) {
                disabilityRatioValue.textContent = e.target.value;
            }
        }
    });
    
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const jobDescriptionInput = document.querySelector('[name="job_description"]');
            if (!jobDescriptionInput) return;
            
            const jobDescription = jobDescriptionInput.value;
            const sessionKey = window.sessionKey;
            
            const tabs = document.getElementById('tabs-1');
            if (tabs) tabs.style.display = 'none';
            
            const adviceContent = document.querySelector('.advice-content');
            if (adviceContent) {
                adviceContent.innerHTML = '';
            }
            
            ensureWebSocketOpen().then(() => {
                ws.send(JSON.stringify({
                    type: 'process_description',
                    job_description: jobDescription,
                    session_key: sessionKey
                }));
                showStatus('Processing job description...');
            });
        });
    }
    
    // Get Advice button - use event delegation
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.getAttribute('data-action') === 'get-advice') {
            e.preventDefault();
            
            const adviceOption = document.getElementById('advice-option');
            const genderRatioSlider = document.getElementById('gender-ratio');
            const disabilityRatioSlider = document.getElementById('disability-ratio');
            
            if (!adviceOption) return;
            
            const adviceType = adviceOption.value;
            const sessionKey = window.sessionKey;
            
            const options = {};
            if (adviceType === 'gender' && genderRatioSlider) {
                options.female_ratio = parseFloat(genderRatioSlider.value);
            } else if (adviceType === 'disability' && disabilityRatioSlider) {
                options.disability_ratio = parseFloat(disabilityRatioSlider.value);
            }
            
            const adviceContent = document.querySelector('.advice-content');
            if (adviceContent) {
                adviceContent.innerHTML = '';
            }
            
            showStatus('Getting advice...');
            
            ensureWebSocketOpen().then(() => {
                ws.send(JSON.stringify({
                    type: 'get_advice',
                    advice_type: adviceType,
                    options: options,
                    session_key: sessionKey
                }));
            });
        }
    });
    
    // Display initial similar vacancies if they exist
    if (window.initialSimilarVacancies) {
        displaySimilarVacancies(window.initialSimilarVacancies);
        showTabs();
    }
}

// Expose function globally
window.initializeJobAdvertOptimiser = initializePage;

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePage);
} else {
    setTimeout(initializePage, 0);
}
