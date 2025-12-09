// Global state
let currentLanguage = 'he';
let allResponsa = [];

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
        populateYearFilter();
        displayResponsa(allResponsa);
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
    
    grid.innerHTML = '';
    
    if (responsa.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    grid.style.display = 'grid';
    emptyState.style.display = 'none';
    
    responsa.forEach(item => {
        const card = createResponsaCard(item);
        grid.appendChild(card);
    });
}

// Create individual responsa card
function createResponsaCard(item) {
    const card = document.createElement('div');
    card.className = 'responsa-card';
    card.onclick = () => window.open(item.file, '_blank');
    
    const titleText = currentLanguage === 'he' ? item.title_he : item.title_en;
    const summaryText = currentLanguage === 'he' ? item.summary_he : item.summary_en;
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
    
    displayResponsa(filtered);
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
    displayResponsa(getFilteredResponsa());
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
