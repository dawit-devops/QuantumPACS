// Minimal browser-safe polyfill for Node's `events` builtin.
// xmlbuilder2 (pulled in via the Cornerstone3D dependency graph) declares
// `class XMLBuilderCBImpl extends EventEmitter` at module scope. Vite
// externalizes Node builtins to an empty proxy for the browser, so without a
// real binding that declaration throws "Class extends value undefined" and
// the whole prebundled cornerstone chunk fails to load in dev and in the
// production build. Only the parts of the EventEmitter API that XML
// streaming emits/observes are needed at runtime; everything else is a
// no-op-safe stub.
class EventEmitter {
  constructor() {
    this._events = new Map();
  }

  on(type, listener) {
    if (!this._events.has(type)) this._events.set(type, new Set());
    this._events.get(type).add(listener);
    return this;
  }

  addListener(type, listener) {
    return this.on(type, listener);
  }

  once(type, listener) {
    const wrapper = (...args) => {
      this.removeListener(type, wrapper);
      listener.apply(this, args);
    };
    wrapper.listener = listener;
    return this.on(type, wrapper);
  }

  off(type, listener) {
    this._events.get(type)?.delete(listener);
    return this;
  }

  removeListener(type, listener) {
    return this.off(type, listener);
  }

  removeAllListeners(type) {
    if (type === undefined) this._events.clear();
    else this._events.delete(type);
    return this;
  }

  emit(type, ...args) {
    for (const listener of [...(this._events.get(type) ?? [])]) {
      listener.apply(this, args);
    }
    return true;
  }

  listeners(type) {
    return [...(this._events.get(type) ?? [])];
  }

  listenerCount(type) {
    return this._events.get(type)?.size ?? 0;
  }

  setMaxListeners() {
    return this;
  }

  getMaxListeners() {
    return 10;
  }

  prependListener(type, listener) {
    if (!this._events.has(type)) this._events.set(type, new Set());
    const set = this._events.get(type);
    set.delete(listener);
    set.add(listener);
    return this;
  }
}

export default EventEmitter;
export { EventEmitter };
export function once(emitter, name) {
  return new Promise((resolve, reject) => {
    const handler = (...args) => {
      emitter.removeListener(name, handler);
      emitter.removeListener("error", errorHandler);
      resolve(args);
    };
    const errorHandler = (err) => {
      emitter.removeListener(name, handler);
      reject(err);
    };
    emitter.once(name, handler);
    emitter.once("error", errorHandler);
  });
}
