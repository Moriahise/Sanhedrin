// Global state
let currentLanguage = 'he';
let allResponsa = [];
let currentResponsa = [];
let qaCategories = [];
let qaDataMode = 'legacy';
let groupByCategory = false;

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

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
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
        renderCategoryOverview();
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

    const currentValue = categoryFilter.value || 'all';
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

    if ([...categoryFilter.options].some(option => option.value === currentValue)) {
        categoryFilter.value = currentValue;
    }
}

function getCategoryCounts(items) {
    const counts = new Map();
    items.forEach(item => {
        const id = item.category || 'general';
        counts.set(id, (counts.get(id) || 0) + 1);
    });
    return counts;
}

function setCategoryFilter(categoryId) {
    const categoryFilter = document.getElementById('categoryFilter');
    if (!categoryFilter) return;
    categoryFilter.value = categoryId || 'all';
    filterResponsa();
}

function renderCategoryOverview() {
    const overview = document.getElementById('categoryOverview');
    if (!overview || !qaCategories.length) return;

    const categoryFilter = document.getElementById('categoryFilter');
    const activeCategory = categoryFilter ? categoryFilter.value : 'all';
    const counts = getCategoryCounts(allResponsa);
    const label = currentLanguage === 'he' ? 'קטגוריות' : 'Categories';
    const hint = currentLanguage === 'he'
        ? 'סנן את השאלות לפי תחום'
        : 'Filter questions by subject';
    const allLabel = currentLanguage === 'he' ? 'הכול' : 'All';

    overview.innerHTML = `
        <div class="category-overview-header">
            <div>
                <h2>${escapeHtml(label)}</h2>
                <p>${escapeHtml(hint)}</p>
            </div>
        </div>
        <div class="category-chip-row" id="categoryChipRow"></div>
    `;

    const row = document.getElementById('categoryChipRow');
    const total = allResponsa.length;

    const addChip = (id, text, count) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'category-chip' + (activeCategory === id ? ' active' : '');
        button.setAttribute('aria-pressed', activeCategory === id ? 'true' : 'false');
        button.dataset.category = id;
        button.innerHTML = `${escapeHtml(text)} <span class="category-chip-count">${count}</span>`;
        button.onclick = () => setCategoryFilter(id);
        row.appendChild(button);
    };

    addChip('all', allLabel, total);
    qaCategories.forEach(cat => {
        const id = cat.id;
        const text = categoryLabel(id, currentLanguage);
        addChip(id, text, counts.get(id) || 0);
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

    if (groupByCategory) {
        renderGroupedCards(grid, pageItems);
    } else {
        pageItems.forEach(item => {
            const card = createResponsaCard(item);
            grid.appendChild(card);
        });
    }

    renderPaginationControls(responsa.length);
}

function renderGroupedCards(grid, items) {
    const grouped = new Map();
    items.forEach(item => {
        const category = item.category || 'general';
        if (!grouped.has(category)) grouped.set(category, []);
        grouped.get(category).push(item);
    });

    qaCategories
        .filter(cat => grouped.has(cat.id))
        .forEach(cat => {
            const groupItems = grouped.get(cat.id);
            const heading = document.createElement('div');
            heading.className = 'category-group-heading';
            heading.innerHTML = `
                <span>${escapeHtml(categoryLabel(cat.id, currentLanguage))}</span>
                <small>${groupItems.length}</small>
            `;
            grid.appendChild(heading);
            groupItems.forEach(item => grid.appendChild(createResponsaCard(item)));
        });

    // Falls Legacy-Daten eine Kategorie enthalten, die nicht in der Definition steht.
    [...grouped.keys()]
        .filter(id => !qaCategories.some(cat => cat.id === id))
        .forEach(id => {
            const groupItems = grouped.get(id);
            const heading = document.createElement('div');
            heading.className = 'category-group-heading';
            heading.innerHTML = `
                <span>${escapeHtml(categoryLabel(id, currentLanguage))}</span>
                <small>${groupItems.length}</small>
            `;
            grid.appendChild(heading);
            groupItems.forEach(item => grid.appendChild(createResponsaCard(item)));
        });
}

function cardMetaTags(item) {
    const tags = Array.isArray(item.tags) ? item.tags.filter(Boolean).slice(0, 4) : [];
    if (!tags.length) return '';
    return `<div class="card-tags">${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join('')}</div>`;
}

// Create individual responsa card
function createResponsaCard(item) {
    const card = document.createElement('div');
    card.className = 'responsa-card';
    if (item.needs_review) card.classList.add('needs-review-card');
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
    const reviewText = currentLanguage === 'he' ? 'בדיקה' : 'Review';

    const fileIcon = item.type === 'pdf' ? '📄' : '📝';
    const fileTypeLabel = item.type === 'pdf' ? 'PDF' : 'HTML';
    const dateText = item.date || '';
    const yearText = item.year || '';
    const reviewBadge = item.needs_review ? `<span class="review-badge">${reviewText}</span>` : '';

    card.innerHTML = `
        <div class="card-header">
            <span class="card-number">#${escapeHtml(item.number)}</span>
            <h3 class="card-title">${escapeHtml(titleText)}</h3>
            <div class="card-meta">
                <span>📅 ${escapeHtml(dateText)}</span>
                <span>📖 ${escapeHtml(yearText)}</span>
                <span>${fileIcon} ${fileTypeLabel}</span>
            </div>
        </div>
        <div class="card-body">
            <p class="card-summary">${escapeHtml(summaryText)}</p>
            <div class="card-category-row">
                <span class="card-category">${escapeHtml(categoryText)}</span>
                ${reviewBadge}
            </div>
            ${cardMetaTags(item)}
        </div>
        <div class="card-footer">
            <a href="${escapeHtml(item.file)}" class="card-link" onclick="event.stopPropagation()">${readMoreText}</a>
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

        let result;
        if (searchTerm) {
            // Standard: schneller Index. Fallback: Volltext nur, wenn der Index nichts findet.
            result = await QAData.search(searchTerm, opts);
            if (result.length === 0 && typeof QAData.searchDeep === 'function') {
                result = await QAData.searchDeep(searchTerm, opts);
            }
        } else {
            result = categoryFilter !== 'all'
                ? await QAData.getQuestionsByCategory(categoryFilter)
                : await QAData.loadQuestionIndex();
        }

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
                String(item.category || '').toLowerCase().includes(term) ||
                String(item.category_he || '').toLowerCase().includes(term) ||
                String(item.category_en || '').toLowerCase().includes(term) ||
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
    renderCategoryOverview();
    displayResponsa(currentResponsa);
}

// Filter by category or year
function filterResponsa() {
    searchResponsa();
}

function toggleCategoryGrouping() {
    const checkbox = document.getElementById('groupByCategory');
    groupByCategory = !!(checkbox && checkbox.checked);
    displayResponsa(currentResponsa);
}

// Toggle language
async function toggleLanguage() {
    currentLanguage = currentLanguage === 'he' ? 'en' : 'he';
    document.documentElement.lang = currentLanguage;
    document.body.dir = currentLanguage === 'he' ? 'rtl' : 'ltr';
    rebuildCategoryFilter();
    updateLanguage();
    renderCategoryOverview();
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
