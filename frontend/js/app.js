/**
 * Invoice Dashboard - Main Application
 */

const API_BASE = 'http://localhost:8000/api';

// State
const state = {
    currentPage: 'dashboard',
    invoicePage: 1,
    invoiceSize: 20,
    invoiceTotal: 0,
    invoicePages: 1,
};

// DOM Elements
const elements = {
    pageTitle: document.getElementById('pageTitle'),
    navItems: document.querySelectorAll('.nav-item'),
    pages: document.querySelectorAll('.page'),

    // Stats
    totalInvoices: document.getElementById('totalInvoices'),
    totalAmount: document.getElementById('totalAmount'),
    totalTax: document.getElementById('totalTax'),
    totalCompanies: document.getElementById('totalCompanies'),
    monthlyChart: document.getElementById('monthlyChart'),

    // Invoices
    invoicesTable: document.getElementById('invoicesTable'),
    searchInput: document.getElementById('searchInput'),
    fromDate: document.getElementById('fromDate'),
    toDate: document.getElementById('toDate'),
    filterBtn: document.getElementById('filterBtn'),
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
        companies: 'Công ty',
    };
    elements.pageTitle.textContent = titles[page] || 'Dashboard';

    // Load data
    if (page === 'dashboard') loadDashboard();
    else if (page === 'invoices') loadInvoices();
    else if (page === 'companies') loadCompanies();
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
                ...options.headers,
            },
        });

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
        elements.totalAmount.textContent = formatCurrency(stats.total_amount);
        elements.totalTax.textContent = formatCurrency(stats.total_tax);

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

async function loadInvoices() {
    const search = elements.searchInput.value;
    const fromDate = elements.fromDate.value;
    const toDate = elements.toDate.value;

    let endpoint = `/invoices?page=${state.invoicePage}&size=${state.invoiceSize}`;
    if (search) endpoint += `&search=${encodeURIComponent(search)}`;
    if (fromDate) endpoint += `&from_date=${fromDate}`;
    if (toDate) endpoint += `&to_date=${toDate}`;

    const data = await api(endpoint);

    if (!data) {
        elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty">Lỗi tải dữ liệu</td></tr>';
        return;
    }

    state.invoiceTotal = data.total;
    state.invoicePages = data.pages;

    if (data.items.length === 0) {
        elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty">Không có hóa đơn nào</td></tr>';
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
                    <button class="btn btn-secondary" onclick="toggleCompany('${c.tax_code}', ${!c.is_active})">${c.is_active ? 'Tạm dừng' : 'Kích hoạt'}</button>
                    ${c.is_active ? `<button class="btn btn-primary" onclick="showCollectorModal('${c.tax_code}', '${c.company_name || c.tax_code}')">📥 Thu thập</button>` : ''}
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

async function saveCompany(e) {
    e.preventDefault();

    const data = {
        tax_code: document.getElementById('companyTaxCode').value,
        company_name: document.getElementById('companyName').value,
        username: document.getElementById('companyUsername').value,
        password: document.getElementById('companyPassword').value,
    };

    const result = await api('/companies', {
        method: 'POST',
        body: JSON.stringify(data),
    });

    if (result) {
        elements.companyModal.classList.remove('active');
        elements.companyForm.reset();
        loadCompanies();
    } else {
        alert('Lỗi thêm công ty. Vui lòng kiểm tra lại.');
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

    elements.collectorToDate.value = today.toISOString().split('T')[0];
    elements.collectorFromDate.value = last30Days.toISOString().split('T')[0];

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
    const fromDate = elements.collectorFromDate.value;
    const toDate = elements.collectorToDate.value;

    if (!fromDate || !toDate) {
        alert('Vui lòng chọn khoảng thời gian');
        return;
    }

    if (new Date(fromDate) > new Date(toDate)) {
        alert('Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc');
        return;
    }

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
            elements.startCollectorBtn.disabled = false;
            elements.startCollectorBtn.textContent = '✅ Hoàn thành!';
            elements.startCollectorBtn.classList.remove('btn-primary');
            elements.startCollectorBtn.classList.add('btn-success');

            // Refresh dashboard stats if on dashboard
            if (state.currentPage === 'dashboard') {
                loadDashboard();
            }
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
    if (!num) return '0 ₫';
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        maximumFractionDigits: 0,
    }).format(num);
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

// ========================================
// Event Listeners
// ========================================

document.addEventListener('DOMContentLoaded', () => {
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

    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
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
        document.getElementById('companyTaxCode').disabled = false;
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
});
