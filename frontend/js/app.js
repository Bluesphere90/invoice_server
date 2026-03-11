/**
 * Invoice Dashboard - Main Application
 */

const isProduction = window.location.hostname.includes('inv-crifvn.info.vn');
const API_BASE = isProduction
    ? 'https://klm-api.inv-crifvn.info.vn/api'
    : `http://${window.location.hostname}:8000/api`;

console.log('Using API Base:', API_BASE);

// ========================================
// Date Helpers (dd/mm/yyyy format)
// ========================================

/** Convert Date object to dd/mm/yyyy string */
function dateToDisplay(d) {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
}

/** Convert dd/mm/yyyy string to yyyy-mm-dd (for API) */
function displayToApi(ddmmyyyy) {
    if (!ddmmyyyy) return '';
    const parts = ddmmyyyy.split('/');
    if (parts.length !== 3) return '';
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
}

/** Parse dd/mm/yyyy string to Date object */
function parseDisplayDate(ddmmyyyy) {
    if (!ddmmyyyy) return null;
    const parts = ddmmyyyy.split('/');
    if (parts.length !== 3) return null;
    return new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
}

/** Validate dd/mm/yyyy format */
function isValidDateFormat(value) {
    if (!value) return false;
    const regex = /^\d{2}\/\d{2}\/\d{4}$/;
    if (!regex.test(value)) return false;
    const d = parseDisplayDate(value);
    return d instanceof Date && !isNaN(d);
}

/** Auto-format date input (add slashes as user types) */
function initDateInputMask(input) {
    input.addEventListener('input', function (e) {
        let value = this.value.replace(/[^\d]/g, '');
        if (value.length > 8) value = value.substring(0, 8);

        let formatted = '';
        if (value.length > 0) formatted = value.substring(0, Math.min(2, value.length));
        if (value.length > 2) formatted += '/' + value.substring(2, Math.min(4, value.length));
        if (value.length > 4) formatted += '/' + value.substring(4, 8);

        this.value = formatted;
    });

    input.addEventListener('keydown', function (e) {
        // Allow: backspace, delete, tab, escape, enter, arrows
        if ([8, 9, 27, 13, 46, 37, 39].includes(e.keyCode)) return;
        // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
        if ((e.ctrlKey || e.metaKey) && [65, 67, 86, 88].includes(e.keyCode)) return;
        // Block non-numeric
        if ((e.keyCode < 48 || e.keyCode > 57) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
}

// Initialize all date input masks on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.date-input').forEach(initDateInputMask);
});

// State
const state = {
    currentPage: 'dashboard',
    invoicePage: 1,
    invoiceSize: 20,
    invoiceTotal: 0,
    invoicePages: 1,
    invoicesLoaded: false, // Track if user has searched
    companies: [], // Cache companies list
    editingCompany: null, // Track company being edited
    // Logs state
    logsPage: 1,
    logsPageSize: 50,
    logsTotalPages: 1,
    logsTotal: 0,
};

// DOM Elements
const elements = {
    pageTitle: document.getElementById('pageTitle'),
    navItems: document.querySelectorAll('.nav-item'),
    pages: document.querySelectorAll('.page'),

    // Stats
    totalInvoices: document.getElementById('totalInvoices'),
    totalCompanies: document.getElementById('totalCompanies'),
    monthlyChart: document.getElementById('monthlyChart'),

    // Invoices
    invoicesTable: document.getElementById('invoicesTable'),
    companySelect: document.getElementById('companySelect'),
    invoiceTypeSelect: document.getElementById('invoiceTypeSelect'),
    searchInput: document.getElementById('searchInput'),
    fromDate: document.getElementById('fromDate'),
    toDate: document.getElementById('toDate'),
    filterBtn: document.getElementById('filterBtn'),
    exportBtn: document.getElementById('exportBtn'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage'),
    pageInfo: document.getElementById('pageInfo'),

    // Companies
    companiesTable: document.getElementById('companiesTable'),
    addCompanyBtn: document.getElementById('addCompanyBtn'),

    // Modals
    invoiceModal: document.getElementById('invoiceModal'),
    invoiceDetail: document.getElementById('invoiceDetail'),
    closeModal: document.getElementById('closeModal'),
    companyModal: document.getElementById('companyModal'),
    closeCompanyModal: document.getElementById('closeCompanyModal'),
    companyForm: document.getElementById('companyForm'),

    // Collector Modal
    collectorModal: document.getElementById('collectorModal'),
    closeCollectorModal: document.getElementById('closeCollectorModal'),
    collectorTaxCode: document.getElementById('collectorTaxCode'),
    collectorCompanyName: document.getElementById('collectorCompanyName'),
    collectorFromDate: document.getElementById('collectorFromDate'),
    collectorToDate: document.getElementById('collectorToDate'),
    collectorProgress: document.getElementById('collectorProgress'),
    collectorProgressFill: document.getElementById('collectorProgressFill'),
    collectorStatus: document.getElementById('collectorStatus'),
    startCollectorBtn: document.getElementById('startCollectorBtn'),

    // Logs page elements
    logsTable: document.getElementById('logsTable'),
    logLevelFilter: document.getElementById('logLevelFilter'),
    logSearchInput: document.getElementById('logSearchInput'),

    // User Management
    usersTable: document.getElementById('usersTable'),
    addUserBtn: document.getElementById('addUserBtn'),
    addUserModal: document.getElementById('addUserModal'),
    closeAddUserModal: document.getElementById('closeAddUserModal'),
    addUserForm: document.getElementById('addUserForm'),
    userCompaniesModal: document.getElementById('userCompaniesModal'),
    closeUserCompaniesModal: document.getElementById('closeUserCompaniesModal'),
    userCompaniesSelect: document.getElementById('userCompaniesSelect'),
    userCompaniesAccessLevel: document.getElementById('userCompaniesAccessLevel'),
    assignCompanyToUserBtn: document.getElementById('assignCompanyToUserBtn'),
    userCompaniesTable: document.getElementById('userCompaniesTable'),

    // Reports page elements
    reportCompanySelect: document.getElementById('reportCompanySelect'),
    reportFromDate: document.getElementById('reportFromDate'),
    reportToDate: document.getElementById('reportToDate'),
    loadReportBtn: document.getElementById('loadReportBtn'),
    totalIncomingAmount: document.getElementById('totalIncomingAmount'),
    totalOutgoingAmount: document.getElementById('totalOutgoingAmount'),
    netTaxObligation: document.getElementById('netTaxObligation'),
    vatTimelineChart: document.getElementById('vatTimelineChart'),
    invoiceFlowChart: document.getElementById('invoiceFlowChart'),

    // Logs page elements (continued)
    logFromDate: document.getElementById('logFromDate'),
    logToDate: document.getElementById('logToDate'),
    filterLogsBtn: document.getElementById('filterLogsBtn'),
    cleanupLogsBtn: document.getElementById('cleanupLogsBtn'),
    prevLogsPage: document.getElementById('prevLogsPage'),
    nextLogsPage: document.getElementById('nextLogsPage'),
    logsPageInfo: document.getElementById('logsPageInfo'),
    warningCount: document.getElementById('warningCount'),
    errorCount: document.getElementById('errorCount'),
    totalLogsCount: document.getElementById('totalLogsCount'),
};

// ========================================
// Navigation
// ========================================

function navigate(page) {
    state.currentPage = page;

    // Update nav
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Update pages
    elements.pages.forEach(p => {
        p.classList.toggle('active', p.id === page + 'Page');
    });

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        invoices: 'Hóa đơn',
        reports: 'Báo cáo',
        companies: 'Công ty',
        users: 'Quản lý người dùng',
        logs: 'System Logs',
    };
    elements.pageTitle.textContent = titles[page] || 'Dashboard';

    // Load data
    if (page === 'dashboard') loadDashboard();
    else if (page === 'invoices') {
        loadCompaniesDropdown();
        // Don't auto-load invoices - wait for user to filter
        if (!state.invoicesLoaded) {
            showInvoiceEmptyState();
        }
    }
    else if (page === 'reports') {
        loadReportCompaniesDropdown();
        // Set default date range to last 30 days
        const today = new Date();
        const last30Days = new Date(today);
        last30Days.setDate(today.getDate() - 30);

        elements.reportToDate.value = dateToDisplay(today);
        elements.reportFromDate.value = dateToDisplay(last30Days);
    }
    else if (page === 'companies') loadCompanies();
    else if (page === 'users') loadUsers();
    else if (page === 'logs') {
        loadLogsStats();
        loadLogs();
    }
}

// ========================================
// API Calls
// ========================================

async function api(endpoint, options = {}) {
    try {
        const response = await fetch(API_BASE + endpoint, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...Auth.getAuthHeader(),
                ...options.headers,
            },
        });

        // Handle 401 - redirect to login
        if (response.status === 401) {
            Auth.logout();
            return null;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

// ========================================
// Dashboard
// ========================================

async function loadDashboard() {
    // Load stats
    const stats = await api('/invoices/stats');
    if (stats) {
        elements.totalInvoices.textContent = formatNumber(stats.total_invoices);

        // Render chart
        renderChart(stats.invoices_by_month);
    }

    // Load companies count
    const companies = await api('/companies');
    if (companies) {
        elements.totalCompanies.textContent = companies.total;
    }
}

function renderChart(data) {
    const container = elements.monthlyChart;
    container.innerHTML = '';

    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; width: 100%;">Chưa có dữ liệu</p>';
        return;
    }

    const entries = Object.entries(data).sort((a, b) => a[0].localeCompare(b[0])).slice(-6);
    const maxValue = Math.max(...entries.map(e => e[1]), 1);

    entries.forEach(([month, count]) => {
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.style.height = `${(count / maxValue) * 100}%`;
        bar.setAttribute('data-label', month.substring(5)); // MM only
        bar.title = `${month}: ${count} hóa đơn`;
        container.appendChild(bar);
    });
}

// ========================================
// Invoices
// ========================================

function showInvoiceEmptyState() {
    elements.invoicesTable.innerHTML = `
        <tr>
            <td colspan="7" class="empty empty-state">
                <div class="empty-icon">🔍</div>
                <div class="empty-text">Vui lòng chọn công ty, loại hóa đơn và khoảng thời gian, sau đó nhấn <strong>Lọc</strong> để tìm kiếm.</div>
            </td>
        </tr>
    `;
    elements.pageInfo.textContent = 'Trang 1 / 1';
}

async function loadCompaniesDropdown() {
    // Only load if not already loaded
    if (state.companies.length > 0) return;

    const data = await api('/companies');
    if (data && data.items) {
        state.companies = data.items;
        elements.companySelect.innerHTML = '<option value="">-- Chọn công ty --</option>' +
            data.items.map(c => `<option value="${c.tax_code}">${c.company_name || c.tax_code}</option>`).join('');
    }
}

async function loadReportCompaniesDropdown() {
    // Only load if not already loaded
    if (state.companies.length > 0) return;

    const data = await api('/companies');
    if (data && data.items) {
        state.companies = data.items;
        elements.reportCompanySelect.innerHTML = '<option value="">-- Chọn công ty --</option>' +
            data.items.map(c => `<option value="${c.tax_code}">${c.company_name || c.tax_code}</option>`).join('');
    }
}

function validateInvoiceFilters() {
    const company = elements.companySelect.value;
    const invoiceType = elements.invoiceTypeSelect.value;
    const fromDate = elements.fromDate.value;
    const toDate = elements.toDate.value;

    if (!company) {
        alert('Vui lòng chọn công ty');
        return false;
    }
    if (!invoiceType) {
        alert('Vui lòng chọn loại hóa đơn (Vào/Ra)');
        return false;
    }
    if (!fromDate || !toDate) {
        alert('Vui lòng chọn khoảng thời gian');
        return false;
    }
    if (!isValidDateFormat(fromDate) || !isValidDateFormat(toDate)) {
        alert('Ngày không hợp lệ. Vui lòng nhập theo định dạng dd/mm/yyyy');
        return false;
    }
    if (parseDisplayDate(fromDate) > parseDisplayDate(toDate)) {
        alert('Ngày bắt đầu phải nhỏ hơn ngày kết thúc');
        return false;
    }
    return true;
}

function validateReportFilters() {
    const company = elements.reportCompanySelect.value;
    const fromDate = elements.reportFromDate.value;
    const toDate = elements.reportToDate.value;

    if (!company) {
        alert('Vui lòng chọn công ty');
        return false;
    }
    if (!fromDate || !toDate) {
        alert('Vui lòng chọn khoảng thời gian');
        return false;
    }
    if (!isValidDateFormat(fromDate) || !isValidDateFormat(toDate)) {
        alert('Ngày không hợp lệ. Vui lòng nhập theo định dạng dd/mm/yyyy');
        return false;
    }
    if (parseDisplayDate(fromDate) > parseDisplayDate(toDate)) {
        alert('Ngày bắt đầu phải nhỏ hơn ngày kết thúc');
        return false;
    }
    return true;
}

async function loadReports() {
    if (!validateReportFilters()) return;

    const company = elements.reportCompanySelect.value;
    const fromDate = displayToApi(elements.reportFromDate.value);
    const toDate = displayToApi(elements.reportToDate.value);

    const originalText = elements.loadReportBtn.textContent;
    elements.loadReportBtn.disabled = true;
    elements.loadReportBtn.textContent = '⏳ Đang tải...';

    try {
        // Load invoice flow report
        const flowData = await api(`/reports/invoice-flow?tax_code=${company}&from_date=${fromDate}&to_date=${toDate}`);

        if (!flowData) {
            alert('Lỗi khi tải dữ liệu báo cáo');
            return;
        }

        // Update summary stats
        elements.totalIncomingAmount.textContent = formatCurrency(flowData.total_incoming_amount);
        elements.totalOutgoingAmount.textContent = formatCurrency(Math.abs(flowData.total_outgoing_amount));
        elements.netTaxObligation.textContent = formatCurrency(flowData.net_tax_obligation);

        // Render invoice flow chart
        renderInvoiceFlowChart(flowData.items);

        // Load VAT timeline report for chart
        const vatData = await api(`/reports/vat-timeline?tax_code=${company}&from_date=${fromDate}&to_date=${toDate}`);

        if (vatData) {
            renderVatTimelineChart(vatData.items);
        }
    } finally {
        elements.loadReportBtn.disabled = false;
        elements.loadReportBtn.textContent = originalText;
    }
}

function renderVatTimelineChart(items) {
    const container = elements.vatTimelineChart;
    container.innerHTML = '';

    if (!items || items.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; width: 100%;">Chưa có dữ liệu</p>';
        return;
    }

    // Create a canvas element for the chart
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Prepare data for Chart.js
    const labels = items.map(item => item.date);
    const incomingTaxData = items.map(item => item.incoming_tax);
    const outgoingTaxData = items.map(item => item.outgoing_tax);
    const netTaxData = items.map(item => item.net_tax);

    // Create the chart
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Thuế đầu vào',
                    data: incomingTaxData,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    yAxisID: 'y'
                },
                {
                    label: 'Thuế đầu ra',
                    data: outgoingTaxData,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    yAxisID: 'y'
                },
                {
                    label: 'Nợ thuế (ra - vào)',
                    data: netTaxData,
                    borderColor: 'rgb(255, 206, 86)',
                    backgroundColor: 'rgba(255, 206, 86, 0.2)',
                    type: 'bar',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Giá trị thuế'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Nợ thuế'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('vi-VN', {
                                    style: 'currency',
                                    currency: 'VND'
                                }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function renderInvoiceFlowChart(items) {
    const container = elements.invoiceFlowChart;
    container.innerHTML = '';

    if (!items || items.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; width: 100%;">Chưa có dữ liệu</p>';
        return;
    }

    // Group items by date to show daily totals
    const groupedByDate = {};
    items.forEach(item => {
        if (!groupedByDate[item.date]) {
            groupedByDate[item.date] = { incoming: 0, outgoing: 0 };
        }

        if (item.type === 'in') {
            groupedByDate[item.date].incoming += item.amount;
        } else {
            groupedByDate[item.date].outgoing += Math.abs(item.amount); // Use absolute value for outgoing
        }
    });

    // Create a canvas element for the chart
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Prepare data for Chart.js
    const dates = Object.keys(groupedByDate).sort();
    const incomingData = dates.map(date => groupedByDate[date].incoming);
    const outgoingData = dates.map(date => -groupedByDate[date].outgoing); // Negative for outgoing

    // Create the chart
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Giá trị đầu vào',
                    data: incomingData,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Giá trị đầu ra',
                    data: outgoingData,
                    backgroundColor: 'rgba(255, 99, 132, 0.6)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Ngày'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Giá trị'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('vi-VN', {
                                    style: 'currency',
                                    currency: 'VND'
                                }).format(Math.abs(context.parsed.y));
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function getInvoiceFilterParams() {
    const company = elements.companySelect.value;
    const invoiceType = elements.invoiceTypeSelect.value;
    const fromDate = displayToApi(elements.fromDate.value);
    const toDate = displayToApi(elements.toDate.value);
    const search = elements.searchInput.value;

    let params = `from_date=${fromDate}&to_date=${toDate}`;

    // Hóa đơn Vào (Mua): MST người mua = MST công ty
    // Hóa đơn Ra (Bán): MST người bán = MST công ty
    if (invoiceType === 'in') {
        params += `&buyer_tax_code=${company}`;
    } else if (invoiceType === 'out') {
        params += `&tax_code=${company}`;
    }

    if (search) params += `&search=${encodeURIComponent(search)}`;

    return params;
}

async function loadInvoices() {
    if (!validateInvoiceFilters()) return;

    elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty">Đang tải...</td></tr>';

    const filterParams = getInvoiceFilterParams();
    let endpoint = `/invoices?page=${state.invoicePage}&size=${state.invoiceSize}&${filterParams}`;

    const data = await api(endpoint);

    if (!data) {
        elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty">Lỗi tải dữ liệu</td></tr>';
        return;
    }

    state.invoicesLoaded = true;
    state.invoiceTotal = data.total;
    state.invoicePages = data.pages;

    if (data.items.length === 0) {
        elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty">Không có hóa đơn nào phù hợp</td></tr>';
    } else {
        elements.invoicesTable.innerHTML = data.items.map(inv => `
            <tr onclick="showInvoiceDetail('${inv.id}')">
                <td>${formatDate(inv.tdlap)}</td>
                <td>${inv.shdon || '-'}</td>
                <td>${inv.khhdon || '-'}</td>
                <td>${inv.nbten || inv.nbmst || '-'}</td>
                <td>${inv.nmten || '-'}</td>
                <td>${formatCurrency(inv.tgtcthue)}</td>
                <td>${formatCurrency(inv.tgtthue)}</td>
            </tr>
        `).join('');
    }

    elements.pageInfo.textContent = `Trang ${state.invoicePage} / ${state.invoicePages}`;
    elements.prevPage.disabled = state.invoicePage <= 1;
    elements.nextPage.disabled = state.invoicePage >= state.invoicePages;
}

async function exportToExcel() {
    if (!validateInvoiceFilters()) return;

    const filterParams = getInvoiceFilterParams();
    const exportUrl = `${API_BASE}/invoices/export?${filterParams}`;

    // Show loading state
    elements.exportBtn.disabled = true;
    elements.exportBtn.textContent = '⏳ Đang xuất...';

    try {
        const response = await fetch(exportUrl);
        if (!response.ok) {
            throw new Error('Export failed');
        }

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'invoices.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?([^"]+)"?/);
            if (match) filename = match[1];
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (error) {
        console.error('Export error:', error);
        alert('Lỗi khi xuất Excel. Vui lòng thử lại.');
    } finally {
        elements.exportBtn.disabled = false;
        elements.exportBtn.textContent = '📊 Export Excel';
    }
}

async function showInvoiceDetail(id) {
    const data = await api(`/invoices/${id}`);

    if (!data) {
        alert('Không thể tải chi tiết hóa đơn');
        return;
    }

    elements.invoiceDetail.innerHTML = `
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Số hóa đơn</div>
                <div class="detail-value">${data.shdon || '-'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Ký hiệu</div>
                <div class="detail-value">${data.khhdon || '-'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Ngày lập</div>
                <div class="detail-value">${formatDate(data.tdlap)}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Tiền tệ</div>
                <div class="detail-value">${data.dvtte || 'VND'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Người bán</div>
                <div class="detail-value">${data.nbten || '-'}<br><small>${data.nbmst || ''}</small></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Người mua</div>
                <div class="detail-value">${data.nmten || '-'}<br><small>${data.nmmst || ''}</small></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Tổng tiền chưa thuế</div>
                <div class="detail-value">${formatCurrency(data.tgtcthue)}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Tiền thuế</div>
                <div class="detail-value">${formatCurrency(data.tgtthue)}</div>
            </div>
        </div>
        
        <h4 style="margin-bottom: 12px;">Danh sách hàng hóa</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>STT</th>
                    <th>Tên hàng hóa</th>
                    <th>ĐVT</th>
                    <th>SL</th>
                    <th>Đơn giá</th>
                    <th>Thành tiền</th>
                </tr>
            </thead>
            <tbody>
                ${data.items.length > 0 ? data.items.map(item => `
                    <tr>
                        <td>${item.stt || '-'}</td>
                        <td>${item.ten || '-'}</td>
                        <td>${item.dvtinh || '-'}</td>
                        <td>${item.sluong || '-'}</td>
                        <td>${formatCurrency(item.dgia)}</td>
                        <td>${formatCurrency(item.thtien)}</td>
                    </tr>
                `).join('') : '<tr><td colspan="6" class="empty">Không có hàng hóa</td></tr>'}
            </tbody>
        </table>
    `;

    elements.invoiceModal.classList.add('active');
}

// ========================================
// Companies
// ========================================

async function loadCompanies() {
    const data = await api('/companies');

    if (!data) {
        elements.companiesTable.innerHTML = '<tr><td colspan="5" class="empty">Lỗi tải dữ liệu</td></tr>';
        return;
    }

    if (data.items.length === 0) {
        elements.companiesTable.innerHTML = '<tr><td colspan="5" class="empty">Chưa có công ty nào</td></tr>';
    } else {
        elements.companiesTable.innerHTML = data.items.map(c => `
            <tr>
                <td>${c.tax_code}</td>
                <td>${c.company_name || '-'}</td>
                <td>${c.username}</td>
                <td><span class="badge ${c.is_active ? 'badge-success' : 'badge-danger'}">${c.is_active ? 'Hoạt động' : 'Tạm dừng'}</span></td>
                <td>
                    <button class="btn btn-secondary" onclick="editCompany('${c.tax_code}')">✏️ Sửa</button>
                    <button class="btn btn-secondary" onclick="toggleCompany('${c.tax_code}', ${!c.is_active})">${c.is_active ? 'Tạm dừng' : 'Kích hoạt'}</button>
                    ${c.is_active ? `<button class="btn btn-primary" onclick="showCollectorModal('${c.tax_code}', '${c.company_name || c.tax_code}')">📥 Thu thập</button>` : ''}
                    <button class="btn btn-danger" onclick="deleteCompany('${c.tax_code}')">🗑️ Xóa</button>
                </td>
            </tr>
        `).join('');
    }
}

async function toggleCompany(taxCode, activate) {
    await api(`/companies/${taxCode}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: activate }),
    });
    loadCompanies();
}

async function editCompany(taxCode) {
    // Fetch company data
    const company = await api(`/companies/${taxCode}`);
    if (!company) {
        alert('Không thể tải thông tin công ty');
        return;
    }

    // Set editing state
    state.editingCompany = taxCode;

    // Populate form
    document.getElementById('companyTaxCode').value = company.tax_code;
    document.getElementById('companyTaxCode').disabled = true; // Cannot change tax code
    document.getElementById('companyName').value = company.company_name || '';
    document.getElementById('companyUsername').value = company.username;
    document.getElementById('companyPassword').value = ''; // Don't show password
    document.getElementById('companyPassword').placeholder = 'Để trống nếu không đổi';

    // Update modal title
    document.getElementById('companyModalTitle').textContent = 'Sửa công ty';

    // Show modal
    elements.companyModal.classList.add('active');
}

async function deleteCompany(taxCode) {
    if (!confirm(`Bạn có chắc muốn xóa công ty ${taxCode}?\n\nLưu ý: Thao tác này sẽ vô hiệu hóa công ty, không xóa dữ liệu.`)) {
        return;
    }

    const result = await api(`/companies/${taxCode}`, {
        method: 'DELETE',
    });

    // DELETE returns 204 No Content, so result might be null but still successful
    loadCompanies();
    // Refresh companies cache
    state.companies = [];
    loadCompaniesDropdown();
}

async function saveCompany(e) {
    e.preventDefault();

    const taxCode = document.getElementById('companyTaxCode').value;
    const isEditing = state.editingCompany !== null;

    const data = {
        company_name: document.getElementById('companyName').value,
        username: document.getElementById('companyUsername').value,
    };

    // Only include password if provided
    const password = document.getElementById('companyPassword').value;
    if (password) {
        data.password = password;
    }

    // Add tax_code only for new companies
    if (!isEditing) {
        data.tax_code = taxCode;
    }

    const endpoint = isEditing ? `/companies/${taxCode}` : '/companies';
    const method = isEditing ? 'PUT' : 'POST';

    const result = await api(endpoint, {
        method: method,
        body: JSON.stringify(data),
    });

    if (result) {
        elements.companyModal.classList.remove('active');
        elements.companyForm.reset();
        state.editingCompany = null;
        loadCompanies();
        // Refresh companies cache
        state.companies = [];
    } else {
        alert(isEditing ? 'Lỗi cập nhật công ty.' : 'Lỗi thêm công ty. Vui lòng kiểm tra lại.');
    }
}

// ========================================
// Collector
// ========================================

let collectorPollingInterval = null;

function showCollectorModal(taxCode, companyName) {
    // Reset modal state
    elements.collectorTaxCode.value = taxCode;
    elements.collectorCompanyName.value = companyName;

    // Set default dates (last 30 days)
    const today = new Date();
    const last30Days = new Date(today);
    last30Days.setDate(today.getDate() - 30);

    elements.collectorToDate.value = dateToDisplay(today);
    elements.collectorFromDate.value = dateToDisplay(last30Days);

    // Reset progress
    elements.collectorProgress.style.display = 'none';
    elements.collectorProgressFill.style.width = '0%';
    elements.collectorStatus.textContent = '';

    // Reset button
    elements.startCollectorBtn.disabled = false;
    elements.startCollectorBtn.textContent = '🚀 Bắt đầu thu thập';
    elements.startCollectorBtn.classList.remove('btn-success');
    elements.startCollectorBtn.classList.add('btn-primary');

    // Show modal
    elements.collectorModal.classList.add('active');
}

async function startCollector() {
    const taxCode = elements.collectorTaxCode.value;
    const fromDateDisplay = elements.collectorFromDate.value;
    const toDateDisplay = elements.collectorToDate.value;

    if (!fromDateDisplay || !toDateDisplay) {
        alert('Vui lòng chọn khoảng thời gian');
        return;
    }

    if (!isValidDateFormat(fromDateDisplay) || !isValidDateFormat(toDateDisplay)) {
        alert('Ngày không hợp lệ. Vui lòng nhập theo định dạng dd/mm/yyyy');
        return;
    }

    if (parseDisplayDate(fromDateDisplay) > parseDisplayDate(toDateDisplay)) {
        alert('Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc');
        return;
    }

    const fromDate = displayToApi(fromDateDisplay);
    const toDate = displayToApi(toDateDisplay);

    // Disable button
    elements.startCollectorBtn.disabled = true;
    elements.startCollectorBtn.textContent = '⏳ Đang khởi động...';

    // Show progress
    elements.collectorProgress.style.display = 'block';
    elements.collectorStatus.textContent = 'Đang khởi động...';

    const result = await api('/collector/run', {
        method: 'POST',
        body: JSON.stringify({
            tax_code: taxCode,
            from_date: fromDate,
            to_date: toDate
        }),
    });

    if (!result) {
        elements.startCollectorBtn.disabled = false;
        elements.startCollectorBtn.textContent = '🚀 Bắt đầu thu thập';
        elements.collectorStatus.textContent = 'Lỗi khi khởi động. Vui lòng thử lại.';
        return;
    }

    // Start polling for status
    pollCollectorStatus(result.job_id);
}

function pollCollectorStatus(jobId) {
    // Clear any existing interval
    if (collectorPollingInterval) {
        clearInterval(collectorPollingInterval);
    }

    collectorPollingInterval = setInterval(async () => {
        const status = await api(`/collector/status/${jobId}`);

        if (!status) {
            clearInterval(collectorPollingInterval);
            elements.collectorStatus.textContent = 'Lỗi kết nối. Vui lòng kiểm tra lại.';
            elements.startCollectorBtn.disabled = false;
            elements.startCollectorBtn.textContent = '🚀 Bắt đầu thu thập';
            return;
        }

        // Update progress
        elements.collectorProgressFill.style.width = `${status.progress}%`;
        elements.collectorStatus.textContent = status.message;

        if (status.status === 'completed') {
            clearInterval(collectorPollingInterval);
            elements.startCollectorBtn.textContent = '✅ Hoàn thành';
            elements.startCollectorBtn.classList.remove('btn-primary');
            elements.startCollectorBtn.classList.add('btn-success');
            elements.startCollectorBtn.disabled = false;

            // Click to close modal
            elements.startCollectorBtn.onclick = () => {
                elements.collectorModal.classList.remove('active');
                // Refresh dashboard stats if on dashboard
                if (state.currentPage === 'dashboard') {
                    loadDashboard();
                }
            };
        } else if (status.status === 'failed') {
            clearInterval(collectorPollingInterval);
            elements.startCollectorBtn.disabled = false;
            elements.startCollectorBtn.textContent = '🚀 Thử lại';
            elements.collectorStatus.textContent = `Lỗi: ${status.error || 'Không xác định'}`;
        }
    }, 2000); // Poll every 2 seconds
}

// ========================================
// Helpers
// ========================================

function formatNumber(num) {
    return (num || 0).toLocaleString('vi-VN');
}

function formatCurrency(num) {
    if (!num) return '0';
    return new Intl.NumberFormat('vi-VN').format(num);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('vi-VN');
    } catch {
        return dateStr.substring(0, 10);
    }
}

function formatDateTime(isoString) {
    if (!isoString) return '-';
    try {
        const d = new Date(isoString);
        return d.toLocaleString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch {
        return isoString;
    }
}

// ========================================
// Logs Page
// ========================================

async function loadLogsStats() {
    const stats = await api('/logs/stats?days=7');
    if (stats) {
        elements.warningCount.textContent = formatNumber(stats.warning_count);
        elements.errorCount.textContent = formatNumber(stats.error_count + stats.critical_count);
        elements.totalLogsCount.textContent = formatNumber(stats.total_logs);
    }
}

async function loadLogs() {
    if (!elements.logsTable) return;

    elements.logsTable.innerHTML = '<tr><td colspan="4" class="empty">Đang tải logs...</td></tr>';

    // Build query params
    const params = new URLSearchParams();
    params.set('page', state.logsPage);
    params.set('page_size', state.logsPageSize);

    const level = elements.logLevelFilter?.value;
    const search = elements.logSearchInput?.value;
    const fromDate = elements.logFromDate?.value;
    const toDate = elements.logToDate?.value;

    if (level) params.set('level', level);
    if (search) params.set('search', search);
    if (fromDate && isValidDateFormat(fromDate)) params.set('from_date', displayToApi(fromDate));
    if (toDate && isValidDateFormat(toDate)) params.set('to_date', displayToApi(toDate));

    const data = await api(`/logs?${params.toString()}`);

    if (!data) {
        elements.logsTable.innerHTML = '<tr><td colspan="4" class="empty">Lỗi tải dữ liệu. Bạn cần quyền Admin.</td></tr>';
        return;
    }

    state.logsTotal = data.total;
    state.logsTotalPages = data.total_pages;

    if (data.logs.length === 0) {
        elements.logsTable.innerHTML = '<tr><td colspan="4" class="empty">Không có logs nào</td></tr>';
    } else {
        elements.logsTable.innerHTML = data.logs.map(log => `
            <tr>
                <td class="log-timestamp">${formatDateTime(log.timestamp)}</td>
                <td><span class="log-level log-level-${log.level.toLowerCase()}">${log.level}</span></td>
                <td class="log-logger">${log.logger || '-'}</td>
                <td class="log-message">${escapeHtml(log.message || '-')}</td>
            </tr>
        `).join('');
    }

    elements.logsPageInfo.textContent = `Trang ${state.logsPage} / ${state.logsTotalPages}`;
    elements.prevLogsPage.disabled = state.logsPage <= 1;
    elements.nextLogsPage.disabled = state.logsPage >= state.logsTotalPages;
}

async function cleanupLogs() {
    const days = prompt('Xóa logs cũ hơn bao nhiêu ngày? (mặc định: 30)', '30');
    if (days === null) return;

    const daysNum = parseInt(days);
    if (isNaN(daysNum) || daysNum < 7) {
        alert('Vui lòng nhập số ngày >= 7');
        return;
    }

    if (!confirm(`Bạn có chắc muốn xóa tất cả logs cũ hơn ${daysNum} ngày?`)) {
        return;
    }

    const result = await api(`/logs/cleanup?days=${daysNum}`, { method: 'DELETE' });
    if (result) {
        alert(`Đã xóa ${result.deleted_count} logs cũ.`);
        loadLogs();
        loadLogsStats();
    } else {
        alert('Lỗi khi xóa logs.');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// Event Listeners
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication first
    if (!Auth.checkAuth()) {
        return; // Will redirect to login
    }

    // Navigation
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navigate(item.dataset.page);
        });
    });

    // Invoice filters
    elements.filterBtn.addEventListener('click', () => {
        state.invoicePage = 1;
        loadInvoices();
    });

    elements.exportBtn.addEventListener('click', exportToExcel);

    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && state.invoicesLoaded) {
            state.invoicePage = 1;
            loadInvoices();
        }
    });

    // Pagination
    elements.prevPage.addEventListener('click', () => {
        if (state.invoicePage > 1) {
            state.invoicePage--;
            loadInvoices();
        }
    });

    elements.nextPage.addEventListener('click', () => {
        if (state.invoicePage < state.invoicePages) {
            state.invoicePage++;
            loadInvoices();
        }
    });

    // Modals
    elements.closeModal.addEventListener('click', () => {
        elements.invoiceModal.classList.remove('active');
    });

    elements.addCompanyBtn.addEventListener('click', () => {
        state.editingCompany = null;
        document.getElementById('companyTaxCode').disabled = false;
        document.getElementById('companyPassword').placeholder = '';
        document.getElementById('companyModalTitle').textContent = 'Thêm công ty';
        elements.companyForm.reset();
        elements.companyModal.classList.add('active');
    });

    elements.closeCompanyModal.addEventListener('click', () => {
        elements.companyModal.classList.remove('active');
    });

    elements.companyForm.addEventListener('submit', saveCompany);

    // Collector modal events
    elements.closeCollectorModal.addEventListener('click', () => {
        elements.collectorModal.classList.remove('active');
        // Clear polling if running
        if (collectorPollingInterval) {
            clearInterval(collectorPollingInterval);
            collectorPollingInterval = null;
        }
    });

    elements.startCollectorBtn.addEventListener('click', startCollector);

    // Close modals on backdrop click
    [elements.invoiceModal, elements.companyModal, elements.collectorModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                // Clear polling if collector modal
                if (modal === elements.collectorModal && collectorPollingInterval) {
                    clearInterval(collectorPollingInterval);
                    collectorPollingInterval = null;
                }
            }
        });
    });

    // Initial load
    loadDashboard();

    // Check if user is admin and show admin-only elements
    const user = Auth.getCurrentUser();
    if (user && user.role && user.role.toLowerCase() === 'admin') {
        document.body.classList.add('is-admin');
    }

    // Logs page events (if elements exist)
    if (elements.filterLogsBtn) {
        elements.filterLogsBtn.addEventListener('click', () => {
            state.logsPage = 1;
            loadLogs();
        });
    }

    if (elements.cleanupLogsBtn) {
        elements.cleanupLogsBtn.addEventListener('click', cleanupLogs);
    }

    if (elements.prevLogsPage) {
        elements.prevLogsPage.addEventListener('click', () => {
            if (state.logsPage > 1) {
                state.logsPage--;
                loadLogs();
            }
        });
    }

    if (elements.nextLogsPage) {
        elements.nextLogsPage.addEventListener('click', () => {
            if (state.logsPage < state.logsTotalPages) {
                state.logsPage++;
                loadLogs();
            }
        });
    }

    if (elements.logSearchInput) {
        elements.logSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                state.logsPage = 1;
                loadLogs();
            }
        });
    }

    // User Management Events
    if (elements.addUserBtn) {
        elements.addUserBtn.addEventListener('click', () => {
            document.getElementById('addUserForm').reset();
            document.getElementById('addUserModalTitle').textContent = 'Thêm người dùng';
            elements.addUserModal.classList.add('active');
        });
    }

    if (elements.closeAddUserModal) {
        elements.closeAddUserModal.addEventListener('click', () => {
            elements.addUserModal.classList.remove('active');
        });
    }

    if (elements.addUserForm) {
        elements.addUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const userData = {
                username: document.getElementById('addUsername').value,
                password: document.getElementById('addPassword').value,
                full_name: document.getElementById('addFullName').value,
                role: document.getElementById('addUserRole').value
            };

            const result = await api('/users', {
                method: 'POST',
                body: JSON.stringify(userData)
            });

            if (result) {
                elements.addUserModal.classList.remove('active');
                loadUsers();
            } else {
                alert('Lỗi khi thêm người dùng');
            }
        });
    }

    // Close addUserModal on backdrop click
    if (elements.addUserModal) {
        elements.addUserModal.addEventListener('click', (e) => {
            if (e.target === elements.addUserModal) {
                elements.addUserModal.classList.remove('active');
            }
        });
    }

    // Report page events
    if (elements.loadReportBtn) {
        elements.loadReportBtn.addEventListener('click', loadReports);
    }

    // Edit User Modal Events
    const editUserModal = document.getElementById('editUserModal');
    const closeEditUserModal = document.getElementById('closeEditUserModal');
    const editUserForm = document.getElementById('editUserForm');

    if (closeEditUserModal) {
        closeEditUserModal.addEventListener('click', () => {
            editUserModal.classList.remove('active');
        });
    }

    if (editUserModal) {
        editUserModal.addEventListener('click', (e) => {
            if (e.target === editUserModal) {
                editUserModal.classList.remove('active');
            }
        });
    }

    if (editUserForm) {
        editUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const userId = document.getElementById('editUserId').value;
            const fullName = document.getElementById('editFullName').value;
            const role = document.getElementById('editUserRole').value;
            const isActive = document.getElementById('editUserStatus').value === 'true';
            const password = document.getElementById('editPassword').value;

            // Update user details
            const updateData = {
                full_name: fullName,
                role: role,
                is_active: isActive
            };

            try {
                // 1. Update basic info
                const result = await api(`/users/${userId}`, {
                    method: 'PUT',
                    body: JSON.stringify(updateData)
                });

                if (!result) {
                    throw new Error('Lỗi cập nhật thông tin người dùng');
                }

                // 2. Update password if provided
                if (password) {
                    const passResult = await api(`/users/${userId}/password`, {
                        method: 'PATCH',
                        body: JSON.stringify({ password: password })
                    });

                    if (!passResult) {
                        alert('Cập nhật thông tin thành công nhưng lỗi cập nhật mật khẩu');
                    }
                }

                alert('Cập nhật người dùng thành công');
                editUserModal.classList.remove('active');
                loadUsers();

            } catch (error) {
                console.error(error);
                alert('Lỗi cập nhật người dùng');
            }
        });
    }

    // User Companies Modal Events
    if (elements.closeUserCompaniesModal) {
        elements.closeUserCompaniesModal.addEventListener('click', () => {
            elements.userCompaniesModal.classList.remove('active');
        });
    }

    if (elements.assignCompanyToUserBtn) {
        elements.assignCompanyToUserBtn.addEventListener('click', async () => {
            const userId = document.getElementById('userCompaniesUserId').value;
            const companyId = document.getElementById('userCompaniesSelect').value;
            const accessLevel = document.getElementById('userCompaniesAccessLevel').value;

            if (!companyId) {
                alert('Vui lòng chọn công ty');
                return;
            }

            const result = await api(`/users/${userId}/companies`, {
                method: 'POST',
                body: JSON.stringify({
                    company_id: parseInt(companyId),
                    access_level: accessLevel
                })
            });

            if (result) {
                loadUserCompanies(userId);
                document.getElementById('userCompaniesSelect').value = '';
            } else {
                alert('Lỗi khi phân quyền công ty');
            }
        });
    }

    // Close userCompaniesModal on backdrop click
    if (elements.userCompaniesModal) {
        elements.userCompaniesModal.addEventListener('click', (e) => {
            if (e.target === elements.userCompaniesModal) {
                elements.userCompaniesModal.classList.remove('active');
            }
        });
    }
});

// ========================================
// User Management Functions
// ========================================

async function loadUsers() {
    const data = await api('/users');

    if (!data) {
        elements.usersTable.innerHTML = '<tr><td colspan="6" class="empty">Lỗi tải dữ liệu</td></tr>';
        return;
    }

    if (data.items.length === 0) {
        elements.usersTable.innerHTML = '<tr><td colspan="6" class="empty">Chưa có người dùng nào</td></tr>';
    } else {
        elements.usersTable.innerHTML = data.items.map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${u.username}</td>
                <td>${u.full_name || '-'}</td>
                <td><span class="badge ${u.role === 'admin' ? 'badge-danger' : u.role === 'accounting' ? 'badge-warning' : 'badge-info'}">${u.role}</span></td>
                <td><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'Hoạt động' : 'Không hoạt động'}</span></td>
                <td>
                    <button class="btn btn-secondary" onclick="editUser(${u.id})">✏️ Sửa</button>
                    <button class="btn btn-primary" onclick="showUserCompanies(${u.id}, '${u.username}')">🏢 Phân quyền</button>
                    <button class="btn btn-danger" onclick="deleteUser(${u.id})">🗑️ Xóa</button>
                </td>
            </tr>
        `).join('');
    }
}

async function loadUserCompanies(userId) {
    const data = await api(`/users/${userId}/companies`);

    if (!data) {
        document.getElementById('userCompaniesTable').innerHTML = '<tr><td colspan="4" class="empty">Lỗi tải dữ liệu</td></tr>';
        return;
    }

    if (data.companies.length === 0) {
        document.getElementById('userCompaniesTable').innerHTML = '<tr><td colspan="4" class="empty">Chưa có công ty nào được phân quyền</td></tr>';
    } else {
        document.getElementById('userCompaniesTable').innerHTML = data.companies.map(c => `
            <tr>
                <td>${c.company_name || c.tax_code}</td>
                <td>${c.tax_code}</td>
                <td><span class="badge ${c.access_level === 'admin' ? 'badge-danger' : c.access_level === 'write' ? 'badge-warning' : 'badge-info'}">${c.access_level}</span></td>
                <td>
                    <button class="btn btn-danger" onclick="removeCompanyFromUser(${userId}, ${c.id})">🗑️ Xóa</button>
                </td>
            </tr>
        `).join('');
    }
}

async function showUserCompanies(userId, username) {
    // Load companies dropdown
    const companiesData = await api('/companies');
    if (companiesData) {
        const companiesSelect = document.getElementById('userCompaniesSelect');
        companiesSelect.innerHTML = '<option value="">-- Chọn công ty --</option>' +
            companiesData.items.map(c => `<option value="${c.id}">${c.company_name || c.tax_code}</option>`).join('');
    }

    // Set user info
    document.getElementById('userCompaniesUserId').value = userId;
    document.getElementById('userCompaniesUsername').value = username;
    document.getElementById('userCompaniesModalTitle').textContent = `Phân quyền công ty cho ${username}`;

    // Load user's companies
    loadUserCompanies(userId);

    // Show modal
    elements.userCompaniesModal.classList.add('active');
}

async function removeCompanyFromUser(userId, companyId) {
    if (!confirm('Bạn có chắc muốn xóa quyền truy cập công ty này?')) {
        return;
    }

    const result = await api(`/users/${userId}/companies/${companyId}`, {
        method: 'DELETE'
    });

    if (result) {
        loadUserCompanies(userId);
    } else {
        alert('Lỗi khi xóa quyền truy cập công ty');
    }
}

async function deleteUser(userId) {
    if (!confirm('Bạn có chắc muốn xóa người dùng này?')) {
        return;
    }

    const result = await api(`/users/${userId}`, {
        method: 'DELETE'
    });

    if (result) {
        loadUsers();
    } else {
        alert('Lỗi khi xóa người dùng');
    }
}

// Edit User Function
async function editUser(userId) {
    // 1. Fetch user details
    const user = await api(`/users/${userId}`);
    if (!user) {
        alert('Không thể tải thông tin người dùng');
        return;
    }

    // 2. Populate modal
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUsername').value = user.username;
    document.getElementById('editFullName').value = user.full_name || '';
    document.getElementById('editUserRole').value = user.role;
    document.getElementById('editUserStatus').value = user.is_active ? 'true' : 'false';
    document.getElementById('editPassword').value = ''; // Reset password field

    // 3. Show modal
    const modal = document.getElementById('editUserModal');
    if (modal) {
        modal.classList.add('active');
    } else {
        console.error('Edit User Modal not found');
    }
}
