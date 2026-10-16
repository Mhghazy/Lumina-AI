/**
 * Vendors Management System - Core Architecture
 * Implements: OOP, Design Patterns, Data Structures, Algorithms
 * Patterns: Strategy, Observer, Singleton, Factory, Command
 */

// ==================== DESIGN PATTERNS ====================

// 1. STRATEGY PATTERN - Search Strategies
class SearchStrategy {
  match(value, searchTerm) {
    throw new Error('match() must be implemented by subclass');
  }
}

class ExactSearchStrategy extends SearchStrategy {
  match(value, searchTerm) {
    return String(value) === String(searchTerm);
  }
}

class PartialSearchStrategy extends SearchStrategy {
  match(value, searchTerm) {
    return String(value).toLowerCase().includes(String(searchTerm).toLowerCase());
  }
}

class CaseInsensitiveSearchStrategy extends SearchStrategy {
  match(value, searchTerm) {
    return String(value).toLowerCase() === String(searchTerm).toLowerCase();
  }
}

class RegexSearchStrategy extends SearchStrategy {
  match(value, searchTerm) {
    try {
      const regex = new RegExp(searchTerm, 'i');
      return regex.test(String(value));
    } catch {
      return false;
    }
  }
}

// 2. STRATEGY PATTERN - Sort Strategies
class SortStrategy {
  sort(data, column, direction) {
    throw new Error('sort() must be implemented by subclass');
  }
}

class AlphabeticSortStrategy extends SortStrategy {
  sort(data, column, direction = 'asc') {
    return [...data].sort((a, b) => {
      const aVal = String(a[column] || '').toLowerCase();
      const bVal = String(b[column] || '').toLowerCase();
      const comparison = aVal.localeCompare(bVal);
      return direction === 'asc' ? comparison : -comparison;
    });
  }
}

class NumericSortStrategy extends SortStrategy {
  sort(data, column, direction = 'asc') {
    return [...data].sort((a, b) => {
      const aVal = Number(a[column]) || 0;
      const bVal = Number(b[column]) || 0;
      const comparison = aVal - bVal;
      return direction === 'asc' ? comparison : -comparison;
    });
  }
}

class DateSortStrategy extends SortStrategy {
  sort(data, column, direction = 'asc') {
    return [...data].sort((a, b) => {
      const aVal = new Date(a[column] || 0).getTime();
      const bVal = new Date(b[column] || 0).getTime();
      const comparison = aVal - bVal;
      return direction === 'asc' ? comparison : -comparison;
    });
  }
}

// 3. SINGLETON PATTERN - Application State
class VendorAppState {
  static instance = null;
  
  constructor() {
    if (VendorAppState.instance) {
      return VendorAppState.instance;
    }
    
    this.data = [];
    this.filteredData = [];
    this.columns = [];
    this.primaryKey = 'id';
    this.sortColumn = null;
    this.sortDirection = 'asc';
    this.searchFilters = new Map();
    this.observers = new Set();
    this.searchStrategy = new PartialSearchStrategy();
    this.sortStrategy = new AlphabeticSortStrategy();
    
    VendorAppState.instance = this;
  }
  
  static getInstance() {
    if (!VendorAppState.instance) {
      VendorAppState.instance = new VendorAppState();
    }
    return VendorAppState.instance;
  }
  
  // Observer Pattern - Subscribe to state changes
  subscribe(observer) {
    this.observers.add(observer);
    return () => this.observers.delete(observer);
  }
  
  notify(event, data) {
    this.observers.forEach(observer => {
      try {
        observer(event, data);
      } catch (error) {
        console.error('Observer error:', error);
      }
    });
  }
  
  setData(data) {
    this.data = data;
    this.applyFiltersAndSort();
    this.notify('dataChanged', { data: this.filteredData });
  }
  
  setColumns(columns) {
    this.columns = columns;
    this.notify('columnsChanged', { columns });
  }
  
  setSearchFilter(column, value) {
    if (value) {
      this.searchFilters.set(column, value);
    } else {
      this.searchFilters.delete(column);
    }
    this.applyFiltersAndSort();
    this.notify('filtersChanged', { filters: this.searchFilters });
  }
  
  setSortColumn(column) {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.applyFiltersAndSort();
    this.notify('sortChanged', { column, direction: this.sortDirection });
  }
  
  applyFiltersAndSort() {
    // Filter
    let filtered = this.data.filter(item => {
      for (const [column, searchTerm] of this.searchFilters.entries()) {
        const value = item[column];
        if (!this.searchStrategy.match(value, searchTerm)) {
          return false;
        }
      }
      return true;
    });
    
    // Sort
    if (this.sortColumn) {
      filtered = this.sortStrategy.sort(filtered, this.sortColumn, this.sortDirection);
    }
    
    this.filteredData = filtered;
  }
  
  getFilteredData() {
    return this.filteredData;
  }
  
  getTotalCount() {
    return this.data.length;
  }
  
  getFilteredCount() {
    return this.filteredData.length;
  }
}

// 4. DATA STORE PATTERN with CRUD Operations
class VendorDataStore {
  constructor() {
    this.data = [];
    this.columns = [];
    this.primaryKey = 'id';
    this.observers = new Set();
  }
  
  setData(data) {
    this.data = data;
    this.notifyObservers('dataLoaded', this.data);
  }
  
  addVendor(vendor) {
    this.data.push(vendor);
    this.notifyObservers('vendorAdded', vendor);
    return vendor;
  }
  
  updateVendor(id, updates) {
    const index = this.data.findIndex(v => v[this.primaryKey] === id);
    if (index !== -1) {
      this.data[index] = { ...this.data[index], ...updates };
      this.notifyObservers('vendorUpdated', this.data[index]);
      return this.data[index];
    }
    return null;
  }
  
  deleteVendor(id) {
    const index = this.data.findIndex(v => v[this.primaryKey] === id);
    if (index !== -1) {
      const deleted = this.data.splice(index, 1)[0];
      this.notifyObservers('vendorDeleted', deleted);
      return deleted;
    }
    return null;
  }
  
  getVendor(id) {
    return this.data.find(v => v[this.primaryKey] === id);
  }
  
  getAllVendors() {
    return [...this.data];
  }
  
  subscribe(observer) {
    this.observers.add(observer);
    return () => this.observers.delete(observer);
  }
  
  notifyObservers(event, data) {
    this.observers.forEach(observer => observer(event, data));
  }
}

// 5. COMMAND PATTERN - Undo/Redo functionality
class Command {
  execute() {}
  undo() {}
}

class AddVendorCommand extends Command {
  constructor(store, vendor) {
    super();
    this.store = store;
    this.vendor = vendor;
  }
  
  execute() {
    this.store.addVendor(this.vendor);
  }
  
  undo() {
    this.store.deleteVendor(this.vendor[this.store.primaryKey]);
  }
}

class UpdateVendorCommand extends Command {
  constructor(store, id, updates) {
    super();
    this.store = store;
    this.id = id;
    this.updates = updates;
    this.previousState = null;
  }
  
  execute() {
    this.previousState = this.store.getVendor(this.id);
    this.store.updateVendor(this.id, this.updates);
  }
  
  undo() {
    if (this.previousState) {
      this.store.updateVendor(this.id, this.previousState);
    }
  }
}

class DeleteVendorCommand extends Command {
  constructor(store, id) {
    super();
    this.store = store;
    this.id = id;
    this.deletedVendor = null;
  }
  
  execute() {
    this.deletedVendor = this.store.deleteVendor(this.id);
  }
  
  undo() {
    if (this.deletedVendor) {
      this.store.addVendor(this.deletedVendor);
    }
  }
}

class CommandHistory {
  constructor() {
    this.undoStack = [];
    this.redoStack = [];
  }
  
  executeCommand(command) {
    command.execute();
    this.undoStack.push(command);
    this.redoStack = []; // Clear redo stack on new command
  }
  
  undo() {
    const command = this.undoStack.pop();
    if (command) {
      command.undo();
      this.redoStack.push(command);
    }
  }
  
  redo() {
    const command = this.redoStack.pop();
    if (command) {
      command.execute();
      this.undoStack.push(command);
    }
  }
  
  canUndo() {
    return this.undoStack.length > 0;
  }
  
  canRedo() {
    return this.redoStack.length > 0;
  }
}

// 6. SCROLL MANAGER with Performance Optimization
class ScrollManager {
  constructor() {
    this.scrollPosition = 0;
    this.isScrolling = false;
    this.scrollThreshold = 300;
    this.rafId = null;
  }
  
  setScrollPosition(position) {
    this.scrollPosition = position;
  }
  
  getScrollPosition() {
    return this.scrollPosition;
  }
  
  shouldShowScrollButton(position) {
    return position > this.scrollThreshold;
  }
  
  scrollToTop(smooth = true) {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
    
    if (smooth) {
      this.smoothScrollToTop();
    } else {
      window.scrollTo(0, 0);
    }
  }
  
  smoothScrollToTop() {
    const scroll = () => {
      const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
      
      if (currentScroll > 0) {
        window.scrollTo(0, currentScroll - currentScroll / 8);
        this.rafId = requestAnimationFrame(scroll);
      } else {
        this.rafId = null;
      }
    };
    
    scroll();
  }
  
  syncHorizontalScroll(source, target) {
    if (!this.isScrolling) {
      this.isScrolling = true;
      target.scrollLeft = source.scrollLeft;
      requestAnimationFrame(() => {
        this.isScrolling = false;
      });
    }
  }
}

// 7. THEME MANAGER with LocalStorage Persistence
class ThemeManager {
  constructor() {
    this.currentTheme = this.loadTheme();
    this.themes = {
      light: {
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        text: '#2c3e50',
        cardBg: '#ffffff'
      },
      dark: {
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        text: '#e0e0e0',
        cardBg: '#2c3e50'
      }
    };
  }
  
  loadTheme() {
    return localStorage.getItem('vendor_theme') || 'light';
  }
  
  saveTheme(theme) {
    localStorage.setItem('vendor_theme', theme);
  }
  
  getCurrentTheme() {
    return this.currentTheme;
  }
  
  setTheme(theme) {
    this.currentTheme = theme;
    this.saveTheme(theme);
    this.applyTheme();
  }
  
  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }
  
  applyTheme() {
    if (this.currentTheme === 'dark') {
      document.body.classList.add('night-mode');
    } else {
      document.body.classList.remove('night-mode');
    }
  }
}

// 8. VALIDATOR with Chain of Responsibility
class Validator {
  constructor() {
    this.rules = new Map();
  }
  
  addRule(field, rule) {
    if (!this.rules.has(field)) {
      this.rules.set(field, []);
    }
    this.rules.get(field).push(rule);
  }
  
  validate(field, value) {
    const fieldRules = this.rules.get(field) || [];
    for (const rule of fieldRules) {
      const result = rule(value);
      if (!result.valid) {
        return result;
      }
    }
    return { valid: true };
  }
  
  isRequired(value) {
    return value !== null && value !== undefined && String(value).trim() !== '';
  }
  
  isValidEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
  }
  
  isValidPhone(phone) {
    const regex = /^[\d\s\-\(\)]+$/;
    return regex.test(phone) && phone.replace(/\D/g, '').length >= 10;
  }
  
  isValidURL(url) {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }
  
  minLength(value, min) {
    return String(value).length >= min;
  }
  
  maxLength(value, max) {
    return String(value).length <= max;
  }
}

// 9. STATISTICS CALCULATOR
class StatisticsCalculator {
  sum(data, field) {
    return data.reduce((sum, item) => sum + (Number(item[field]) || 0), 0);
  }
  
  average(data, field) {
    return data.length > 0 ? this.sum(data, field) / data.length : 0;
  }
  
  max(data, field) {
    return Math.max(...data.map(item => Number(item[field]) || 0));
  }
  
  min(data, field) {
    return Math.min(...data.map(item => Number(item[field]) || 0));
  }
  
  count(data, field, value) {
    return data.filter(item => item[field] === value).length;
  }
  
  groupBy(data, field) {
    return data.reduce((groups, item) => {
      const key = item[field];
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(item);
      return groups;
    }, {});
  }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
  window.VendorCore = {
    // Patterns
    SearchStrategy,
    ExactSearchStrategy,
    PartialSearchStrategy,
    CaseInsensitiveSearchStrategy,
    RegexSearchStrategy,
    SortStrategy,
    AlphabeticSortStrategy,
    NumericSortStrategy,
    DateSortStrategy,
    // State & Data
    VendorAppState,
    VendorDataStore,
    // Commands
    Command,
    AddVendorCommand,
    UpdateVendorCommand,
    DeleteVendorCommand,
    CommandHistory,
    // Utilities
    ScrollManager,
    ThemeManager,
    Validator,
    StatisticsCalculator
  };
}
