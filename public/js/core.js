/**
 * Core Application Framework - OOP Architecture
 * Implements: Design Patterns, Performance Optimization, Data Structures
 */

// ============= Performance & Utility Classes =============

class PerformanceMonitor {
  constructor() {
    this.metrics = new Map();
    this.observers = new Set();
  }

  mark(label) {
    performance.mark(label);
  }

  measure(name, startMark, endMark) {
    try {
      performance.measure(name, startMark, endMark);
      const measure = performance.getEntriesByName(name)[0];
      this.metrics.set(name, measure.duration);
      this.notifyObservers(name, measure.duration);
    } catch (e) {
      console.warn(`Performance measurement failed: ${e.message}`);
    }
  }

  addObserver(callback) {
    this.observers.add(callback);
  }

  notifyObservers(name, duration) {
    this.observers.forEach(observer => observer(name, duration));
  }
}

class DOMCache {
  constructor() {
    this.cache = new Map();
  }

  get(selector) {
    if (!this.cache.has(selector)) {
      const element = document.querySelector(selector);
      if (element) this.cache.set(selector, element);
    }
    return this.cache.get(selector);
  }

  getAll(selector) {
    if (!this.cache.has(selector)) {
      const elements = [...document.querySelectorAll(selector)];
      if (elements.length) this.cache.set(selector, elements);
    }
    return this.cache.get(selector) || [];
  }

  clear() {
    this.cache.clear();
  }

  refresh(selector) {
    this.cache.delete(selector);
    return this.get(selector);
  }
}

class Debouncer {
  constructor() {
    this.timers = new Map();
  }

  debounce(key, callback, delay = 300) {
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
    }
    
    const timer = setTimeout(() => {
      callback();
      this.timers.delete(key);
    }, delay);
    
    this.timers.set(key, timer);
  }

  cancel(key) {
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
      this.timers.delete(key);
    }
  }

  cancelAll() {
    this.timers.forEach(timer => clearTimeout(timer));
    this.timers.clear();
  }
}

class EventBus {
  constructor() {
    this.events = new Map();
  }

  on(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event).add(callback);
    
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.events.has(event)) {
      this.events.get(event).delete(callback);
    }
  }

  emit(event, data) {
    if (this.events.has(event)) {
      this.events.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (e) {
          console.error(`Event handler error for ${event}:`, e);
        }
      });
    }
  }

  clear(event) {
    if (event) {
      this.events.delete(event);
    } else {
      this.events.clear();
    }
  }
}

// ============= Animation System =============

class AnimationController {
  constructor() {
    this.animations = new Map();
    this.rafId = null;
  }

  register(id, animation) {
    this.animations.set(id, animation);
  }

  play(id) {
    const animation = this.animations.get(id);
    if (animation && typeof animation.play === 'function') {
      animation.play();
    }
  }

  pause(id) {
    const animation = this.animations.get(id);
    if (animation && typeof animation.pause === 'function') {
      animation.pause();
    }
  }

  requestFrame(callback) {
    this.rafId = requestAnimationFrame(callback);
  }

  cancelFrame() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }
}

class ParticleSystem {
  constructor(container, options = {}) {
    this.container = container;
    this.particles = [];
    this.config = {
      count: options.count || 20,
      minSize: options.minSize || 2,
      maxSize: options.maxSize || 10,
      speed: options.speed || 1,
      color: options.color || 'rgba(255, 255, 255, 0.5)',
      ...options
    };
    this.pool = [];
    this.active = false;
  }

  createParticle() {
    if (this.pool.length > 0) {
      return this.pool.pop();
    }

    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.cssText = `
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      will-change: transform, opacity;
    `;
    return particle;
  }

  recycleParticle(particle) {
    if (particle.parentNode) {
      particle.parentNode.removeChild(particle);
    }
    this.pool.push(particle);
  }

  init() {
    const fragment = document.createDocumentFragment();
    
    for (let i = 0; i < this.config.count; i++) {
      const particle = this.createParticle();
      const size = Math.random() * (this.config.maxSize - this.config.minSize) + this.config.minSize;
      
      particle.style.width = `${size}px`;
      particle.style.height = `${size}px`;
      particle.style.background = this.config.color;
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.top = `${Math.random() * 100}%`;
      particle.style.animationDelay = `${Math.random() * 15}s`;
      particle.style.animationDuration = `${Math.random() * 10 + 10}s`;
      
      this.particles.push(particle);
      fragment.appendChild(particle);
    }
    
    this.container.appendChild(fragment);
    this.active = true;
  }

  destroy() {
    this.particles.forEach(particle => this.recycleParticle(particle));
    this.particles = [];
    this.active = false;
  }
}

// ============= Storage Layer =============

class LocalStorageManager {
  constructor(prefix = 'app') {
    this.prefix = prefix;
    this.cache = new Map();
  }

  getKey(key) {
    return `${this.prefix}_${key}`;
  }

  set(key, value, useCache = true) {
    try {
      const serialized = JSON.stringify(value);
      localStorage.setItem(this.getKey(key), serialized);
      if (useCache) {
        this.cache.set(key, value);
      }
      return true;
    } catch (e) {
      console.error('LocalStorage set error:', e);
      return false;
    }
  }

  get(key, defaultValue = null) {
    // Check cache first
    if (this.cache.has(key)) {
      return this.cache.get(key);
    }

    try {
      const item = localStorage.getItem(this.getKey(key));
      if (item === null) return defaultValue;
      
      const parsed = JSON.parse(item);
      this.cache.set(key, parsed);
      return parsed;
    } catch (e) {
      console.error('LocalStorage get error:', e);
      return defaultValue;
    }
  }

  remove(key) {
    localStorage.removeItem(this.getKey(key));
    this.cache.delete(key);
  }

  clear() {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        localStorage.removeItem(key);
      }
    });
    this.cache.clear();
  }

  has(key) {
    return localStorage.getItem(this.getKey(key)) !== null;
  }
}

// ============= Data Structures =============

class PriorityQueue {
  constructor(compareFn = (a, b) => a - b) {
    this.heap = [];
    this.compare = compareFn;
  }

  get size() {
    return this.heap.length;
  }

  peek() {
    return this.heap[0];
  }

  push(value) {
    this.heap.push(value);
    this.bubbleUp(this.heap.length - 1);
  }

  pop() {
    if (this.heap.length === 0) return undefined;
    
    const top = this.heap[0];
    const bottom = this.heap.pop();
    
    if (this.heap.length > 0) {
      this.heap[0] = bottom;
      this.bubbleDown(0);
    }
    
    return top;
  }

  bubbleUp(index) {
    while (index > 0) {
      const parentIndex = Math.floor((index - 1) / 2);
      
      if (this.compare(this.heap[index], this.heap[parentIndex]) >= 0) {
        break;
      }
      
      [this.heap[index], this.heap[parentIndex]] = [this.heap[parentIndex], this.heap[index]];
      index = parentIndex;
    }
  }

  bubbleDown(index) {
    while (true) {
      let minIndex = index;
      const leftChild = 2 * index + 1;
      const rightChild = 2 * index + 2;
      
      if (leftChild < this.heap.length && this.compare(this.heap[leftChild], this.heap[minIndex]) < 0) {
        minIndex = leftChild;
      }
      
      if (rightChild < this.heap.length && this.compare(this.heap[rightChild], this.heap[minIndex]) < 0) {
        minIndex = rightChild;
      }
      
      if (minIndex === index) break;
      
      [this.heap[index], this.heap[minIndex]] = [this.heap[minIndex], this.heap[index]];
      index = minIndex;
    }
  }
}

class LRUCache {
  constructor(capacity = 100) {
    this.capacity = capacity;
    this.cache = new Map();
  }

  get(key) {
    if (!this.cache.has(key)) return null;
    
    const value = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.capacity) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  clear() {
    this.cache.clear();
  }
}

// ============= UI Components Base =============

class Component {
  constructor(container, options = {}) {
    this.container = container;
    this.options = options;
    this.state = {};
    this.eventListeners = [];
    this.rendered = false;
  }

  setState(newState) {
    this.state = { ...this.state, ...newState };
    if (this.rendered) {
      this.render();
    }
  }

  getState() {
    return { ...this.state };
  }

  addEventListener(element, event, handler, options) {
    element.addEventListener(event, handler, options);
    this.eventListeners.push({ element, event, handler, options });
  }

  removeEventListeners() {
    this.eventListeners.forEach(({ element, event, handler, options }) => {
      element.removeEventListener(event, handler, options);
    });
    this.eventListeners = [];
  }

  render() {
    // Override in subclass
  }

  mount() {
    this.render();
    this.rendered = true;
  }

  unmount() {
    this.removeEventListeners();
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.rendered = false;
  }
}

// ============= Responsive Utilities =============

class ResponsiveManager {
  constructor() {
    this.breakpoints = {
      mobile: 768,
      tablet: 1024,
      desktop: 1440
    };
    this.listeners = new Map();
    this.currentBreakpoint = this.getCurrentBreakpoint();
    this.init();
  }

  init() {
    const mediaQueries = {
      mobile: window.matchMedia(`(max-width: ${this.breakpoints.mobile - 1}px)`),
      tablet: window.matchMedia(`(min-width: ${this.breakpoints.mobile}px) and (max-width: ${this.breakpoints.tablet - 1}px)`),
      desktop: window.matchMedia(`(min-width: ${this.breakpoints.tablet}px)`)
    };

    Object.entries(mediaQueries).forEach(([breakpoint, mq]) => {
      mq.addEventListener('change', () => this.handleBreakpointChange());
    });
  }

  getCurrentBreakpoint() {
    const width = window.innerWidth;
    if (width < this.breakpoints.mobile) return 'mobile';
    if (width < this.breakpoints.tablet) return 'tablet';
    return 'desktop';
  }

  handleBreakpointChange() {
    const newBreakpoint = this.getCurrentBreakpoint();
    if (newBreakpoint !== this.currentBreakpoint) {
      const oldBreakpoint = this.currentBreakpoint;
      this.currentBreakpoint = newBreakpoint;
      this.notifyListeners(newBreakpoint, oldBreakpoint);
    }
  }

  onBreakpointChange(callback) {
    const id = Symbol('listener');
    this.listeners.set(id, callback);
    return () => this.listeners.delete(id);
  }

  notifyListeners(newBreakpoint, oldBreakpoint) {
    this.listeners.forEach(callback => {
      callback(newBreakpoint, oldBreakpoint);
    });
  }

  isMobile() {
    return this.currentBreakpoint === 'mobile';
  }

  isTablet() {
    return this.currentBreakpoint === 'tablet';
  }

  isDesktop() {
    return this.currentBreakpoint === 'desktop';
  }
}

// ============= Export Singleton Instances =============

const perfMonitor = new PerformanceMonitor();
const domCache = new DOMCache();
const debouncer = new Debouncer();
const eventBus = new EventBus();
const animController = new AnimationController();
const storage = new LocalStorageManager('its_group');
const responsive = new ResponsiveManager();

// Make available globally
if (typeof window !== 'undefined') {
  window.AppCore = {
    PerformanceMonitor,
    DOMCache,
    Debouncer,
    EventBus,
    AnimationController,
    ParticleSystem,
    LocalStorageManager,
    PriorityQueue,
    LRUCache,
    Component,
    ResponsiveManager,
    // Instances
    perfMonitor,
    domCache,
    debouncer,
    eventBus,
    animController,
    storage,
    responsive
  };
}
