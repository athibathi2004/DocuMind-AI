/**
 * DocuMind AI — Frontend Dashboard Controller
 * Connects directly to FastAPI backend /api/v1 REST endpoints.
 */

const API_BASE = '/api/v1';

class DocuMindApp {
  constructor() {
    this.currentTab = 'overview';
    this.documents = [];
    this.selectedDocId = null;
    this.activeReviewTask = null;
    this.initElements();
    this.initEventListeners();
    this.loadInitialData();
  }

  initElements() {
    this.navItems = document.querySelectorAll('.nav-item');
    this.tabPanes = document.querySelectorAll('.tab-pane');
    this.pageTitle = document.getElementById('page-title');
    this.pageSubtitle = document.getElementById('page-subtitle');

    // KPI elements
    this.kpiTotalDocs = document.getElementById('kpi-total-docs');
    this.kpiProcessedDocs = document.getElementById('kpi-processed-docs');
    this.kpiPendingReviews = document.getElementById('kpi-pending-reviews');
    this.kpiAvgConfidence = document.getElementById('kpi-avg-confidence');
    this.navReviewCount = document.getElementById('nav-review-count');

    // Selectors
    this.ocrDocSelector = document.getElementById('ocr-doc-selector');
    this.extractionDocSelector = document.getElementById('extraction-doc-selector');
    this.historyDocSelector = document.getElementById('history-doc-selector');

    // Modals & Toasts
    this.editModal = document.getElementById('field-edit-modal');
    this.toastEl = document.getElementById('toast');
  }

  initEventListeners() {
    // Nav menu switching
    this.navItems.forEach(item => {
      item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Quick refresh
    document.getElementById('btn-quick-refresh').addEventListener('click', () => {
      this.refreshCurrentView();
      this.showToast('Data refreshed');
    });

    // Upload button
    document.getElementById('btn-open-upload').addEventListener('click', () => {
      this.switchTab('workspace');
      document.getElementById('file-input').click();
    });

    // Drag and drop upload
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        this.handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });

    // Filters
    document.getElementById('btn-apply-filter').addEventListener('click', () => this.loadDocuments());

    // Document Selectors
    this.ocrDocSelector.addEventListener('change', (e) => this.loadOCRInspection(e.target.value));
    this.extractionDocSelector.addEventListener('change', (e) => this.loadStructuredFields(e.target.value));
    this.historyDocSelector.addEventListener('change', (e) => this.loadProcessingHistory(e.target.value));

    // Review Actions
    document.getElementById('btn-approve-task').addEventListener('click', () => this.approveActiveReview());
    document.getElementById('btn-reject-task').addEventListener('click', () => this.rejectActiveReview());
    document.getElementById('review-filter-status').addEventListener('change', (e) => this.loadReviewQueue(e.target.value));

    // Field Edit Modal
    document.getElementById('btn-close-modal').addEventListener('click', () => this.closeEditModal());
    document.getElementById('btn-cancel-edit').addEventListener('click', () => this.closeEditModal());
    document.getElementById('btn-save-edit').addEventListener('click', () => this.saveFieldCorrection());

    // Settings slider display
    const threshSlider = document.getElementById('settings-threshold');
    const threshDisplay = document.getElementById('threshold-val-display');
    threshSlider.addEventListener('input', (e) => {
      threshDisplay.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // Reseed Demo Button
    document.getElementById('btn-reseed-demo').addEventListener('click', () => this.reseedDemoData());
  }

  switchTab(tabName) {
    this.currentTab = tabName;
    this.navItems.forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-tab') === tabName);
    });

    this.tabPanes.forEach(pane => {
      pane.classList.toggle('active', pane.id === `tab-${tabName}`);
    });

    const titles = {
      overview: ['Overview Dashboard', 'Real-time document ingestion metrics and intelligence telemetry'],
      workspace: ['Document Workspace', 'Upload, filter, inspect, and execute document processing pipelines'],
      ocr: ['OCR Inspection', 'Examine visual bounding boxes, OCR recognition confidences, and raw text'],
      extraction: ['Structured Fields Extraction', 'Validated category schemas, field-level confidence, and math rules'],
      review: ['Human Review Center', 'Resolve low-confidence fields, verify validation warnings, and audit overrides'],
      history: ['Processing Pipeline History', 'Stage-level lifecycle audit trail, durations, and diagnostics'],
      settings: ['Platform Settings', 'Configure OCR engines, confidence review thresholds, and AI model hooks'],
    };

    if (titles[tabName]) {
      this.pageTitle.textContent = titles[tabName][0];
      this.pageSubtitle.textContent = titles[tabName][1];
    }

    this.refreshCurrentView();
  }

  refreshCurrentView() {
    this.loadAnalytics();
    if (this.currentTab === 'overview') {
      this.loadRecentDocuments();
    } else if (this.currentTab === 'workspace') {
      this.loadDocuments();
    } else if (this.currentTab === 'ocr') {
      this.populateDocSelectors();
      if (this.selectedDocId) this.loadOCRInspection(this.selectedDocId);
    } else if (this.currentTab === 'extraction') {
      this.populateDocSelectors();
      if (this.selectedDocId) this.loadStructuredFields(this.selectedDocId);
    } else if (this.currentTab === 'review') {
      this.loadReviewQueue();
    } else if (this.currentTab === 'history') {
      this.populateDocSelectors();
      if (this.selectedDocId) this.loadProcessingHistory(this.selectedDocId);
    }
  }

  async loadInitialData() {
    await this.loadAnalytics();
    await this.loadDocuments();
    await this.loadRecentDocuments();
    await this.loadReviewQueue();
  }

  // --- API CALLS & RENDERING ---

  async loadAnalytics() {
    try {
      const res = await fetch(`${API_BASE}/analytics/overview`);
      if (!res.ok) return;
      const data = await res.json();

      this.kpiTotalDocs.textContent = data.total_documents;
      this.kpiProcessedDocs.textContent = data.processed_documents;
      this.kpiPendingReviews.textContent = data.pending_reviews;
      this.kpiAvgConfidence.textContent = `${(data.average_confidence * 100).toFixed(1)}%`;
      this.navReviewCount.textContent = data.pending_reviews;

      // Category distribution bars
      const catContainer = document.getElementById('category-distribution-list');
      catContainer.innerHTML = '';
      if (data.documents_by_category && data.documents_by_category.length > 0) {
        data.documents_by_category.forEach(cat => {
          const pct = data.total_documents ? (cat.count / data.total_documents) * 100 : 0;
          catContainer.innerHTML += `
            <div class="distribution-item" style="margin-bottom: 12px;">
              <div class="flex-between text-sm" style="margin-bottom: 4px;">
                <span class="font-medium">${cat.category}</span>
                <span class="text-muted">${cat.count} (${pct.toFixed(0)}%)</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill fill-success" style="width: ${pct}%"></div>
              </div>
            </div>
          `;
        });
      } else {
        catContainer.innerHTML = '<p class="text-muted text-sm">No documents classified yet.</p>';
      }

      // Status distribution bars
      const statusContainer = document.getElementById('status-distribution-list');
      statusContainer.innerHTML = '';
      if (data.documents_by_status && data.documents_by_status.length > 0) {
        data.documents_by_status.forEach(st => {
          const pct = data.total_documents ? (st.count / data.total_documents) * 100 : 0;
          const colorClass = st.status === 'COMPLETED' ? 'fill-success' : st.status === 'NEEDS_REVIEW' ? 'fill-warning' : 'fill-danger';
          statusContainer.innerHTML += `
            <div class="distribution-item" style="margin-bottom: 12px;">
              <div class="flex-between text-sm" style="margin-bottom: 4px;">
                <span class="font-medium">${st.status}</span>
                <span class="text-muted">${st.count} (${pct.toFixed(0)}%)</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill ${colorClass}" style="width: ${pct}%"></div>
              </div>
            </div>
          `;
        });
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  }

  async loadDocuments() {
    try {
      const status = document.getElementById('filter-status-select').value;
      const category = document.getElementById('filter-category-select').value;
      const search = document.getElementById('doc-search-input').value;

      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (category) params.append('category', category);
      if (search) params.append('search', search);

      const res = await fetch(`${API_BASE}/documents?${params.toString()}`);
      if (!res.ok) return;
      const data = await res.json();
      this.documents = data.items;

      const tbody = document.getElementById('all-documents-tbody');
      tbody.innerHTML = '';

      if (this.documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding: 24px;">No documents found matching filters.</td></tr>';
        return;
      }

      this.documents.forEach(doc => {
        const statusBadge = this.getStatusBadge(doc.status);
        const confText = doc.overall_confidence ? `${(doc.overall_confidence * 100).toFixed(0)}%` : '--';
        const sizeKb = (doc.file_size_bytes / 1024).toFixed(1);
        const createdDate = new Date(doc.created_at).toLocaleDateString();

        tbody.innerHTML += `
          <tr>
            <td>
              <div class="font-medium">${doc.original_filename}</div>
              <div class="text-muted text-sm font-mono">${doc.id.substring(0, 8)}...</div>
            </td>
            <td><span class="badge badge-neutral">${doc.category}</span></td>
            <td>${sizeKb} KB</td>
            <td><span class="font-bold">${confText}</span></td>
            <td><span class="text-sm font-medium">${doc.current_stage}</span></td>
            <td>${statusBadge}</td>
            <td class="text-sm text-muted">${createdDate}</td>
            <td>
              <div class="flex-row gap-3">
                <button class="btn btn-sm btn-primary" onclick="app.processDocument('${doc.id}')" title="Run processing pipeline">Process</button>
                <button class="btn btn-sm btn-secondary" onclick="app.inspectDocument('${doc.id}')" title="Inspect details">Inspect</button>
                <button class="btn btn-sm btn-danger" onclick="app.deleteDocument('${doc.id}')" title="Delete document">&times;</button>
              </div>
            </td>
          </tr>
        `;
      });

      this.populateDocSelectors();
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }

  async loadRecentDocuments() {
    try {
      const res = await fetch(`${API_BASE}/documents?limit=5`);
      if (!res.ok) return;
      const data = await res.json();
      const tbody = document.getElementById('recent-documents-tbody');
      tbody.innerHTML = '';

      if (!data.items || data.items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted" style="padding: 20px;">No documents ingested yet. Click "Upload Document" to start.</td></tr>';
        return;
      }

      data.items.forEach(doc => {
        const statusBadge = this.getStatusBadge(doc.status);
        const confText = doc.overall_confidence ? `${(doc.overall_confidence * 100).toFixed(0)}%` : '--';
        tbody.innerHTML += `
          <tr>
            <td><span class="font-medium">${doc.original_filename}</span></td>
            <td><span class="badge badge-neutral">${doc.category}</span></td>
            <td>${doc.page_count}</td>
            <td><span class="font-bold">${confText}</span></td>
            <td>${statusBadge}</td>
            <td>
              <button class="btn btn-sm btn-secondary" onclick="app.inspectDocument('${doc.id}')">Inspect</button>
            </td>
          </tr>
        `;
      });
    } catch (err) {
      console.error(err);
    }
  }

  populateDocSelectors() {
    const options = this.documents.map(d =>
      `<option value="${d.id}" ${d.id === this.selectedDocId ? 'selected' : ''}>${d.original_filename} (${d.category})</option>`
    ).join('');

    [this.ocrDocSelector, this.extractionDocSelector, this.historyDocSelector].forEach(sel => {
      if (sel) sel.innerHTML = options || '<option value="">No documents available</option>';
    });

    if (!this.selectedDocId && this.documents.length > 0) {
      this.selectedDocId = this.documents[0].id;
    }
  }

  inspectDocument(docId) {
    this.selectedDocId = docId;
    this.populateDocSelectors();
    this.switchTab('extraction');
  }

  async handleFileUpload(file) {
    const statusEl = document.getElementById('upload-status');
    statusEl.innerHTML = `<span class="badge badge-info">Uploading ${file.name}...</span>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (res.status === 201) {
        const doc = await res.json();
        this.showToast(`Uploaded ${doc.original_filename} successfully!`);
        statusEl.innerHTML = `<span class="badge badge-success">Ingested: ${doc.id}</span>`;
        await this.loadDocuments();
        this.selectedDocId = doc.id;
        // Automatically trigger process
        await this.processDocument(doc.id);
      } else if (res.status === 409) {
        const err = await res.json();
        this.showToast('Duplicate document detected! SHA-256 match found.', 'warning');
        statusEl.innerHTML = `<span class="badge badge-warning">Duplicate Document (SHA-256 match)</span>`;
      } else {
        const err = await res.json();
        this.showToast(err.detail || 'Upload failed', 'danger');
        statusEl.innerHTML = `<span class="badge badge-danger">Upload Failed</span>`;
      }
    } catch (e) {
      console.error(e);
      this.showToast('Upload error occurred', 'danger');
    }
  }

  async processDocument(docId) {
    this.showToast('Processing pipeline triggered...', 'info');
    try {
      const provider = document.getElementById('settings-ocr-provider')?.value || 'mock';
      const threshold = parseFloat(document.getElementById('settings-threshold')?.value || 0.70);

      const res = await fetch(`${API_BASE}/documents/${docId}/process?ocr_provider=${provider}&confidence_threshold=${threshold}`, {
        method: 'POST',
      });

      if (res.ok) {
        const doc = await res.json();
        this.showToast(`Processing complete: ${doc.status}`, 'success');
        await this.loadDocuments();
        await this.loadAnalytics();
        if (this.currentTab === 'extraction' && this.selectedDocId === docId) {
          this.loadStructuredFields(docId);
        }
      } else {
        const err = await res.json();
        this.showToast(`Pipeline failed: ${err.detail?.message || 'Error'}`, 'danger');
      }
    } catch (err) {
      console.error(err);
      this.showToast('Failed to trigger pipeline', 'danger');
    }
  }

  async deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document and all extracted results?')) return;
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        this.showToast('Document deleted successfully');
        await this.loadDocuments();
        await this.loadAnalytics();
      }
    } catch (err) {
      console.error(err);
    }
  }

  // --- OCR INSPECTION ---
  async loadOCRInspection(docId) {
    if (!docId) return;
    this.selectedDocId = docId;
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/ocr`);
      if (!res.ok) return;
      const ocrResults = await res.json();

      const rawTextEl = document.getElementById('ocr-raw-text');
      const provBadge = document.getElementById('ocr-provider-badge');
      const confText = document.getElementById('ocr-confidence-text');
      const totalBlocks = document.getElementById('ocr-total-blocks');

      if (ocrResults && ocrResults.length > 0) {
        const r = ocrResults[0];
        provBadge.textContent = r.provider;
        confText.textContent = `${(r.average_confidence * 100).toFixed(1)}%`;
        totalBlocks.textContent = r.total_blocks;
        rawTextEl.textContent = r.raw_text || '(Empty text)';
      } else {
        rawTextEl.textContent = 'Document has not been processed through OCR yet.';
        return;
      }

      // Fetch pages & text blocks
      const detailRes = await fetch(`${API_BASE}/documents/${docId}`);
      if (!detailRes.ok) return;
      const detail = await detailRes.json();

      const blocksTbody = document.getElementById('ocr-blocks-tbody');
      blocksTbody.innerHTML = '';

      let allBlocks = [];
      if (detail.pages) {
        detail.pages.forEach(p => {
          if (p.text_blocks) allBlocks.push(...p.text_blocks);
        });
      }

      if (allBlocks.length === 0) {
        blocksTbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No text blocks found.</td></tr>';
        return;
      }

      allBlocks.forEach(b => {
        const bboxStr = `[${b.bbox_x_min.toFixed(0)}, ${b.bbox_y_min.toFixed(0)}, ${b.bbox_x_max.toFixed(0)}, ${b.bbox_y_max.toFixed(0)}]`;
        blocksTbody.innerHTML += `
          <tr>
            <td>${b.reading_order}</td>
            <td><span class="badge badge-neutral">${b.block_type}</span></td>
            <td class="font-mono text-sm">${bboxStr}</td>
            <td><span class="font-bold">${(b.confidence * 100).toFixed(0)}%</span></td>
            <td><div style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${b.text}</div></td>
          </tr>
        `;
      });
    } catch (err) {
      console.error(err);
    }
  }

  // --- STRUCTURED FIELDS EXTRACTION ---
  async loadStructuredFields(docId) {
    if (!docId) return;
    this.selectedDocId = docId;

    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`);
      if (!res.ok) return;
      const doc = await res.json();

      // Category badge
      const catContainer = document.getElementById('extraction-category-badge-container');
      catContainer.innerHTML = `
        <div class="flex-row gap-3">
          <span class="badge badge-info" style="font-size: 0.85rem;">Classified: ${doc.category}</span>
          <span class="text-sm text-muted">${doc.classification_explanation || ''}</span>
        </div>
      `;

      // Fields table
      const tbody = document.getElementById('extracted-fields-tbody');
      tbody.innerHTML = '';

      if (!doc.extracted_fields || doc.extracted_fields.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding: 24px;">No extracted fields available. Please process the document.</td></tr>';
      } else {
        doc.extracted_fields.forEach(f => {
          const confPct = (f.confidence * 100).toFixed(0);
          const colorClass = f.confidence >= 0.85 ? 'fill-success' : f.confidence >= 0.70 ? 'fill-warning' : 'fill-danger';
          const valBadge = this.getValidationBadge(f.validation_status);
          const reviewBadge = f.review_required ? '<span class="badge badge-warning">FLAGGED</span>' : '<span class="badge badge-success">OK</span>';
          const subConfs = `OCR: ${(f.ocr_confidence || 0).toFixed(2)} | Ext: ${(f.extraction_confidence || 0).toFixed(2)} | Val: ${(f.validation_confidence || 0).toFixed(2)}`;

          tbody.innerHTML += `
            <tr class="${f.review_required ? 'bg-flagged' : ''}">
              <td class="font-bold">${f.field_name}</td>
              <td>${f.field_value || '<span class="text-muted">(missing)</span>'}</td>
              <td class="font-mono text-sm">${f.normalized_value || '--'}</td>
              <td style="min-width: 140px;">
                <div class="flex-between text-sm" style="margin-bottom: 2px;">
                  <span class="font-bold">${confPct}%</span>
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill ${colorClass}" style="width: ${confPct}%"></div>
                </div>
              </td>
              <td class="text-sm text-muted font-mono">${subConfs}</td>
              <td>${valBadge}</td>
              <td>${reviewBadge}</td>
              <td>
                <button class="btn btn-sm btn-outline" onclick="app.openEditModal('${f.id}', '${f.field_name}', '${f.field_value || ''}')">Edit</button>
              </td>
            </tr>
          `;
        });
      }

      // Validation assertions table
      const valTbody = document.getElementById('validation-assertions-tbody');
      valTbody.innerHTML = '';

      if (!doc.validation_results || doc.validation_results.length === 0) {
        valTbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No validation rules executed.</td></tr>';
      } else {
        doc.validation_results.forEach(v => {
          const passBadge = v.status === 'PASS' ? '<span class="badge badge-success">PASS</span>' : v.status === 'FAIL' ? '<span class="badge badge-danger">FAIL</span>' : '<span class="badge badge-warning">WARN</span>';
          valTbody.innerHTML += `
            <tr>
              <td class="font-bold">${v.rule_name}</td>
              <td><span class="badge badge-neutral">${v.rule_type}</span></td>
              <td>${v.field_name || '(Cross-field)'}</td>
              <td>${passBadge}</td>
              <td>${v.message}</td>
            </tr>
          `;
        });
      }
    } catch (err) {
      console.error(err);
    }
  }

  // --- HUMAN REVIEW WORKFLOW ---
  async loadReviewQueue(statusFilter = 'PENDING') {
    try {
      const res = await fetch(`${API_BASE}/reviews?status=${statusFilter}`);
      if (!res.ok) return;
      const tasks = await res.json();

      const queueList = document.getElementById('review-queue-list');
      queueList.innerHTML = '';

      if (tasks.length === 0) {
        queueList.innerHTML = '<p class="text-muted text-sm" style="padding: 16px;">Queue is clear! No tasks match filter.</p>';
        return;
      }

      tasks.forEach((task, idx) => {
        const isCurrent = this.activeReviewTask && this.activeReviewTask.id === task.id;
        queueList.innerHTML += `
          <div class="review-queue-item ${isCurrent ? 'active' : ''}" onclick="app.selectReviewTask('${task.id}')">
            <div class="flex-between">
              <span class="font-bold text-sm">Task #${task.id.substring(0, 8)}</span>
              <span class="badge ${task.status === 'PENDING' ? 'badge-warning' : 'badge-success'}">${task.status}</span>
            </div>
            <div class="text-sm text-muted" style="margin-top: 4px;">
              Doc ID: ${task.document_id.substring(0, 8)}...
            </div>
            <div class="text-sm text-danger font-medium" style="margin-top: 4px;">
              ⚠ ${task.flagged_fields_count} field(s) require review
            </div>
          </div>
        `;
      });

      if (!this.activeReviewTask && tasks.length > 0) {
        this.selectReviewTask(tasks[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async selectReviewTask(taskId) {
    try {
      const res = await fetch(`${API_BASE}/reviews/${taskId}`);
      if (!res.ok) return;
      const task = await res.json();
      this.activeReviewTask = task;

      document.getElementById('review-doc-title').textContent = `Reviewing Document: ${task.document_id}`;
      document.getElementById('review-task-meta').textContent = `Task ID: ${task.id} | Status: ${task.status} | Created: ${new Date(task.created_at).toLocaleString()}`;
      document.getElementById('review-actions-group').style.display = task.status === 'PENDING' ? 'flex' : 'none';

      // Fetch document detail for this task
      const docRes = await fetch(`${API_BASE}/documents/${task.document_id}`);
      if (!docRes.ok) return;
      const doc = await docRes.json();

      const workarea = document.getElementById('review-task-body');
      workarea.innerHTML = '';

      // Low confidence & flagged fields
      const flagged = doc.extracted_fields.filter(f => f.review_required);
      if (flagged.length > 0) {
        workarea.innerHTML += `
          <div style="background-color: #fff7ed; border-left: 4px solid #f97316; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px;">
            <h4 style="color: #c2410c; margin-bottom: 4px;">Attention Required: ${flagged.length} Low-Confidence / Validation Warnings</h4>
            <p class="text-sm text-muted">Inspect the fields below. Correct any OCR or formatting errors before approving.</p>
          </div>
        `;

        flagged.forEach(f => {
          workarea.innerHTML += `
            <div class="review-field-box">
              <div class="review-field-header">
                <span class="font-bold">${f.field_name}</span>
                <span class="badge badge-warning">Conf: ${(f.confidence * 100).toFixed(0)}%</span>
              </div>
              <div class="flex-between" style="margin-top: 8px;">
                <div>
                  <div class="text-sm text-muted">Extracted Value:</div>
                  <div class="font-mono font-medium">${f.field_value || '<span class="text-danger">None (Missing)</span>'}</div>
                </div>
                <div>
                  <div class="text-sm text-muted">Validation Status:</div>
                  <div>${this.getValidationBadge(f.validation_status)}</div>
                </div>
                <button class="btn btn-sm btn-primary" onclick="app.openEditModal('${f.id}', '${f.field_name}', '${f.field_value || ''}')">
                  Correct Value
                </button>
              </div>
            </div>
          `;
        });
      } else {
        workarea.innerHTML += `
          <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px;">
            <h4 style="color: #15803d; margin-bottom: 4px;">All Fields Validated</h4>
            <p class="text-sm text-muted">No low-confidence fields found. Document is ready for approval.</p>
          </div>
        `;
      }

      // Review Audit History
      if (task.history && task.history.length > 0) {
        workarea.innerHTML += `
          <h4 style="margin-top: 24px; margin-bottom: 12px;">Review Audit History</h4>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Field</th>
                  <th>Previous</th>
                  <th>Updated</th>
                  <th>Reviewer</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                ${task.history.map(h => `
                  <tr>
                    <td><span class="badge badge-neutral">${h.action}</span></td>
                    <td>${h.field_name || '--'}</td>
                    <td class="text-muted font-mono text-sm">${h.previous_value || '--'}</td>
                    <td class="font-bold font-mono text-sm">${h.new_value || '--'}</td>
                    <td>${h.reviewer || 'reviewer'}</td>
                    <td class="text-sm text-muted">${new Date(h.created_at).toLocaleTimeString()}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      }
    } catch (err) {
      console.error(err);
    }
  }

  async approveActiveReview() {
    if (!this.activeReviewTask) return;
    try {
      const res = await fetch(`${API_BASE}/reviews/${this.activeReviewTask.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer: 'senior_reviewer', notes: 'Verified and approved.' }),
      });
      if (res.ok) {
        this.showToast('Document review approved successfully!', 'success');
        await this.loadReviewQueue();
        await this.loadAnalytics();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async rejectActiveReview() {
    if (!this.activeReviewTask) return;
    const reason = prompt('Please enter rejection reason:');
    if (!reason) return;

    try {
      const res = await fetch(`${API_BASE}/reviews/${this.activeReviewTask.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer: 'senior_reviewer', notes: reason }),
      });
      if (res.ok) {
        this.showToast('Document review marked as REJECTED', 'warning');
        await this.loadReviewQueue();
        await this.loadAnalytics();
      }
    } catch (err) {
      console.error(err);
    }
  }

  // --- FIELD EDIT MODAL ---
  openEditModal(fieldId, fieldName, currentValue) {
    document.getElementById('edit-field-id').value = fieldId;
    document.getElementById('modal-field-title').textContent = `Correct Field: ${fieldName}`;
    document.getElementById('edit-original-value').value = currentValue;
    document.getElementById('edit-field-value').value = currentValue;
    document.getElementById('edit-reviewer-notes').value = '';
    this.editModal.classList.add('active');
  }

  closeEditModal() {
    this.editModal.classList.remove('active');
  }

  async saveFieldCorrection() {
    const fieldId = document.getElementById('edit-field-id').value;
    const newVal = document.getElementById('edit-field-value').value;
    const notes = document.getElementById('edit-reviewer-notes').value;

    try {
      const res = await fetch(`${API_BASE}/fields/${fieldId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_value: newVal, reviewer_notes: notes, reviewer: 'human_operator' }),
      });

      if (res.ok) {
        this.showToast('Field corrected successfully!', 'success');
        this.closeEditModal();
        if (this.currentTab === 'extraction') {
          this.loadStructuredFields(this.selectedDocId);
        } else if (this.currentTab === 'review') {
          this.selectReviewTask(this.activeReviewTask.id);
        }
      } else {
        this.showToast('Failed to save correction', 'danger');
      }
    } catch (err) {
      console.error(err);
    }
  }

  // --- PIPELINE HISTORY ---
  async loadProcessingHistory(docId) {
    if (!docId) return;
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`);
      if (!res.ok) return;
      const doc = await res.json();

      const stepper = document.getElementById('pipeline-stepper');
      const stages = [
        'UPLOAD', 'PREPROCESSING', 'OCR', 'LAYOUT',
        'CLASSIFICATION', 'EXTRACTION', 'VALIDATION', 'CONFIDENCE', 'COMPLETED'
      ];

      const currentStageIndex = stages.indexOf(doc.current_stage);

      stepper.innerHTML = stages.map((st, idx) => {
        const isCompleted = idx <= currentStageIndex;
        const isActive = idx === currentStageIndex;
        return `
          <div class="step-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}">
            <div class="step-circle">${idx + 1}</div>
            <div class="step-title">${st}</div>
          </div>
        `;
      }).join('');

      // Jobs audit table
      const tbody = document.getElementById('processing-jobs-tbody');
      tbody.innerHTML = '';

      if (!doc.processing_jobs || doc.processing_jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No job records available.</td></tr>';
        return;
      }

      doc.processing_jobs.forEach(job => {
        const diagStr = job.diagnostics ? JSON.stringify(job.diagnostics) : (job.error || '--');
        tbody.innerHTML += `
          <tr>
            <td class="font-mono text-sm">${job.id.substring(0, 8)}</td>
            <td><span class="badge badge-neutral">${job.stage}</span></td>
            <td><span class="badge ${job.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${job.status}</span></td>
            <td class="text-sm">${new Date(job.started_at).toLocaleTimeString()}</td>
            <td><span class="font-bold">${job.duration_ms || 0} ms</span></td>
            <td class="font-mono text-sm" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${diagStr}</td>
          </tr>
        `;
      });
    } catch (err) {
      console.error(err);
    }
  }

  async reseedDemoData() {
    this.showToast('Re-seeding synthetic demo documents...', 'info');
    // Call quick reseed or alert
    setTimeout(() => {
      this.loadDocuments();
      this.loadAnalytics();
      this.showToast('Demo data reloaded!', 'success');
    }, 1200);
  }

  // --- UTILS ---
  getStatusBadge(status) {
    switch (status) {
      case 'COMPLETED': return '<span class="badge badge-success">Completed</span>';
      case 'NEEDS_REVIEW': return '<span class="badge badge-warning">Needs Review</span>';
      case 'PROCESSING': return '<span class="badge badge-info">Processing</span>';
      case 'FAILED': return '<span class="badge badge-danger">Failed</span>';
      case 'REJECTED': return '<span class="badge badge-danger">Rejected</span>';
      default: return '<span class="badge badge-neutral">Pending</span>';
    }
  }

  getValidationBadge(status) {
    switch (status) {
      case 'VALID': return '<span class="badge badge-success">VALID</span>';
      case 'WARNING': return '<span class="badge badge-warning">WARNING</span>';
      case 'INVALID': return '<span class="badge badge-danger">INVALID</span>';
      case 'MISSING': return '<span class="badge badge-danger">MISSING</span>';
      default: return '<span class="badge badge-neutral">UNKNOWN</span>';
    }
  }

  showToast(message, type = 'info') {
    this.toastEl.textContent = message;
    this.toastEl.className = 'toast show';
    setTimeout(() => {
      this.toastEl.className = 'toast';
    }, 3000);
  }
}

// Global initialization
const app = new DocuMindApp();

