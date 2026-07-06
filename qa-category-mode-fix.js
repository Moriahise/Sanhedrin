/* qa-category-mode-fix.js
 * Prevents the legacy responsa.json mode from showing misleading empty category chips.
 * New data/questions mode is unchanged: all migrated categories remain available.
 */
(function () {
    'use strict';

    function inNewQuestionMode() {
        return typeof qaDataMode !== 'undefined' && qaDataMode === 'new';
    }

    function safeEscape(value) {
        if (typeof escapeHtml === 'function') return escapeHtml(value);
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function labelFor(categoryId, lang) {
        if (typeof categoryLabel === 'function') return categoryLabel(categoryId, lang);
        const cat = qaCategories.find(c => c.id === categoryId);
        if (!cat) return categoryId || '';
        return lang === 'he' ? (cat.label_he || cat.label_en || cat.id)
                             : (cat.label_en || cat.label_he || cat.id);
    }

    function categoryCounts(items) {
        const counts = new Map();
        (items || []).forEach(item => {
            const id = item.category || 'other';
            counts.set(id, (counts.get(id) || 0) + 1);
        });
        return counts;
    }

    function visibleCategories(counts) {
        if (inNewQuestionMode()) return qaCategories || [];
        return (qaCategories || []).filter(cat => (counts.get(cat.id) || 0) > 0);
    }

    // Override the existing function from script.js.
    window.rebuildCategoryFilter = function rebuildCategoryFilter() {
        const categoryFilter = document.getElementById('categoryFilter');
        if (!categoryFilter || !qaCategories || !qaCategories.length) return;

        const counts = categoryCounts(allResponsa || []);
        const categories = visibleCategories(counts);
        const currentValue = categoryFilter.value || 'all';
        const allText = currentLanguage === 'he' ? 'כל הקטגוריות' : 'All Categories';

        categoryFilter.innerHTML = '';
        const allOption = document.createElement('option');
        allOption.value = 'all';
        allOption.dataset.he = 'כל הקטגוריות';
        allOption.dataset.en = 'All Categories';
        allOption.textContent = allText;
        categoryFilter.appendChild(allOption);

        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.dataset.he = cat.label_he || cat.id;
            option.dataset.en = cat.label_en || cat.id;
            option.textContent = currentLanguage === 'he' ? option.dataset.he : option.dataset.en;
            categoryFilter.appendChild(option);
        });

        if ([...categoryFilter.options].some(option => option.value === currentValue)) {
            categoryFilter.value = currentValue;
        } else {
            categoryFilter.value = 'all';
        }
    };

    // Override the existing function from script.js.
    window.renderCategoryOverview = function renderCategoryOverview() {
        const overview = document.getElementById('categoryOverview');
        if (!overview || !qaCategories || !qaCategories.length) return;

        const counts = categoryCounts(allResponsa || []);
        const categories = visibleCategories(counts);
        const categoryFilter = document.getElementById('categoryFilter');
        const activeCategory = categoryFilter ? categoryFilter.value : 'all';
        const label = currentLanguage === 'he' ? 'קטגוריות' : 'Categories';
        const allLabel = currentLanguage === 'he' ? 'הכול' : 'All';
        const hint = inNewQuestionMode()
            ? (currentLanguage === 'he' ? 'סנן את השאלות לפי תחום' : 'Filter questions by subject')
            : (currentLanguage === 'he'
                ? 'הנתונים הישנים עדיין אינם מסווגים לפי תחום; מוצגות רק קטגוריות עם תוכן'
                : 'Legacy data is not fully classified yet; only categories with content are shown');

        overview.innerHTML = `
            <div class="category-overview-header">
                <div>
                    <h2>${safeEscape(label)}</h2>
                    <p>${safeEscape(hint)}</p>
                </div>
            </div>
            <div class="category-chip-row" id="categoryChipRow"></div>
        `;

        const row = document.getElementById('categoryChipRow');
        const total = (allResponsa || []).length;

        const addChip = (id, text, count) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'category-chip' + (activeCategory === id ? ' active' : '');
            button.setAttribute('aria-pressed', activeCategory === id ? 'true' : 'false');
            button.dataset.category = id;
            button.innerHTML = `${safeEscape(text)} <span class="category-chip-count">${count}</span>`;
            button.onclick = () => setCategoryFilter(id);
            row.appendChild(button);
        };

        addChip('all', allLabel, total);
        categories.forEach(cat => {
            addChip(cat.id, labelFor(cat.id, currentLanguage), counts.get(cat.id) || 0);
        });
    };

    // Override the existing statistics function so the Categories card is not misleading in legacy mode.
    window.updateStatistics = function updateStatistics() {
        const total = document.getElementById('totalResponsa');
        if (total) total.textContent = allResponsa.length;

        const totalCategories = document.getElementById('totalCategories');
        if (totalCategories) {
            const counts = categoryCounts(allResponsa || []);
            totalCategories.textContent = visibleCategories(counts).length || qaCategories.length || 0;
        }

        if (allResponsa.length > 0) {
            const years = allResponsa.map(r => Number(r.year)).filter(Boolean);
            const latestYear = document.getElementById('latestYear');
            if (latestYear && years.length) latestYear.textContent = Math.max(...years);
        }
    };
})();
