// Main application logic
let currentLanguage = 'EN';
let originalData = {
    research: [],
    treatments: []
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupLanguageSelector();
});

// Setup language selector
function setupLanguageSelector() {
    const languageSelect = document.getElementById('language');
    languageSelect.addEventListener('change', async (e) => {
        currentLanguage = e.target.value;
        await translateContent();
    });
}

// Load initial data
async function loadData() {
    try {
        showLoading(true);
        hideError();

        // Fetch research and treatments in parallel
        const [researchResponse, treatmentsResponse] = await Promise.all([
            fetch('/api/news'),
            fetch('/api/treatments')
        ]);

        if (!researchResponse.ok || !treatmentsResponse.ok) {
            throw new Error('Failed to fetch data');
        }

        originalData.research = await researchResponse.json();
        originalData.treatments = await treatmentsResponse.json();

        renderResearch(originalData.research);
        renderTreatments(originalData.treatments);

        showLoading(false);
        document.getElementById('research-section').classList.remove('hidden');
        document.getElementById('treatments-section').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load data. Please try again later.');
        showLoading(false);
    }
}

// Render research articles
function renderResearch(articles) {
    const container = document.getElementById('research-container');
    container.innerHTML = '';

    articles.forEach(article => {
        const card = createResearchCard(article);
        container.appendChild(card);
    });
}

// Create research card
function createResearchCard(article) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-lg shadow-md p-6 hover:shadow-xl transition-shadow duration-300';
    card.setAttribute('data-id', article.id);

    const date = new Date(article.publication_date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    card.innerHTML = `
        <div class="flex items-start justify-between mb-3">
            <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded">${article.source}</span>
            <span class="text-xs text-gray-500">${date}</span>
        </div>
        <h3 class="text-xl font-bold text-gray-800 mb-3 article-title">${article.title}</h3>
        <p class="text-gray-600 mb-4 article-summary">${article.summary}</p>
        <div class="flex items-center justify-between">
            <div class="text-xs text-gray-500">
                <i class="fas fa-user mr-1"></i>
                ${article.authors.slice(0, 2).join(', ')}${article.authors.length > 2 ? ' et al.' : ''}
            </div>
            ${article.url ? `<a href="${article.url}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm font-semibold">
                Read more <i class="fas fa-external-link-alt ml-1"></i>
            </a>` : ''}
        </div>
    `;

    return card;
}

// Render treatments
function renderTreatments(treatments) {
    const container = document.getElementById('treatments-container');
    container.innerHTML = '';

    treatments.forEach(treatment => {
        const card = createTreatmentCard(treatment);
        container.appendChild(card);
    });
}

// Create treatment card
function createTreatmentCard(treatment) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-lg shadow-md p-6 hover:shadow-xl transition-shadow duration-300';
    card.setAttribute('data-id', treatment.id);

    const statusColors = {
        'approved': 'bg-green-100 text-green-800',
        'clinical_trial': 'bg-yellow-100 text-yellow-800',
        'research': 'bg-blue-100 text-blue-800'
    };

    const statusLabels = {
        'approved': 'FDA Approved',
        'clinical_trial': 'Clinical Trial',
        'research': 'Research Stage'
    };

    card.innerHTML = `
        <div class="flex items-start justify-between mb-3">
            <span class="text-xs font-semibold px-2 py-1 rounded ${statusColors[treatment.status]}">
                ${statusLabels[treatment.status]}
            </span>
            ${treatment.approval_date ? `<span class="text-xs text-gray-500">${new Date(treatment.approval_date).getFullYear()}</span>` : ''}
        </div>
        <h3 class="text-xl font-bold text-gray-800 mb-3 treatment-name">${treatment.name}</h3>
        <p class="text-gray-600 mb-4 treatment-description">${treatment.description}</p>
        ${treatment.url ? `<a href="${treatment.url}" target="_blank" class="text-green-600 hover:text-green-800 text-sm font-semibold">
            Learn more <i class="fas fa-external-link-alt ml-1"></i>
        </a>` : ''}
    `;

    return card;
}

// Translate content
async function translateContent() {
    if (currentLanguage === 'EN') {
        // Restore original content
        renderResearch(originalData.research);
        renderTreatments(originalData.treatments);
        return;
    }

    try {
        showLoading(true);

        // Translate research articles
        const translatedResearch = await Promise.all(
            originalData.research.map(async (article) => {
                const titleTranslation = await translateText(article.title, currentLanguage);
                const summaryTranslation = await translateText(article.summary, currentLanguage);

                return {
                    ...article,
                    title: titleTranslation,
                    summary: summaryTranslation
                };
            })
        );

        // Translate treatments
        const translatedTreatments = await Promise.all(
            originalData.treatments.map(async (treatment) => {
                const nameTranslation = await translateText(treatment.name, currentLanguage);
                const descriptionTranslation = await translateText(treatment.description, currentLanguage);

                return {
                    ...treatment,
                    name: nameTranslation,
                    description: descriptionTranslation
                };
            })
        );

        renderResearch(translatedResearch);
        renderTreatments(translatedTreatments);
        showLoading(false);
    } catch (error) {
        console.error('Translation error:', error);
        showError('Translation failed. Showing original content.');
        renderResearch(originalData.research);
        renderTreatments(originalData.treatments);
        showLoading(false);
    }
}

// Translate text using API
async function translateText(text, targetLanguage) {
    try {
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                target_language: targetLanguage
            })
        });

        if (!response.ok) {
            throw new Error('Translation request failed');
        }

        const data = await response.json();
        return data.translated_text;
    } catch (error) {
        console.error('Error translating text:', error);
        return text; // Return original text on error
    }
}

// Show/hide loading indicator
function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.style.display = show ? 'flex' : 'none';
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Hide error message
function hideError() {
    const errorDiv = document.getElementById('error');
    errorDiv.classList.add('hidden');
}
