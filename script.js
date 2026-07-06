// Global state
let currentLanguage = 'he';
let allResponsa = [];
let currentResponsa = [];
let qaCategories = [];
let qaDataMode = 'legacy';

// Pagination configuration
const ITEMS_PER_PAGE = 60;
let currentPage = 1;

// Helper to sanitize summary text for Mi Yodeya entries.
function sanitizeSummary(text, titleText) {
    if (!text) return '';
    const lines = String(text).split(/\r?\n/);
    const processedLines = [];
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line === '' || /^#+\s*/.test(line)) continue;
        let cutIndex = line.length;
        const idx2 = line.indexOf('##');
        if (idx2 !== -1 && idx2 < cutIndex) cutIndex = idx2;
        const idx3 = line.indexOf('###');
        if (idx3 !== -1 && idx3 < cutIndex) cutIndex = idx3;
        if (cutIndex < line.length) line = line.substring(0, cutIndex).trim();
        if (line !== '') processedLines.push(line);
    }
    if (processedLines.length === 0) return '';
    let summary = processedLines[0];
    if (titleText) {
        const titleNorm = String(titleText).trim().toLowerCase();
        const summaryNorm = summary.toLowerCase();
        if (summaryNorm === titleNorm || summaryNorm.startsWith(titleNorm)) {
            summary = processedLines.length > 1 ? processedLines[1] : '';
        }
    }
    return summary;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadResponsa();
    updateLanguage();
});

function categoryLabel(categoryId, lang) {
    const cat = qaCategories.find(c => c.id === categoryId);
    if (!cat) return categoryId || '';
    return lang === 'he' ? (cat.label_he || cat.label_en || cat.id)
                         : (cat.label_en || cat.label_he || cat.id);
}

function normalizeQuestionIndexEntry(entry, idx) {
    const titleHe = entry.title_he || '';
    const titleEn = entry.title_en || titleHe || '';
    const summary = entry.excerpt || '';
    const category = entry.category || 'general';
    const id = entry.id || String(idx + 1);

    return {
        number: id,
        source_id: id,
        category: category,
        category_he: categoryLabel(category, 'he'),
        category_en: categoryLabel(category, 'en'),
        title_he: titleHe,
        title_en: titleEn,
        summary_he: summary,
        summary_en: summary,
        file: 'qa.html?id=' + encodeURIComponent(id),
        date: entry.year || '',
        year: entry.year || '',
        type: 'html',
        qaIndex: true,
        needs_review: !!entry.needsReview,
        tags: entry.tags || []
    };
}

// Load responsa / Q&A index data
async function loadResponsa() {
    try {
        if (window.QAData) {
            const modeInfo = await QAData.init();
            qaDataMode = modeInfo.mode;
            qaCategories = await QAData.loadCategories();

            if (qaDataMode === 'new') {
                const questionIndex = await QAData.loadQuestionIndex();
                allResponsa = questionIndex.map(normalizeQuestionIndexEntry);
                rebuildCategoryFilter();
            } else {
                const response = await fetch('responsa.json');
                allResponsa = await response.json();
                qaCategories = legacyCategoriesFromSelect();
            }
        } else {
            const response = await fetch('responsa.json');
            allResponsa = await response.json();
            qaCategories = legacyCategoriesFromSelect();
        }

        currentResponsa = allResponsa;
        populateYearFilter();
        currentPage = 1;
        displayResponsa(currentResponsa);
        updateStatistics();
    } catch (error) {
        console.error('Error loading responsa:', error);
        document.getElementById('emptyState').style.display = 'block';
    }
}

function legacyCategoriesFromSelect() {
    const select = document.getElementById('categoryFilter');
    return Array.from(select.querySelectorAll('option'))
        .filter(option => option.value !== 'all')
        .map((option, idx) => ({
            id: option.value,
            label_he: option.dataset.he || option.textContent,
            label_en: option.dataset.en || option.textContent,
            order: idx + 1
        }));
}

function rebuildCategoryFilter() {
    const categoryFilter = document.getElementById('categoryFilter');
    if (!categoryFilter || !qaCategories.length) return;

    const allText = currentLanguage === 'he' ? 'כל הקטגוריות' : 'All Categories';
    categoryFilter.innerHTML = '';
    const allOption = document.createElement('option');
    allOption.value = 'all';
    allOption.dataset.he = 'כל הקטגוריות';
    allOption.dataset.en = 'All Categories';
    allOption.textContent = allText;
    categoryFilter.appendChild(allOption);

    qaCategories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.id;
        option.dataset.he = cat.label_he || cat.id;
        option.dataset.en = cat.label_en || cat.id;
        option.textContent = currentLanguage === 'he' ? option.dataset.he : option.dataset.en;
        categoryFilter.appendChild(option);
    });
}

// Populate year filter
function populateYearFilter() {
    const yearFilter = document.getElementById('yearFilter');
    if (!yearFilter) return;
    const currentValue = yearFilter.value || 'all';
    yearFilter.innerHTML = '';
    const allOption = document.createElement('option');
    allOption.value = 'all';
    allOption.dataset.he = 'כל השנים';
    allOption.dataset.en = 'All Years';
    allOption.textContent = currentLanguage === 'he' ? 'כל השנים' : 'All Years';
    yearFilter.appendChild(allOption);

    const years = [...new Set(allResponsa.map(r => r.year).filter(Boolean))]
        .sort((a, b) => Number(b) - Number(a));

    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });

    if ([...yearFilter.options].some(o => o.value === currentValue)) {
        yearFilter.value = currentValue;
    }
}

// Display responsa cards
function displayResponsa(responsa) {
    const grid = document.getElementById('responsaGrid');
    const emptyState = document.getElementById('emptyState');

    grid.innerHTML = '';

    if (responsa.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        const paginationContainer = document.getElementById('paginationControls');
        if (paginationContainer) paginationContainer.style.display = 'none';
        return;
    }

    grid.style.display = 'grid';
    emptyState.style.display = 'none';

    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const pageItems = responsa.slice(startIndex, endIndex);

    pageItems.forEach(item => {
        const card = createResponsaCard(item);
        grid.appendChild(card);
    });

    renderPaginationControls(responsa.length);
}

// Create individual responsa card
function createResponsaCard(item) {
    const card = document.createElement('div');
    card.className = 'responsa-card';
    card.onclick = () => window.open(item.file, '_blank');

    const titleText = (currentLanguage === 'he' ? item.title_he : item.title_en) ||
                      item.title_he || item.title_en || item.number || '';

    const rawSummary = (currentLanguage === 'he' ? item.summary_he : item.summary_en) ||
                       item.summary_he || item.summary_en || '';

    let summaryText = sanitizeSummary(rawSummary, titleText);
    if (!summaryText) summaryText = rawSummary || '';

    const categoryText = (currentLanguage === 'he' ? item.category_he : item.category_en) ||
                         categoryLabel(item.category, currentLanguage);
    const readMoreText = currentLanguage === 'he' ? 'קרא עוד ←' : 'Read More →';

    const fileIcon = item.type === 'pdf' ? '📄' : '📝';
    const fileTypeLabel = item.type === 'pdf' ? 'PDF' : 'HTML';
    const dateText = item.date || '';
    const yearText = item.year || '';

    card.innerHTML = `
        <div class="card-header">
            <span class="card-number">#${item.number}</span>
            <h3 class="card-title">${titleText}</h3>
            <div class="card-meta">
                <span>📅 ${dateText}</span>
                <span>📖 ${yearText}</span>
                <span>${fileIcon} ${fileTypeLabel}</span>
            </div>
        </div>
        <div class="card-body">
            <p class="card-summary">${summaryText}</p>
            <span class="card-category">${categoryText}</span>
        </div>
        <div class="card-footer">
            <a href="${item.file}" class="card-link" onclick="event.stopPropagation()">${readMoreText}</a>
        </div>
    `;

    return card;
}

// Search functionality
async function searchResponsa() {
    const searchTerm = document.getElementById('searchInput').value;
    const categoryFilter = document.getElementById('categoryFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;

    let filtered;

    if (window.QAData && qaDataMode === 'new') {
        const opts = {};
        if (categoryFilter !== 'all') opts.category = categoryFilter;
        const result = searchTerm
            ? await QAData.search(searchTerm, opts)
            : (categoryFilter !== 'all'
                ? await QAData.getQuestionsByCategory(categoryFilter)
                : await QAData.loadQuestionIndex());
        filtered = result.map(normalizeQuestionIndexEntry);
    } else {
        filtered = allResponsa;
        const term = String(searchTerm || '').toLowerCase();

        if (term) {
            filtered = filtered.filter(item =>
                String(item.title_he || '').toLowerCase().includes(term) ||
                String(item.title_en || '').toLowerCase().includes(term) ||
                String(item.summary_he || '').toLowerCase().includes(term) ||
                String(item.summary_en || '').toLowerCase().includes(term) ||
                String(item.number || '').toLowerCase().includes(term)
            );
        }

        if (categoryFilter !== 'all') {
            filtered = filtered.filter(item => item.category === categoryFilter);
        }
    }

    if (yearFilter !== 'all') {
        filtered = filtered.filter(item => String(item.year || '') === String(yearFilter));
    }

    currentResponsa = filtered;
    currentPage = 1;
    displayResponsa(currentResponsa);
}

// Filter by category or year
function filterResponsa() {
    searchResponsa();
}

// Toggle language
async function toggleLanguage() {
    currentLanguage = currentLanguage === 'he' ? 'en' : 'he';
    document.documentElement.lang = currentLanguage;
    document.body.dir = currentLanguage === 'he' ? 'rtl' : 'ltr';
    updateLanguage();
    await searchResponsa();
}

// Update language-dependent elements
function updateLanguage() {
    const selects = document.querySelectorAll('select option');
    selects.forEach(option => {
        const text = currentLanguage === 'he' ? option.dataset.he : option.dataset.en;
        if (text) option.textContent = text;
    });

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.placeholder = currentLanguage === 'he' ? 'חיפוש...' : 'Search...';
    }
}

// Get currently filtered responsa
function getFilteredResponsa() {
    return currentResponsa;
}

// Update statistics
function updateStatistics() {
    document.getElementById('totalResponsa').textContent = allResponsa.length;
    const totalCategories = document.getElementById('totalCategories');
    if (totalCategories && qaCategories.length) totalCategories.textContent = qaCategories.length;

    if (allResponsa.length > 0) {
        const years = allResponsa.map(r => Number(r.year)).filter(Boolean);
        if (years.length) {
            document.getElementById('latestYear').textContent = Math.max(...years);
        }
    }
}

function renderPaginationControls(totalItems) {
    let paginationContainer = document.getElementById('paginationControls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'paginationControls';
        paginationContainer.className = 'pagination-controls';
        const gridParent = document.getElementById('responsaGrid').parentNode;
        gridParent.appendChild(paginationContainer);
    }

    paginationContainer.innerHTML = '';
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    const prevLabel = currentLanguage === 'he' ? 'הקודם' : 'Previous';
    const nextLabel = currentLanguage === 'he' ? 'הבא' : 'Next';

    const prevButton = document.createElement('button');
    prevButton.textContent = prevLabel;
    prevButton.disabled = currentPage === 1;
    prevButton.onclick = function(event) {
        event.preventDefault();
        if (currentPage > 1) changePage(currentPage - 1);
    };
    paginationContainer.appendChild(prevButton);

    const pageIndicator = document.createElement('span');
    pageIndicator.textContent = `${currentPage} / ${totalPages}`;
    pageIndicator.className = 'page-indicator';
    pageIndicator.style.margin = '0 1rem';
    paginationContainer.appendChild(pageIndicator);

    const nextButton = document.createElement('button');
    nextButton.textContent = nextLabel;
    nextButton.disabled = currentPage === totalPages;
    nextButton.onclick = function(event) {
        event.preventDefault();
        if (currentPage < totalPages) changePage(currentPage + 1);
    };
    paginationContainer.appendChild(nextButton);
}

function changePage(page) {
    const totalPages = Math.ceil(currentResponsa.length / ITEMS_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    displayResponsa(currentResponsa);
}
