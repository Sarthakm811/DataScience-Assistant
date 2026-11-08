import '@testing-library/jest-dom/vitest'

Object.defineProperty(window, 'sessionStorage', {
    value: {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {}
    },
    configurable: true
})

globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
}
