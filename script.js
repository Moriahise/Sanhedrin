// Global state
let currentLanguage = 'he';
let allResponsa = [];

// Pagination configuration
// Number of cards to display on each page. Adjust this value to balance performance
// and the amount of content displayed on the screen. A lower number means fewer
// cards are rendered at once, which keeps the DOM small and the page responsive.
const ITEMS_PER_PAGE = 60;
// The currently active page (1-based index). When filters or searches change,
// this resets to 1 so the user always starts at the beginning of the result set.
let currentPage = 1;
// Holds the current filtered list of responsa. This is updated after every search
// or filter operation. Rendering functions operate on this list rather than
// recomputing the filter chain each time.
let currentResponsa = [];

// Helper to sanitize summary text for Mi Yodeya entries.
// Mi Yodeya entries sometimes include markdown headings like "# Title" or "## Frage".
// This function removes any line starting with '#' (after trimming) and also removes
// a leading line that repeats the title text. It returns a trimmed version of the
// summary for display in cards. If no suitable summary remains, it returns an empty
// string, prompting the caller to use a fallback.
function sanitizeSummary(text, titleText) {
    // Helper to sanitize summary text for Mi Yodeya entries.
    // Mi Yodeya summaries often embed markdown headings such as "# Title", "## Frage" or
    // in‑line markers like "##" or "###" within a single line. These headings add
    // unnecessary clutter to the short snippet shown on the index page. To keep
    // summaries concise and meaningful we:
    //   1. Skip any lines that are empty or start with one or more '#' characters.
    //   2. Within each remaining line, strip content after the first occurrence of '##' or '###'.
    //   3. Use only the first processed line as the summary. This typically corresponds
    //      to the question text itself. If this line repeats the title (case‑insensitive),
    //      we discard it and take the next processed line if available.
    //   4. If no suitable line is found, return an empty string and let the caller
    //      decide how to handle the absence of a summary.
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
        if (cutIndex < line.length) {
            line = line.substring(0, cutIndex).trim();
        }
        if (line === '') continue;
        processedLines.push(line);
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

// Load responsa data
async function loadResponsa() {
    try {
        const response = await fetch('responsa.json');
        allResponsa = await response.json();
        // The full dataset is the initial set of responsa
        currentResponsa = allResponsa;
        populateYearFilter();
        // Reset to page 1 and render the first page
        currentPage = 1;
        displayResponsa(currentResponsa);
        updateStatistics();
    } catch (error) {
        console.error('Error loading responsa:', error);
        // If file doesn't exist, show empty state
        document.getElementById('emptyState').style.display = 'block';
    }
}

// Populate year filter
function populateYearFilter() {
    const yearFilter = document.getElementById('yearFilter');
    const years = [...new Set(allResponsa.map(r => r.year))].sort((a, b) => b - a);
    
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
}

// Display responsa cards
function displayResponsa(responsa) {
    const grid = document.getElementById('responsaGrid');
    const emptyState = document.getElementById('emptyState');
    
    // Always clear the grid before rendering
    grid.innerHTML = '';
    
    // If no items match the current filter, show the empty state and hide pagination
    if (responsa.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        const paginationContainer = document.getElementById('paginationControls');
        if (paginationContainer) {
            paginationContainer.style.display = 'none';
        }
        return;
    }
    
    grid.style.display = 'grid';
    emptyState.style.display = 'none';
    
    // Determine which slice of items to render for the current page
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const pageItems = responsa.slice(startIndex, endIndex);
    
    pageItems.forEach(item => {
        const card = createResponsaCard(item);
        grid.appendChild(card);
    });
    
    // Render pagination controls to allow navigating between pages
    renderPaginationControls(responsa.length);
}

// Create individual responsa card
function createResponsaCard(item) {
    const card = document.createElement('div');
    card.className = 'responsa-card';
    card.onclick = () => window.open(item.file, '_blank');
    
    const titleText = currentLanguage === 'he' ? item.title_he : item.title_en;
    // Choose the appropriate summary based on language and sanitize it for display. If the sanitized
    // summary is empty (for example, if it contained only markdown headings), fall back to the
    // original summary text or an empty string.
    const rawSummary = currentLanguage === 'he' ? item.summary_he : item.summary_en;
    let summaryText = sanitizeSummary(rawSummary, titleText);
    if (!summaryText) {
        summaryText = rawSummary || '';
    }
    const categoryText = currentLanguage === 'he' ? item.category_he : item.category_en;
    const readMoreText = currentLanguage === 'he' ? 'קרא עוד ←' : 'Read More →';
    
    // Determine file type icon
    const fileIcon = item.type === 'pdf' ? '📄' : '📝';
    const fileTypeLabel = item.type === 'pdf' ? 'PDF' : 'HTML';
    
    card.innerHTML = `
        <div class="card-header">
            <span class="card-number">#${item.number}</span>
            <h3 class="card-title">${titleText}</h3>
            <div class="card-meta">
                <span>📅 ${item.date}</span>
                <span>📖 ${item.year}</span>
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
function searchResponsa() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;
    
    let filtered = allResponsa;
    
    // Apply search
    if (searchTerm) {
        filtered = filtered.filter(item => 
            item.title_he.toLowerCase().includes(searchTerm) ||
            item.title_en.toLowerCase().includes(searchTerm) ||
            item.summary_he.toLowerCase().includes(searchTerm) ||
            item.summary_en.toLowerCase().includes(searchTerm) ||
            item.number.toString().includes(searchTerm)
        );
    }
    
    // Apply category filter
    if (categoryFilter !== 'all') {
        filtered = filtered.filter(item => item.category === categoryFilter);
    }
    
    // Apply year filter
    if (yearFilter !== 'all') {
        filtered = filtered.filter(item => item.year.toString() === yearFilter);
    }
    
    // Update the global filtered responsa and reset to the first page
    currentResponsa = filtered;
    currentPage = 1;
    displayResponsa(currentResponsa);
}

// Filter by category or year
function filterResponsa() {
    searchResponsa();
}

// Toggle language
function toggleLanguage() {
    currentLanguage = currentLanguage === 'he' ? 'en' : 'he';
    document.documentElement.lang = currentLanguage;
    document.body.dir = currentLanguage === 'he' ? 'rtl' : 'ltr';
    updateLanguage();
    // Recompute the filtered list to ensure language-specific fields (e.g. title) are updated
    currentResponsa = getFilteredResponsa();
    // Maintain the current page when toggling language (do not reset to page 1)
    displayResponsa(currentResponsa);
}

// Update language-dependent elements
function updateLanguage() {
    // Update select options
    const selects = document.querySelectorAll('select option');
    selects.forEach(option => {
        const text = currentLanguage === 'he' ? option.dataset.he : option.dataset.en;
        if (text) option.textContent = text;
    });
    
    // Update placeholder
    const searchInput = document.getElementById('searchInput');
    searchInput.placeholder = currentLanguage === 'he' ? 'חיפוש...' : 'Search...';
}

// Get currently filtered responsa
function getFilteredResponsa() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;
    
    let filtered = allResponsa;
    
    if (searchTerm) {
        filtered = filtered.filter(item => 
            item.title_he.toLowerCase().includes(searchTerm) ||
            item.title_en.toLowerCase().includes(searchTerm) ||
            item.summary_he.toLowerCase().includes(searchTerm) ||
            item.summary_en.toLowerCase().includes(searchTerm)
        );
    }
    
    if (categoryFilter !== 'all') {
        filtered = filtered.filter(item => item.category === categoryFilter);
    }
    
    if (yearFilter !== 'all') {
        filtered = filtered.filter(item => item.year.toString() === yearFilter);
    }
    
    return filtered;
}

// Update statistics
function updateStatistics() {
    document.getElementById('totalResponsa').textContent = allResponsa.length;
    
    if (allResponsa.length > 0) {
        const years = allResponsa.map(r => r.year);
        const latestYear = Math.max(...years);
        document.getElementById('latestYear').textContent = latestYear;
    }
}

/**
 * Render pagination controls below the responsa grid. This function creates
 * Previous/Next buttons and a page indicator based on the total number of
 * items. Buttons are disabled when on the first or last page. The labels
 * adjust to the current language.
 *
 * @param {number} totalItems - Total number of items in the current filtered list.
 */
function renderPaginationControls(totalItems) {
    // Locate or create the pagination container
    let paginationContainer = document.getElementById('paginationControls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'paginationControls';
        paginationContainer.className = 'pagination-controls';
        // Insert after the responsa grid
        const gridParent = document.getElementById('responsaGrid').parentNode;
        gridParent.appendChild(paginationContainer);
    }
    // Clear existing controls
    paginationContainer.innerHTML = '';

    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    // If only one page is needed, hide controls
    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    paginationContainer.style.display = 'flex';

    // Determine labels based on language
    const prevLabel = currentLanguage === 'he' ? 'הקודם' : 'Previous';
    const nextLabel = currentLanguage === 'he' ? 'הבא' : 'Next';
    // Create Previous button
    const prevButton = document.createElement('button');
    prevButton.textContent = prevLabel;
    prevButton.disabled = currentPage === 1;
    prevButton.onclick = function(event) {
        event.preventDefault();
        if (currentPage > 1) {
            changePage(currentPage - 1);
        }
    };
    paginationContainer.appendChild(prevButton);
    
    // Page indicator
    const pageIndicator = document.createElement('span');
    pageIndicator.textContent = `${currentPage} / ${totalPages}`;
    pageIndicator.className = 'page-indicator';
    pageIndicator.style.margin = '0 1rem';
    paginationContainer.appendChild(pageIndicator);
    
    // Create Next button
    const nextButton = document.createElement('button');
    nextButton.textContent = nextLabel;
    nextButton.disabled = currentPage === totalPages;
    nextButton.onclick = function(event) {
        event.preventDefault();
        if (currentPage < totalPages) {
            changePage(currentPage + 1);
        }
    };
    paginationContainer.appendChild(nextButton);
}

/**
 * Change the current page and re-render the responsa grid using the previously
 * filtered list. This function ensures that the page number remains within
 * bounds and triggers a call to displayResponsa.
 *
 * @param {number} page - The new page number to display.
 */
function changePage(page) {
    const totalPages = Math.ceil(currentResponsa.length / ITEMS_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    displayResponsa(currentResponsa);
}
