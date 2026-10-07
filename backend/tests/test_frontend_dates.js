// Run only the invoice date formatter, without loading the browser app.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../frontend/js/app.js'), 'utf8');
const start = source.indexOf('function formatDate(dateStr)');
const end = source.indexOf('function formatDateTime(', start);
assert.ok(start >= 0 && end > start);
const context = {};
vm.runInNewContext(source.slice(start, end), context);
for (const zone of ['UTC', 'Asia/Ho_Chi_Minh', 'America/Los_Angeles']) {
    process.env.TZ = zone;
    assert.equal(context.formatDate('2026-09-30T17:00:00Z'), '1/10/2026');
    assert.equal(context.formatDate('2026-10-01T00:00:00+07:00'), '1/10/2026');
    assert.equal(context.formatDate('2026-12-31T17:00:00Z'), '1/1/2027');
    assert.equal(context.formatDate(null), '-');
}
console.log('Invoice date display passed in three browser timezones.');
