import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Download,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  Layers,
  ShieldCheck,
  Building,
  Calendar,
  User,
  MapPin,
  Sparkles,
} from 'lucide-react';
import type { TakeoffExtractionResponse, TakeoffItem } from './types';

export default function App() {
  const [takeoffData, setTakeoffData] = useState<TakeoffExtractionResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(1);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSection, setSelectedSection] = useState<string>('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check backend health on mount
  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'healthy') {
          setBackendConnected(true);
        } else {
          setBackendConnected(false);
        }
      })
      .catch(() => {
        setBackendConnected(false);
      });
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Upload and process PDF file
  const processPdfFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please select a valid PDF document (.pdf).');
      return;
    }

    setErrorMessage(null);
    setIsProcessing(true);
    setProcessingStep(1);

    const stepInterval = setInterval(() => {
      setProcessingStep((prev) => (prev < 3 ? prev + 1 : prev));
    }, 1200);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/takeoff/extract', {
        method: 'POST',
        body: formData,
      });

      clearInterval(stepInterval);

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const detailMsg = errorData?.detail?.message || `Extraction failed with HTTP ${response.status}`;
        throw new Error(detailMsg);
      }

      const data: TakeoffExtractionResponse = await response.json();
      setTakeoffData(data);
      showToast(`Takeoff extracted successfully: ${data.all_items.length} items found.`);
    } catch (err: any) {
      clearInterval(stepInterval);
      setErrorMessage(err.message || 'An unexpected error occurred during takeoff extraction.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processPdfFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processPdfFile(e.target.files[0]);
    }
  };

  // Download Excel
  const handleDownloadExcel = async () => {
    if (!takeoffData) return;

    try {
      const timestamp = Date.now();

      const res = await fetch(
        `/api/takeoff/export/excel?t=${timestamp}`,
        {
          method: 'POST',
          cache: 'no-store',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            Pragma: 'no-cache',
          },
          body: JSON.stringify(takeoffData),
        }
      );

      if (!res.ok) {
        throw new Error('Excel generation failed on server');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = `${(
        takeoffData.project_metadata.project_name || 'takeoff'
      ).replace(/[^a-zA-Z0-9_-]/g, '_')}_takeoff.xlsx`;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      showToast('Excel workbook downloaded successfully!');
    } catch (err: any) {
      setErrorMessage(`Excel export failed: ${err.message}`);
    }
  };

  // Download CSV
  const handleDownloadCsv = async () => {
    if (!takeoffData) return;

    try {
      const timestamp = Date.now();

      const res = await fetch(
        `/api/takeoff/export/csv?t=${timestamp}`,
        {
          method: 'POST',
          cache: 'no-store',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            Pragma: 'no-cache',
          },
          body: JSON.stringify(takeoffData),
        }
      );

      if (!res.ok) {
        throw new Error('CSV generation failed on server');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = `${(
        takeoffData.project_metadata.project_name || 'takeoff'
      ).replace(/[^a-zA-Z0-9_-]/g, '_')}_takeoff.csv`;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      showToast('CSV schedule downloaded successfully!');
    } catch (err: any) {
      setErrorMessage(`CSV export failed: ${err.message}`);
    }
  };

  // Filter items for main table
  const filteredItems = takeoffData
    ? takeoffData.all_items.filter((item) => {
      const matchesSearch =
        item.original_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.item_number && item.item_number.toString().includes(searchTerm)) ||
        (item.unit && item.unit.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesSection = selectedSection === 'all' || item.section === selectedSection;

      return matchesSearch && matchesSection;
    })
    : [];

  return (
    <div className="app-container">
      {/* Toast Notice */}
      {toastMessage && (
        <div className="toast-notice" id="toast-message">
          <CheckCircle size={18} color="#10b981" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <h1 className="brand-title">AI Construction Takeoff Engine</h1>
            <p className="brand-subtitle">
              GPT-powered extraction for construction proposals across trades
            </p>
          </div>
        </div>

        <div className="system-status-badge" id="system-status">
          <div
            className="status-dot"
            style={{ backgroundColor: backendConnected ? '#10b981' : '#f59e0b' }}
          />
          <span>{backendConnected ? 'Backend Connected (OpenAI GPT Ready)' : 'Connecting to API...'}</span>
        </div>
      </header>

      {/* Error Banner */}
      {errorMessage && (
        <div className="error-banner" id="error-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={20} color="#ef4444" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ color: '#fca5a5', fontWeight: 600, fontSize: '0.9rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Upload Screen / Hero */}
      {!takeoffData && !isProcessing && (
        <div className="upload-container">
          <div
            id="upload-dropzone"
            className={`dropzone-area ${isDragging ? 'drag-over' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              id="pdf-upload-input"
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              style={{ display: 'none' }}
              onChange={handleFileInputChange}
            />

            <div className="dropzone-icon-wrapper">
              <UploadCloud size={36} />
            </div>

            <h2 className="dropzone-title">Upload Contractor Bid PDF</h2>
            <p className="dropzone-subtitle">
              Drag and drop your PDF here, or click to browse from your device
            </p>

            <button
              id="upload-button"
              type="button"
              className="btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              <FileText size={18} />
              <span>Browse PDF File</span>
            </button>

            <span className="file-type-hint">Accepts construction proposal PDFs across trades (max 45 MB)</span>
          </div>

        </div>
      )}

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="glass-panel processing-card" id="processing-indicator">
          <div className="spinner" />
          <h3 className="processing-title">GPT is reading the proposal and extracting takeoff data...</h3>
          <p className="processing-desc">
            Sending the original PDF directly to the OpenAI API for document understanding and structured extraction.
          </p>

          <div className="processing-steps">
            <div className={`step-item ${processingStep >= 1 ? 'active' : ''}`}>
              <div className="step-indicator" />
              <span>1. Sending original PDF to GPT</span>
            </div>
            <div className={`step-item ${processingStep >= 2 ? 'active' : ''}`}>
              <div className="step-indicator" />
              <span>2. Extracting structured takeoff data</span>
            </div>
            <div className={`step-item ${processingStep >= 3 ? 'active' : ''}`}>
              <div className="step-indicator" />
              <span>3. Preparing reviewable results</span>
            </div>
          </div>
        </div>
      )}

      {/* Takeoff Result Schedule Screen */}
      {takeoffData && !isProcessing && (
        <div>
          {/* Project Administrative Metadata Card */}
          <div className="glass-panel metadata-grid">
            <div className="meta-item">
              <span className="meta-label">
                <Building size={12} style={{ display: 'inline', marginRight: 4 }} />
                Job Name
              </span>
              <span className="meta-value">{takeoffData.project_metadata.project_name || 'Not Stated'}</span>
            </div>

            <div className="meta-item">
              <span className="meta-label">
                <MapPin size={12} style={{ display: 'inline', marginRight: 4 }} />
                Location
              </span>
              <span className="meta-value">{takeoffData.project_metadata.location || 'Not Stated'}</span>
            </div>

            <div className="meta-item">
              <span className="meta-label">
                <Calendar size={12} style={{ display: 'inline', marginRight: 4 }} />
                Bid Date
              </span>
              <span className="meta-value">{takeoffData.project_metadata.bid_date || 'Not Stated'}</span>
            </div>

            <div className="meta-item">
              <span className="meta-label">
                <User size={12} style={{ display: 'inline', marginRight: 4 }} />
                Prepared By
              </span>
              <span className="meta-value">{takeoffData.project_metadata.prepared_by || 'Not Stated'}</span>
            </div>

            <div className="meta-item">
              <span className="meta-label">
                <DollarSign size={12} style={{ display: 'inline', marginRight: 4 }} />
                Base Proposal Total
              </span>
              <span className="meta-value highlight">
                {takeoffData.project_metadata.budget
                  ? `$${takeoffData.project_metadata.budget.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}`
                  : 'Not Stated'}
              </span>
            </div>
          </div>

          {/* Metric Cards Row */}
          <div className="metrics-row">
            <div className="metric-card">
              <div className="metric-num">{takeoffData.summary.total_items}</div>
              <div className="metric-label">Total Takeoff Items</div>
            </div>

            <div className="metric-card">
              <div className="metric-num" style={{ color: '#34d399' }}>
                {takeoffData.summary.total_items_with_quantity}
              </div>
              <div className="metric-label">Stated Quantities</div>
            </div>

            <div className="metric-card">
              <div className="metric-num" style={{ color: '#cbd5e1' }}>
                {takeoffData.summary.total_items_missing_quantity}
              </div>
              <div className="metric-label">Missing / Null Quantities</div>
            </div>

            <div className="metric-card">
              <div className="metric-num" style={{ color: '#f59e0b' }}>
                {takeoffData.summary.total_review_required}
              </div>
              <div className="metric-label">Items Flagged for Review</div>
            </div>
          </div>

          {/* Control Toolbar */}
          <div className="glass-panel toolbar-card">
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <div className="search-box">
                <Search size={16} color="#94a3b8" />
                <input
                  id="search-input"
                  type="text"
                  placeholder="Filter by description, S.No, or unit..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              {/* Section Filter Dropdown */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Filter size={16} color="#94a3b8" />
                <select
                  id="section-filter"
                  value={selectedSection}
                  onChange={(e) => setSelectedSection(e.target.value)}
                  style={{
                    background: 'rgba(0, 0, 0, 0.4)',
                    color: '#cbd5e1',
                    border: '1px solid var(--border-color)',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    outline: 'none',
                    fontSize: '0.88rem',
                  }}
                >
                  <option value="all">All Sections ({takeoffData.all_items.length} items)</option>
                  {Object.entries(takeoffData.sections).map(([sKey, sData]) => (
                    <option key={sKey} value={sKey}>
                      {sData.section_title} ({sData.item_count})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Export and Reset Buttons */}
            <div className="export-actions">
              <button id="download-excel-btn" type="button" className="btn-success" onClick={handleDownloadExcel}>
                <FileSpreadsheet size={18} />
                <span>Download Excel (.xlsx)</span>
              </button>

              <button id="download-csv-btn" type="button" className="btn-csv" onClick={handleDownloadCsv}>
                <Download size={18} />
                <span>Download CSV (.csv)</span>
              </button>

              <button
                id="reset-btn"
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setTakeoffData(null);
                  setSearchTerm('');
                  setSelectedSection('all');
                }}
              >
                <RefreshCw size={16} />
                <span>New PDF</span>
              </button>
            </div>
          </div>

          {/* MAIN TAKEOFF SCHEDULE TABLE (SECTIONS 1 TO 4) */}
          <div className="table-container">
            <table className="takeoff-table" id="takeoff-main-table">
              <thead>
                <tr>
                  <th style={{ width: '80px', textAlign: 'center' }}>S.No.</th>
                  <th>Description</th>
                  <th style={{ width: '130px', textAlign: 'center' }}>Quantity</th>
                  <th style={{ width: '110px', textAlign: 'center' }}>Unit</th>
                </tr>
              </thead>
              <tbody>
                {/* Render items by section */}
                {Object.entries(takeoffData.sections).map(([secKey, secData]) => {
                  const itemsInSection = filteredItems.filter((it) => it.section === secKey);
                  if (itemsInSection.length === 0 && selectedSection !== 'all') return null;

                  return (
                    <React.Fragment key={secKey}>
                      {/* Section Banner */}
                      <tr className="section-header-row">
                        <td colSpan={4}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                            <Layers size={16} />
                            {secData.section_title.toUpperCase()} ({itemsInSection.length} items)
                          </span>
                        </td>
                      </tr>

                      {/* Line Item Rows */}
                      {itemsInSection.map((item, idx) => {
                        const unitClass = item.unit
                          ? item.unit.toLowerCase() === 'lf'
                            ? 'lf'
                            : item.unit.toLowerCase() === 'ls'
                              ? 'ls'
                              : item.unit.toLowerCase() === 'mo'
                                ? 'mo'
                                : ''
                          : '';

                        return (
                          <tr key={`${secKey}-${item.item_number || idx}`}>
                            <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: '#94a3b8' }}>
                              {item.item_number || idx + 1}
                            </td>
                            <td>
                              <span style={{ color: '#f1f5f9' }}>{item.original_description}</span>
                              {item.review_required && (
                                <span
                                  style={{
                                    marginLeft: '10px',
                                    fontSize: '0.74rem',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    background: item.review_reasons?.some((r) => r.toLowerCase().includes('approximate'))
                                      ? 'rgba(245, 158, 11, 0.15)'
                                      : 'rgba(239, 68, 68, 0.15)',
                                    color: item.review_reasons?.some((r) => r.toLowerCase().includes('approximate'))
                                      ? '#fcd34d'
                                      : '#fca5a5',
                                    border: item.review_reasons?.some((r) => r.toLowerCase().includes('approximate'))
                                      ? '1px solid rgba(245, 158, 11, 0.3)'
                                      : '1px solid rgba(239, 68, 68, 0.3)',
                                  }}
                                  title={item.review_reasons?.join('; ')}
                                >
                                  {item.review_reasons?.some((r) => r.toLowerCase().includes('approximate'))
                                    ? 'Approximate Qty'
                                    : 'Review Required'}
                                </span>
                              )}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {item.quantity !== null && item.quantity !== undefined ? (
                                <span className="qty-val">
                                  {Number.isInteger(item.quantity) ? item.quantity : item.quantity.toFixed(1)}
                                </span>
                              ) : (
                                <span style={{ color: '#64748b' }}>—</span>
                              )}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {item.unit ? (
                                <span className={`badge-unit ${unitClass}`}>{item.unit}</span>
                              ) : (
                                <span style={{ color: '#64748b' }}>—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          {/* SECTION 5: OPTIONAL ITEMS AND COMMERCIAL SUMMARY */}
          {takeoffData.proposal_terms && (
            <div className="table-container" id="commercial-summary-section">
              <table className="takeoff-table">
                <thead>
                  <tr className="section-5-header-row">
                    <td colSpan={4}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                        <DollarSign size={16} />
                        SECTION: 5. OPTIONAL ITEMS AND COMMERCIAL SUMMARY
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>Description</th>
                    <th style={{ width: '130px', textAlign: 'center' }}>Quantity</th>
                    <th style={{ width: '110px', textAlign: 'center' }}>Unit</th>
                    <th style={{ width: '160px', textAlign: 'right' }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Base Proposal Total */}
                  {takeoffData.proposal_terms.base_proposal_total && (
                    <tr style={{ background: 'rgba(99, 102, 241, 0.05)' }}>
                      <td style={{ fontWeight: 600, color: '#f8fafc' }}>Base Proposal Total (Contract Sum)</td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="qty-val">1</span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="badge-unit ls">LS</span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <span className="amount-val">
                          ${takeoffData.proposal_terms.base_proposal_total.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                    </tr>
                  )}

                  {/* Optional Scope Items */}
                  {takeoffData.proposal_terms.options &&
                    takeoffData.proposal_terms.options.map((opt, i) => (
                      <tr key={`opt-${i}`}>
                        <td style={{ color: '#e2e8f0' }}>{opt.description}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="qty-val">{opt.quantity || 1}</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="badge-unit ls">{opt.unit || 'LS'}</span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <span className="amount-val">
                            {opt.amount !== null && opt.amount !== undefined
                              ? `$${opt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                              : 'Optional'}
                          </span>
                        </td>
                      </tr>
                    ))}

                  {/* Monthly Monitoring Rates */}
                  {takeoffData.proposal_terms.monitoring_rates &&
                    takeoffData.proposal_terms.monitoring_rates.map((mr, i) => (
                      <tr key={`mr-${i}`}>
                        <td style={{ color: '#e2e8f0' }}>{mr.description}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="qty-val">{mr.quantity || 1}</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="badge-unit mo">{mr.unit || 'MO'}</span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <span className="amount-val">
                            {mr.amount !== null && mr.amount !== undefined
                              ? `$${mr.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} / mo`
                              : 'Included'}
                          </span>
                        </td>
                      </tr>
                    ))}

                  {/* Payment Milestone Schedule */}
                  {takeoffData.proposal_terms.payment_schedule &&
                    takeoffData.proposal_terms.payment_schedule.map((ps, i) => (
                      <tr key={`ps-${i}`}>
                        <td style={{ color: '#cbd5e1' }}>{ps.milestone}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="qty-val">1</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className="badge-unit ls">LS</span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <span className="amount-val">
                            {ps.amount !== null && ps.amount !== undefined
                              ? ps.milestone.toLowerCase().includes('balance')
                                ? `$${ps.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} (Calculated)`
                                : `$${ps.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                              : ps.milestone.toLowerCase().includes('balance')
                                ? 'Balance Due (Calculated)'
                                : 'Balance Due'}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {/* SECTION 6: CUSTOMER RESPONSIBILITIES & PROPOSAL CONDITIONS */}
          {takeoffData.proposal_terms &&
            ((takeoffData.proposal_terms.customer_responsibilities &&
              takeoffData.proposal_terms.customer_responsibilities.length > 0) ||
              (takeoffData.proposal_terms.notes && takeoffData.proposal_terms.notes.length > 0)) && (
              <div className="table-container" id="notes-conditions-section" style={{ marginTop: '24px' }}>
                <table className="takeoff-table">
                  <thead>
                    <tr style={{ background: 'rgba(30, 41, 59, 0.95)' }}>
                      <th
                        colSpan={2}
                        style={{
                          textAlign: 'left',
                          padding: '14px 18px',
                          color: '#93c5fd',
                          fontSize: '0.95rem',
                        }}
                      >
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                          <ShieldCheck size={18} />
                          SECTION: 6. CUSTOMER RESPONSIBILITIES & PROPOSAL CONDITIONS (IMPORTANT NOTES & TERMS)
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Customer Responsibilities */}
                    {takeoffData.proposal_terms.customer_responsibilities &&
                      takeoffData.proposal_terms.customer_responsibilities.length > 0 && (
                        <>
                          <tr className="section-header-row">
                            <td
                              colSpan={2}
                              style={{
                                color: '#fbbf24',
                                fontSize: '0.86rem',
                                letterSpacing: '0.05em',
                              }}
                            >
                              CUSTOMER RESPONSIBILITIES & SITE REQUIREMENTS
                            </td>
                          </tr>
                          {takeoffData.proposal_terms.customer_responsibilities.map((cr, idx) => (
                            <tr key={`cr-${idx}`}>
                              <td
                                style={{
                                  width: '60px',
                                  textAlign: 'center',
                                  fontFamily: 'var(--font-mono)',
                                  color: '#94a3b8',
                                }}
                              >
                                {idx + 1}
                              </td>
                              <td style={{ color: '#e2e8f0', lineHeight: 1.5 }}>{cr}</td>
                            </tr>
                          ))}
                        </>
                      )}

                    {/* Proposal Conditions & Notes */}
                    {takeoffData.proposal_terms.notes && takeoffData.proposal_terms.notes.length > 0 && (
                      <>
                        <tr className="section-header-row">
                          <td
                            colSpan={2}
                            style={{
                              color: '#38bdf8',
                              fontSize: '0.86rem',
                              letterSpacing: '0.05em',
                            }}
                          >
                            PROPOSAL CONDITIONS, EXCLUSIONS & NOTES
                          </td>
                        </tr>
                        {takeoffData.proposal_terms.notes.map((note, idx) => (
                          <tr key={`note-${idx}`}>
                            <td
                              style={{
                                width: '60px',
                                textAlign: 'center',
                                fontFamily: 'var(--font-mono)',
                                color: '#94a3b8',
                              }}
                            >
                              {idx + 1}
                            </td>
                            <td style={{ color: '#cbd5e1', lineHeight: 1.5 }}>{note}</td>
                          </tr>
                        ))}
                      </>
                    )}
                  </tbody>
                </table>
              </div>
            )}
        </div>
      )}
    </div>
  );
}