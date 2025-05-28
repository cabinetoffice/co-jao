export const onAriaSelected = (element, callback) => {
    /**
     * When aria-selected on an element is true, trigger a callback.
     *
     * @param {HTMLElement} element - The element to observe.
     * @param {Function} callback - The callback to trigger.
     */
    if (!element) {
        console.warn(`Tab element not found`);
        return;
    }
    const observer = new MutationObserver(() => {
        const isSelected = element.getAttribute('aria-selected') === 'true';
        if (isSelected) {
            callback();
        }
    });
    observer.observe(element, {
        attributes: true,
        attributeFilter: ['aria-selected']
    });
    // On initialisation trigger the callback if the element is selected:
    if (element.getAttribute('aria-selected') === 'true') {
        callback();
    }
    return () => observer.disconnect();
};

export const onDOMContentLoaded = (callback) => {
    /**
     * Execute a callback when DOM content is loaded.
     * If DOM is already loaded, executes callback immediately.
     *
     * @param {Function} callback - The callback to trigger.
     */
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        callback();
    } else {
        document.addEventListener('DOMContentLoaded', callback);
    }
};