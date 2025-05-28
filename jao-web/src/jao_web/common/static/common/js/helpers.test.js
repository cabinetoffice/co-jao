import { onAriaSelected, onDOMContentLoaded } from './helpers'

describe('onAriaSelected', () => {
  let element
  let callback
  beforeEach(() => {
    element = document.createElement('div')
    callback = vi.fn()
  })
  test('triggers callback when aria-selected becomes true', async () => {
    onAriaSelected(element, callback)
    element.setAttribute('aria-selected', 'true')
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(callback).toHaveBeenCalledTimes(1)
  })
  test('triggers callback if initially selected', () => {
    element.setAttribute('aria-selected', 'true')
    onAriaSelected(element, callback)
    expect(callback).toHaveBeenCalledTimes(1)
  })
  test('handles null element gracefully', () => {
    const consoleSpy = vi.spyOn(console, 'warn')
    onAriaSelected(null, callback)
    expect(consoleSpy).toHaveBeenCalledWith('Tab element not found')
    expect(callback).not.toHaveBeenCalled()
  })
  test('disconnect works', () => {
    const disconnect = onAriaSelected(element, callback)
    disconnect()
    element.setAttribute('aria-selected', 'true')
    expect(callback).not.toHaveBeenCalled()
  })
})

describe('onDOMContentLoaded', () => {
  let callback

  beforeEach(() => {
    callback = vi.fn()
  })

  test('calls callback immediately if DOM is already loaded', () => {
    // Mock document.readyState as 'complete'
    Object.defineProperty(document, 'readyState', {
      configurable: true,
      get: vi.fn(() => 'complete')
    })

    onDOMContentLoaded(callback)
    expect(callback).toHaveBeenCalledTimes(1)
  })

  test('calls callback immediately if DOM is interactive', () => {
    // Mock document.readyState as 'interactive'
    Object.defineProperty(document, 'readyState', {
      configurable: true,
      get: vi.fn(() => 'interactive')
    })

    onDOMContentLoaded(callback)
    expect(callback).toHaveBeenCalledTimes(1)
  })

  test('adds event listener if DOM is loading', () => {
    // Mock document.readyState as 'loading'
    Object.defineProperty(document, 'readyState', {
      configurable: true,
      get: vi.fn(() => 'loading')
    })

    const addEventListenerSpy = vi.spyOn(document, 'addEventListener')

    onDOMContentLoaded(callback)

    // Check that addEventListener was called with correct parameters
    expect(addEventListenerSpy).toHaveBeenCalledWith('DOMContentLoaded', callback)
    expect(callback).not.toHaveBeenCalled()

    // Simulate DOMContentLoaded event
    const event = new Event('DOMContentLoaded')
    document.dispatchEvent(event)

    expect(callback).toHaveBeenCalledTimes(1)
  })
})