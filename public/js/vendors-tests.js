/**
 * Vendors Management System - Test Suite
 * Test-Driven Development (TDD) Implementation
 * Framework: Jest-like vanilla JS testing
 */

class TestRunner {
  constructor(name) {
    this.name = name;
    this.tests = [];
    this.beforeEachFn = null;
    this.afterEachFn = null;
    this.results = { passed: 0, failed: 0, errors: [] };
  }

  beforeEach(fn) {
    this.beforeEachFn = fn;
  }

  afterEach(fn) {
    this.afterEachFn = fn;
  }

  test(description, fn) {
    this.tests.push({ description, fn });
  }

  async run() {
    console.log(`\n🧪 Running Test Suite: ${this.name}\n${'='.repeat(50)}`);
    
    for (const test of this.tests) {
      try {
        if (this.beforeEachFn) await this.beforeEachFn();
        
        await test.fn();
        
        if (this.afterEachFn) await this.afterEachFn();
        
        this.results.passed++;
        console.log(`✅ PASS: ${test.description}`);
      } catch (error) {
        this.results.failed++;
        this.results.errors.push({ test: test.description, error: error.message });
        console.error(`❌ FAIL: ${test.description}\n   Error: ${error.message}`);
      }
    }

    this.printSummary();
    return this.results;
  }

  printSummary() {
    console.log(`\n${'='.repeat(50)}`);
    console.log(`📊 Test Summary for ${this.name}`);
    console.log(`Total: ${this.tests.length} | Passed: ${this.results.passed} | Failed: ${this.results.failed}`);
    
    if (this.results.failed > 0) {
      console.log(`\n❌ Failed Tests:`);
      this.results.errors.forEach(({ test, error }) => {
        console.log(`   - ${test}: ${error}`);
      });
    }
    
    console.log(`${'='.repeat(50)}\n`);
  }
}

// Assertion Library
class Expect {
  constructor(actual) {
    this.actual = actual;
  }

  toBe(expected) {
    if (this.actual !== expected) {
      throw new Error(`Expected ${expected} but got ${this.actual}`);
    }
  }

  toEqual(expected) {
    if (JSON.stringify(this.actual) !== JSON.stringify(expected)) {
      throw new Error(`Expected ${JSON.stringify(expected)} but got ${JSON.stringify(this.actual)}`);
    }
  }

  toBeTruthy() {
    if (!this.actual) {
      throw new Error(`Expected truthy value but got ${this.actual}`);
    }
  }

  toBeFalsy() {
    if (this.actual) {
      throw new Error(`Expected falsy value but got ${this.actual}`);
    }
  }

  toBeNull() {
    if (this.actual !== null) {
      throw new Error(`Expected null but got ${this.actual}`);
    }
  }

  toBeUndefined() {
    if (this.actual !== undefined) {
      throw new Error(`Expected undefined but got ${this.actual}`);
    }
  }

  toBeInstanceOf(expectedClass) {
    if (!(this.actual instanceof expectedClass)) {
      throw new Error(`Expected instance of ${expectedClass.name} but got ${this.actual.constructor.name}`);
    }
  }

  toContain(item) {
    if (!this.actual.includes(item)) {
      throw new Error(`Expected array to contain ${item}`);
    }
  }

  toHaveLength(length) {
    if (this.actual.length !== length) {
      throw new Error(`Expected length ${length} but got ${this.actual.length}`);
    }
  }

  toThrow() {
    try {
      this.actual();
      throw new Error('Expected function to throw but it did not');
    } catch (e) {
      if (e.message === 'Expected function to throw but it did not') throw e;
    }
  }
}

function expect(actual) {
  return new Expect(actual);
}

// Mock DOM for testing
class MockDOM {
  static createElement(tag) {
    return {
      tagName: tag.toUpperCase(),
      children: [],
      attributes: {},
      style: {},
      classList: {
        add: function(...classes) { this.classes = [...(this.classes || []), ...classes]; },
        remove: function(...classes) { this.classes = (this.classes || []).filter(c => !classes.includes(c)); },
        contains: function(className) { return (this.classes || []).includes(className); }
      },
      addEventListener: function() {},
      removeEventListener: function() {},
      appendChild: function(child) { this.children.push(child); },
      querySelector: function() { return null; },
      querySelectorAll: function() { return []; },
      getAttribute: function(name) { return this.attributes[name]; },
      setAttribute: function(name, value) { this.attributes[name] = value; },
      removeAttribute: function(name) { delete this.attributes[name]; }
    };
  }

  static createTextNode(text) {
    return { nodeType: 3, textContent: text };
  }
}

// ==============================================
// UNIT TESTS
// ==============================================

async function runVendorManagementTests() {
  const suite = new TestRunner('Vendor Management System');

  // Test: VendorDataStore Class
  suite.test('VendorDataStore should initialize correctly', () => {
    const store = new VendorDataStore();
    expect(store.data).toEqual([]);
    expect(store.columns).toEqual([]);
    expect(store.primaryKey).toBe('id');
  });

  suite.test('VendorDataStore should add vendor correctly', () => {
    const store = new VendorDataStore();
    const vendor = { id: 1, name: 'Test Vendor', category: 'A' };
    store.addVendor(vendor);
    expect(store.data).toHaveLength(1);
    expect(store.data[0]).toEqual(vendor);
  });

  suite.test('VendorDataStore should update vendor correctly', () => {
    const store = new VendorDataStore();
    const vendor = { id: 1, name: 'Test Vendor', category: 'A' };
    store.addVendor(vendor);
    store.updateVendor(1, { name: 'Updated Vendor' });
    expect(store.getVendor(1).name).toBe('Updated Vendor');
  });

  suite.test('VendorDataStore should delete vendor correctly', () => {
    const store = new VendorDataStore();
    const vendor = { id: 1, name: 'Test Vendor', category: 'A' };
    store.addVendor(vendor);
    store.deleteVendor(1);
    expect(store.data).toHaveLength(0);
  });

  // Test: SearchStrategy Classes
  suite.test('ExactSearchStrategy should match exact values', () => {
    const strategy = new ExactSearchStrategy();
    expect(strategy.match('test', 'test')).toBeTruthy();
    expect(strategy.match('test', 'Test')).toBeFalsy();
  });

  suite.test('PartialSearchStrategy should match partial values', () => {
    const strategy = new PartialSearchStrategy();
    expect(strategy.match('testing', 'test')).toBeTruthy();
    expect(strategy.match('best', 'test')).toBeTruthy();
    expect(strategy.match('hello', 'test')).toBeFalsy();
  });

  suite.test('CaseInsensitiveSearchStrategy should ignore case', () => {
    const strategy = new CaseInsensitiveSearchStrategy();
    expect(strategy.match('Test', 'test')).toBeTruthy();
    expect(strategy.match('TEST', 'test')).toBeTruthy();
    expect(strategy.match('TeSt', 'test')).toBeTruthy();
  });

  // Test: SortStrategy Classes
  suite.test('AlphabeticSortStrategy should sort correctly', () => {
    const strategy = new AlphabeticSortStrategy();
    const data = [{ name: 'Charlie' }, { name: 'Alice' }, { name: 'Bob' }];
    const sorted = strategy.sort(data, 'name', 'asc');
    expect(sorted[0].name).toBe('Alice');
    expect(sorted[2].name).toBe('Charlie');
  });

  suite.test('NumericSortStrategy should sort numbers correctly', () => {
    const strategy = new NumericSortStrategy();
    const data = [{ value: 30 }, { value: 10 }, { value: 20 }];
    const sorted = strategy.sort(data, 'value', 'asc');
    expect(sorted[0].value).toBe(10);
    expect(sorted[2].value).toBe(30);
  });

  // Test: Filter Function
  suite.test('filterVendors should apply search criteria correctly', () => {
    const vendors = [
      { id: 1, name: 'Test Vendor', category: 'A' },
      { id: 2, name: 'Another Vendor', category: 'B' },
      { id: 3, name: 'Test Company', category: 'A' }
    ];
    
    const filters = { name: 'test' };
    const strategy = new CaseInsensitiveSearchStrategy();
    
    const filtered = vendors.filter(vendor => {
      for (const [key, value] of Object.entries(filters)) {
        if (value && !strategy.match(String(vendor[key]), String(value))) {
          return false;
        }
      }
      return true;
    });
    
    expect(filtered).toHaveLength(2);
    expect(filtered[0].name).toBe('Test Vendor');
  });

  // Test: ScrollManager
  suite.test('ScrollManager should track scroll position', () => {
    const manager = new ScrollManager();
    manager.setScrollPosition(100);
    expect(manager.getScrollPosition()).toBe(100);
  });

  suite.test('ScrollManager should show/hide scroll button correctly', () => {
    const manager = new ScrollManager();
    expect(manager.shouldShowScrollButton(0)).toBeFalsy();
    expect(manager.shouldShowScrollButton(400)).toBeTruthy();
  });

  // Test: Validation
  suite.test('Validator should validate required fields', () => {
    const validator = new Validator();
    expect(validator.isRequired('')).toBeFalsy();
    expect(validator.isRequired('value')).toBeTruthy();
    expect(validator.isRequired(null)).toBeFalsy();
    expect(validator.isRequired(undefined)).toBeFalsy();
  });

  suite.test('Validator should validate email format', () => {
    const validator = new Validator();
    expect(validator.isValidEmail('test@example.com')).toBeTruthy();
    expect(validator.isValidEmail('invalid-email')).toBeFalsy();
    expect(validator.isValidEmail('')).toBeFalsy();
  });

  suite.test('Validator should validate phone number', () => {
    const validator = new Validator();
    expect(validator.isValidPhone('123-456-7890')).toBeTruthy();
    expect(validator.isValidPhone('(123) 456-7890')).toBeTruthy();
    expect(validator.isValidPhone('invalid')).toBeFalsy();
  });

  // Test: StatisticsCalculator
  suite.test('StatisticsCalculator should calculate totals correctly', () => {
    const calc = new StatisticsCalculator();
    const data = [{ value: 10 }, { value: 20 }, { value: 30 }];
    expect(calc.sum(data, 'value')).toBe(60);
    expect(calc.average(data, 'value')).toBe(20);
    expect(calc.max(data, 'value')).toBe(30);
    expect(calc.min(data, 'value')).toBe(10);
  });

  // Test: ThemeManager
  suite.test('ThemeManager should toggle theme correctly', () => {
    const manager = new ThemeManager();
    const initialTheme = manager.getCurrentTheme();
    manager.toggleTheme();
    expect(manager.getCurrentTheme()).not.toBe(initialTheme);
  });

  await suite.run();
  return suite.results;
}

// ==============================================
// INTEGRATION TESTS
// ==============================================

async function runIntegrationTests() {
  const suite = new TestRunner('Integration Tests');

  suite.test('Full vendor CRUD workflow', () => {
    const store = new VendorDataStore();
    
    // Create
    const vendor = { id: 1, name: 'Test Vendor', category: 'A' };
    store.addVendor(vendor);
    expect(store.data).toHaveLength(1);
    
    // Read
    const retrieved = store.getVendor(1);
    expect(retrieved).toEqual(vendor);
    
    // Update
    store.updateVendor(1, { category: 'B' });
    expect(store.getVendor(1).category).toBe('B');
    
    // Delete
    store.deleteVendor(1);
    expect(store.data).toHaveLength(0);
  });

  suite.test('Search and sort workflow', () => {
    const store = new VendorDataStore();
    store.addVendor({ id: 1, name: 'Charlie', value: 30 });
    store.addVendor({ id: 2, name: 'Alice', value: 10 });
    store.addVendor({ id: 3, name: 'Bob', value: 20 });
    
    // Sort alphabetically
    const alphaSorted = new AlphabeticSortStrategy().sort(store.data, 'name', 'asc');
    expect(alphaSorted[0].name).toBe('Alice');
    
    // Sort numerically
    const numSorted = new NumericSortStrategy().sort(store.data, 'value', 'desc');
    expect(numSorted[0].value).toBe(30);
  });

  suite.test('Theme persistence workflow', () => {
    const manager = new ThemeManager();
    const storage = new LocalStorageManager('vendors_test');
    
    // Set theme
    manager.setTheme('dark');
    storage.set('theme', 'dark');
    
    // Retrieve theme
    const savedTheme = storage.get('theme');
    expect(savedTheme).toBe('dark');
  });

  await suite.run();
  return suite.results;
}

// ==============================================
// PERFORMANCE TESTS
// ==============================================

async function runPerformanceTests() {
  const suite = new TestRunner('Performance Tests');

  suite.test('Large dataset filtering should complete within 100ms', () => {
    const store = new VendorDataStore();
    
    // Create 1000 vendors
    for (let i = 0; i < 1000; i++) {
      store.addVendor({
        id: i,
        name: `Vendor ${i}`,
        category: i % 2 === 0 ? 'A' : 'B'
      });
    }
    
    const start = performance.now();
    const strategy = new CaseInsensitiveSearchStrategy();
    const filtered = store.data.filter(v => strategy.match(v.category, 'A'));
    const duration = performance.now() - start;
    
    expect(filtered).toHaveLength(500);
    if (duration > 100) {
      throw new Error(`Filtering took ${duration}ms, expected < 100ms`);
    }
  });

  suite.test('Sorting 1000 items should complete within 50ms', () => {
    const data = [];
    for (let i = 0; i < 1000; i++) {
      data.push({ id: i, value: Math.random() * 1000 });
    }
    
    const start = performance.now();
    const strategy = new NumericSortStrategy();
    strategy.sort(data, 'value', 'asc');
    const duration = performance.now() - start;
    
    if (duration > 50) {
      throw new Error(`Sorting took ${duration}ms, expected < 50ms`);
    }
  });

  await suite.run();
  return suite.results;
}

// ==============================================
// E2E TESTS (End-to-End)
// ==============================================

async function runE2ETests() {
  const suite = new TestRunner('End-to-End Tests');

  suite.test('Complete page initialization', () => {
    // Mock DOM environment
    const app = {
      initialized: false,
      init: function() {
        this.store = new VendorDataStore();
        this.scrollManager = new ScrollManager();
        this.themeManager = new ThemeManager();
        this.initialized = true;
      }
    };
    
    app.init();
    expect(app.initialized).toBeTruthy();
    expect(app.store).toBeInstanceOf(VendorDataStore);
    expect(app.scrollManager).toBeInstanceOf(ScrollManager);
  });

  await suite.run();
  return suite.results;
}

// ==============================================
// TEST EXECUTION
// ==============================================

async function runAllTests() {
  console.log('\n🚀 Starting Automated Test Suite\n');
  
  const results = {
    unit: await runVendorManagementTests(),
    integration: await runIntegrationTests(),
    performance: await runPerformanceTests(),
    e2e: await runE2ETests()
  };
  
  const totalTests = Object.values(results).reduce((sum, r) => sum + r.passed + r.failed, 0);
  const totalPassed = Object.values(results).reduce((sum, r) => sum + r.passed, 0);
  const totalFailed = Object.values(results).reduce((sum, r) => sum + r.failed, 0);
  
  console.log('\n' + '='.repeat(60));
  console.log('🎯 FINAL TEST RESULTS');
  console.log('='.repeat(60));
  console.log(`Total Tests: ${totalTests}`);
  console.log(`✅ Passed: ${totalPassed} (${Math.round(totalPassed / totalTests * 100)}%)`);
  console.log(`❌ Failed: ${totalFailed} (${Math.round(totalFailed / totalTests * 100)}%)`);
  console.log('='.repeat(60));
  
  if (totalFailed === 0) {
    console.log('\n🎉 ALL TESTS PASSED! 🎉\n');
  } else {
    console.log('\n⚠️  SOME TESTS FAILED - Please review errors above\n');
  }
  
  return { totalTests, totalPassed, totalFailed, results };
}

// Export for use in vendor page
if (typeof window !== 'undefined') {
  window.VendorTests = {
    runAllTests,
    runVendorManagementTests,
    runIntegrationTests,
    runPerformanceTests,
    runE2ETests,
    expect,
    TestRunner
  };
}

// Auto-run tests if in test mode
if (typeof window !== 'undefined' && window.location.search.includes('test=true')) {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => runAllTests(), 1000);
  });
}
