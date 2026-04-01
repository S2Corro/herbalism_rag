/**
 * Herbalism RAG — Application Logic
 * SPR-006 T-003: Vanilla JavaScript SPA
 *
 * Communicates with the FastAPI backend via:
 *   POST /api/query  → QueryResponse (BLU-002 §5)
 *   GET  /api/herbs  → { herbs: string[] }
 *   GET  /api/status → { status: string, doc_count: number }
 *
 * No external libraries. No build tools. Plain ES2020+.
 */

/* ============================================================
 * DOM Element References
 * ============================================================ */

const DOM = {
  // Query form
  queryForm:        document.getElementById('query-form'),
  queryInput:       document.getElementById('query-input'),
  submitBtn:        document.getElementById('submit-btn'),
  submitBtnText:    document.getElementById('submit-btn-text'),
  queryError:       document.getElementById('query-error'),

  // Loading
  loadingSection:   document.getElementById('loading-section'),
  loadingText:      document.getElementById('loading-text'),

  // Error
  errorSection:     document.getElementById('error-section'),
  errorTitle:       document.getElementById('error-title'),
  errorDetail:      document.getElementById('error-detail'),

  // Answer
  answerSection:    document.getElementById('answer-section'),
  answerText:       document.getElementById('answer-text'),
  answerQueryTime:  document.getElementById('answer-query-time'),
  answerSourceCount:document.getElementById('answer-source-count'),

  // Sources
  sourcesSection:   document.getElementById('sources-section'),
  sourcesGrid:      document.getElementById('sources-grid'),
  sourcesCount:     document.getElementById('sources-count'),

  // Herbs
  herbsSection:     document.getElementById('herbs-section'),
  herbsGrid:        document.getElementById('herbs-grid'),

  // Status
  statusText:       document.getElementById('status-text'),
  statusIndicator:  document.getElementById('status-indicator'),
};


/* ============================================================
 * API Client
 * ============================================================ */

const API_BASE = '';   // Same origin — FastAPI serves both static and API

/**
 * POST /api/query
 * Sends the user's question and returns a QueryResponse.
 *
 * @param {string} question - The herb-related question
 * @returns {Promise<QueryResponse>}
 * @throws {Error} On network failure or non-2xx HTTP status
 */
async function submitQuery(question) {
  const response = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // Non-JSON error body — use status text
      detail = `${response.status} ${response.statusText}`;
    }
    throw new Error(detail);
  }

  return response.json();
}


/**
 * GET /api/herbs
 * Returns the list of indexed herb names.
 *
 * @returns {Promise<string[]>}
 */
async function fetchHerbs() {
  const response = await fetch(`${API_BASE}/api/herbs`);
  if (!response.ok) throw new Error(`Failed to load herbs (HTTP ${response.status})`);
  const data = await response.json();
  return Array.isArray(data.herbs) ? data.herbs : [];
}


/**
 * GET /api/status
 * Returns system health: status string and document count.
 *
 * @returns {Promise<{status: string, doc_count: number}>}
 */
async function fetchStatus() {
  const response = await fetch(`${API_BASE}/api/status`);
  if (!response.ok) throw new Error(`Status check failed (HTTP ${response.status})`);
  return response.json();
}


/* ============================================================
 * UI — Visibility Helpers
 * ============================================================ */

/**
 * Shows the loading spinner and hides answer/error/sources.
 */
function showLoading() {
  DOM.loadingSection.classList.add('visible');
  DOM.loadingSection.setAttribute('aria-hidden', 'false');

  DOM.answerSection.classList.remove('visible');
  DOM.answerSection.setAttribute('aria-hidden', 'true');

  DOM.sourcesSection.classList.remove('visible');
  DOM.sourcesSection.setAttribute('aria-hidden', 'true');

  DOM.errorSection.classList.remove('visible');
  DOM.errorSection.setAttribute('aria-hidden', 'true');

  DOM.queryError.classList.remove('visible');
}

/**
 * Hides the loading spinner.
 */
function hideLoading() {
  DOM.loadingSection.classList.remove('visible');
  DOM.loadingSection.setAttribute('aria-hidden', 'true');
}

/**
 * Disables the query form while a request is in-flight.
 */
function setFormDisabled(disabled) {
  DOM.queryInput.disabled = disabled;
  DOM.submitBtn.disabled = disabled;
  DOM.submitBtnText.textContent = disabled ? 'Searching…' : 'Search';
}


/* ============================================================
 * UI — Error Display
 * ============================================================ */

/**
 * Renders a user-friendly error message in the error section.
 *
 * @param {Error|string} error - The error to display
 */
function handleError(error) {
  hideLoading();

  const message = error instanceof Error ? error.message : String(error);

  // Network errors have a generic message — make it friendlier
  const isNetworkError =
    message.toLowerCase().includes('failed to fetch') ||
    message.toLowerCase().includes('networkerror') ||
    message.toLowerCase().includes('network request failed');

  DOM.errorTitle.textContent = isNetworkError
    ? 'Cannot reach the server'
    : 'Something went wrong';

  DOM.errorDetail.textContent = isNetworkError
    ? 'The backend is not reachable. Make sure the FastAPI server is running on this origin.'
    : message;

  DOM.errorSection.classList.add('visible');
  DOM.errorSection.setAttribute('aria-hidden', 'false');
}


/* ============================================================
 * UI — Citation Rendering
 * ============================================================ */

/**
 * Scans answer text for [N] citation markers and replaces them
 * with clickable gold badge elements that scroll to the
 * corresponding source card.
 *
 * @param {string} text - The raw answer text from the API
 * @returns {string} HTML string with citation markers replaced
 */
function replaceCitations(text) {
  // Match [1], [2], ... [N] — greedy on digits
  return text.replace(/\[(\d+)\]/g, (match, num) => {
    const index = parseInt(num, 10);
    return `<a class="citation" href="#source-card-${index}" data-source="${index}" title="Jump to source ${index}" role="button" aria-label="Citation ${index}">[${num}]</a>`;
  });
}


/**
 * Parses the answer text — converts newlines to paragraphs,
 * injects citation badges, and returns safe HTML.
 * Note: The answer text from Claude is plain text (not Markdown).
 * We do our own basic formatting; no eval() or innerHTML from user input
 * beyond the API response which is server-controlled.
 *
 * @param {string} rawAnswer - Answer string from QueryResponse
 * @returns {string} HTML string
 */
function parseAnswerToHTML(rawAnswer) {
  // Split into paragraphs on double newlines
  const paragraphs = rawAnswer
    .trim()
    .split(/\n{2,}/)
    .filter(p => p.trim().length > 0);

  return paragraphs
    .map(para => {
      // Handle single-newlines within a paragraph — keep as line breaks
      const withBreaks = para.replace(/\n/g, '<br>');
      // Replace citation markers [N] with gold badge links
      const withCitations = replaceCitations(withBreaks);
      return `<p>${withCitations}</p>`;
    })
    .join('');
}


/* ============================================================
 * UI — Answer Rendering
 * ============================================================ */

/**
 * Renders the answer section with formatted text and metadata.
 *
 * @param {QueryResponse} queryResponse - Full API response object
 */
function renderAnswer(queryResponse) {
  const { answer, sources, query_time_ms } = queryResponse;

  // Keep an empty-state fallback
  if (!answer || answer.trim().length === 0) {
    DOM.answerText.innerHTML =
      '<div class="empty-state"><div class="empty-state__icon">🔍</div><p class="empty-state__text">No answer found for your question. Try rephrasing or asking about a specific herb.</p></div>';
  } else {
    DOM.answerText.innerHTML = parseAnswerToHTML(answer);
  }

  // Meta footer: query time + source count
  const sourceCount = Array.isArray(sources) ? sources.length : 0;
  DOM.answerQueryTime.textContent = query_time_ms
    ? `⏱ ${query_time_ms}ms`
    : '';
  DOM.answerSourceCount.textContent = sourceCount
    ? `${sourceCount} source${sourceCount !== 1 ? 's' : ''}`
    : '';

  // Show the answer section with animation
  DOM.answerSection.classList.add('visible');
  DOM.answerSection.setAttribute('aria-hidden', 'false');

  // Wire up citation click handlers AFTER innerHTML is set
  attachCitationHandlers();
}


/**
 * Attaches click handlers to all citation badges inside the answer.
 * Clicking a [N] badge scrolls to and highlights source card N.
 */
function attachCitationHandlers() {
  const citations = DOM.answerText.querySelectorAll('.citation');
  citations.forEach(link => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const sourceNum = parseInt(link.dataset.source, 10);
      scrollToSource(sourceNum);
    });
  });
}


/* ============================================================
 * UI — Source Cards Rendering
 * ============================================================ */

/**
 * Returns the CSS modifier class for a given source type badge.
 *
 * @param {string} sourceType - e.g. "PubMed" | "MSK" | "WHO" | "USDA Duke"
 * @returns {string} BEM modifier class
 */
function getSourceBadgeClass(sourceType) {
  const map = {
    'pubmed':     'source-badge--pubmed',
    'msk':        'source-badge--msk',
    'who':        'source-badge--who',
    'usda duke':  'source-badge--usda',
    'usda':       'source-badge--usda',
  };
  const key = (sourceType || '').toLowerCase();
  return map[key] ?? 'source-badge--who';
}


/**
 * Builds the HTML for a single source card.
 *
 * @param {Source} source - Source object from QueryResponse.sources
 * @param {number} index  - 1-based card number (matches citation [N])
 * @returns {string} HTML string for the card
 */
function buildSourceCardHTML(source, index) {
  const badgeClass = getSourceBadgeClass(source.source_type);
  const title = escapeHTML(source.title ?? 'Untitled');
  const year   = source.year ? escapeHTML(String(source.year)) : '';
  const excerpt = source.excerpt ? escapeHTML(source.excerpt) : 'No excerpt available.';
  const url    = source.url ?? '#';
  const type   = escapeHTML(source.source_type ?? 'Source');

  return `
    <div
      class="source-card"
      id="source-card-${index}"
      role="listitem"
      aria-label="Source ${index}: ${title}"
    >
      <div class="source-card__header" role="button" tabindex="0"
           aria-expanded="false" aria-controls="source-body-${index}"
           onclick="toggleSourceCard(this)"
           onkeydown="handleSourceCardKey(event, this)">
        <span class="source-card__number" aria-hidden="true">${index}</span>
        <div class="source-card__info">
          <div class="source-card__title" title="${title}">${title}</div>
          <div class="source-card__meta">
            <span class="source-badge ${badgeClass}">${type}</span>
            ${year ? `<span>${year}</span>` : ''}
          </div>
        </div>
        <span class="source-card__toggle" aria-hidden="true">▾</span>
      </div>

      <div class="source-card__body" id="source-body-${index}" role="region"
           aria-label="Details for source ${index}">
        <blockquote class="source-card__excerpt">${excerpt}</blockquote>
        ${url && url !== '#'
          ? `<a class="source-card__link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">
               View source ↗
             </a>`
          : ''}
      </div>
    </div>
  `.trim();
}


/**
 * Renders all source cards into #sources-grid and shows the section.
 *
 * @param {Source[]} sources - Array of source objects from QueryResponse
 */
function renderSources(sources) {
  if (!Array.isArray(sources) || sources.length === 0) {
    DOM.sourcesSection.setAttribute('aria-hidden', 'true');
    return;
  }

  DOM.sourcesGrid.innerHTML = sources
    .map((source, i) => buildSourceCardHTML(source, i + 1))
    .join('');

  DOM.sourcesCount.textContent = `${sources.length} source${sources.length !== 1 ? 's' : ''}`;

  DOM.sourcesSection.classList.add('visible');
  DOM.sourcesSection.setAttribute('aria-hidden', 'false');
}


/* ============================================================
 * UI — Source Card Expand/Collapse
 * ============================================================ */

/**
 * Toggles the expand/collapse state of a source card.
 *
 * @param {HTMLElement} headerEl - The .source-card__header element
 */
function toggleSourceCard(headerEl) {
  const card = headerEl.closest('.source-card');
  const isExpanded = card.classList.contains('expanded');

  card.classList.toggle('expanded', !isExpanded);
  headerEl.setAttribute('aria-expanded', String(!isExpanded));
}

/**
 * Keyboard handler for source card headers (Enter / Space to toggle).
 *
 * @param {KeyboardEvent} event
 * @param {HTMLElement} headerEl
 */
function handleSourceCardKey(event, headerEl) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    toggleSourceCard(headerEl);
  }
}


/**
 * Scrolls to a source card and briefly highlights it (gold border flash).
 *
 * @param {number} sourceNum - 1-based source number
 */
function scrollToSource(sourceNum) {
  const card = document.getElementById(`source-card-${sourceNum}`);
  if (!card) return;

  // Expand it if collapsed
  const header = card.querySelector('.source-card__header');
  if (!card.classList.contains('expanded') && header) {
    toggleSourceCard(header);
  }

  // Scroll into view
  card.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Highlight briefly
  card.classList.add('highlighted');
  setTimeout(() => card.classList.remove('highlighted'), 2000);
}


/* ============================================================
 * UI — Herb Index
 * ============================================================ */

/**
 * GET /api/herbs — fetches the full herb list and renders clickable tags.
 * Clicking a tag pre-fills the query input with a template question.
 */
async function loadHerbs() {
  try {
    const herbs = await fetchHerbs();

    if (!herbs.length) {
      DOM.herbsGrid.innerHTML =
        '<span class="text-secondary" style="font-size:0.85rem;">No herbs indexed yet.</span>';
      DOM.herbsSection.classList.add('visible');
      return;
    }

    DOM.herbsGrid.innerHTML = herbs
      .map(herb => {
        const name = escapeHTML(herb);
        return `
          <button
            class="herb-tag"
            role="listitem"
            type="button"
            aria-label="Search for ${name}"
            onclick="prefillHerbQuery('${escapeAttr(herb)}')"
          >${name}</button>
        `.trim();
      })
      .join('');

    DOM.herbsSection.classList.add('visible');
  } catch (err) {
    // Non-critical — silently hide the herb section on error
    console.warn('[HerbIndex] Could not load herbs:', err.message);
    DOM.herbsSection.style.display = 'none';
  }
}


/**
 * Pre-fills the query input with a question template for the given herb,
 * and focuses the input so the user can refine before submitting.
 *
 * @param {string} herbName - The herb name from the index
 */
function prefillHerbQuery(herbName) {
  DOM.queryInput.value = `What are the evidence-based benefits of ${herbName}?`;
  DOM.queryInput.focus();
  // Animate focus glow
  DOM.queryInput.select();
  // Scroll to the top of the page so the user sees the input
  document.getElementById('query-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}


/* ============================================================
 * UI — Status / Health Check
 * ============================================================ */

/**
 * GET /api/status — updates the header status indicator with
 * system health and document count.
 */
async function checkStatus() {
  try {
    const { status, doc_count } = await fetchStatus();

    const isOk = status === 'ok';
    const count = typeof doc_count === 'number' ? doc_count : null;

    DOM.statusText.textContent = isOk
      ? `${count !== null ? `${count.toLocaleString()} docs` : 'Online'}`
      : 'Degraded';

    // Dot color: green = ok, amber = degraded
    const dot = DOM.statusIndicator.querySelector('.app-header__status-dot');
    if (dot) {
      dot.style.background = isOk ? 'var(--accent-primary)' : 'var(--accent-gold)';
    }
  } catch (err) {
    // Backend not reachable
    DOM.statusText.textContent = 'Offline';
    const dot = DOM.statusIndicator.querySelector('.app-header__status-dot');
    if (dot) {
      dot.style.background = '#ef4444';
      dot.style.boxShadow = 'none';
      dot.style.animation = 'none';
    }
    console.warn('[Status] Backend unreachable:', err.message);
  }
}


/* ============================================================
 * Main Query Flow
 * ============================================================ */

/**
 * Handles the full query lifecycle:
 * 1. Validates input
 * 2. Shows loading state + disables form
 * 3. Calls POST /api/query
 * 4. Renders answer + sources
 * 5. Handles errors
 *
 * @param {string} question - The question string from the input
 */
async function handleQuerySubmit(question) {
  // Input validation
  if (!question || question.trim().length === 0) {
    DOM.queryError.classList.add('visible');
    DOM.queryInput.focus();
    return;
  }

  DOM.queryError.classList.remove('visible');

  // Show loading, disable form
  showLoading();
  setFormDisabled(true);

  // Cycle through loading messages for better UX
  const loadingMessages = [
    'Searching knowledge base…',
    'Retrieving relevant excerpts…',
    'Synthesising answer…',
    'Almost there…',
  ];
  let msgIndex = 0;
  const loadingInterval = setInterval(() => {
    msgIndex = (msgIndex + 1) % loadingMessages.length;
    if (DOM.loadingText) {
      DOM.loadingText.textContent = loadingMessages[msgIndex];
    }
  }, 1800);

  try {
    const queryResponse = await submitQuery(question.trim());

    clearInterval(loadingInterval);
    hideLoading();

    // Render answer and sources
    renderAnswer(queryResponse);
    renderSources(queryResponse.sources);

  } catch (err) {
    clearInterval(loadingInterval);
    handleError(err);
    console.error('[Query] Failed:', err.message);
  } finally {
    setFormDisabled(false);
  }
}


/* ============================================================
 * Event Listeners
 * ============================================================ */

// Form submit (button click or Enter key inside input)
DOM.queryForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const question = DOM.queryInput.value;
  handleQuerySubmit(question);
});

// Clear inline validation error on input
DOM.queryInput.addEventListener('input', () => {
  if (DOM.queryError.classList.contains('visible')) {
    DOM.queryError.classList.remove('visible');
  }
});


/* ============================================================
 * Utilities
 * ============================================================ */

/**
 * Escapes HTML special characters to prevent XSS when setting innerHTML.
 *
 * @param {string} str - Raw string
 * @returns {string} HTML-safe string
 */
function escapeHTML(str) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(str).replace(/[&<>"']/g, ch => map[ch]);
}

/**
 * Escapes a string for use inside an HTML attribute value (single-quoted).
 *
 * @param {string} str - Raw string
 * @returns {string} Attribute-safe string
 */
function escapeAttr(str) {
  return String(str).replace(/'/g, "\\'");
}


/* ============================================================
 * Page Initialisation
 * ============================================================ */

/**
 * Runs on DOMContentLoaded — kicks off status check and herb index load.
 * These are fire-and-forget; failures are handled gracefully inside
 * checkStatus() and loadHerbs().
 */
async function init() {
  // Run in parallel — neither blocks the other
  await Promise.allSettled([
    checkStatus(),
    loadHerbs(),
  ]);
}

// Kick off — DOM is already ready since this script loads at end of body
init();
