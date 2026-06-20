const params = new URLSearchParams(location.search);
const testMode = params.get('mode') || 'fixed';

window.__TEST_CONFIG__ = {
    transitionMs: Number(params.get('transition') || 100),
    cycleIntervalMs: Number(params.get('interval') || 300),
    cycles: Number(params.get('cycles') || 94),
    logEvery: Number(params.get('logEvery') || 5),
    mode: testMode,
};

const scripts = [
    testMode === 'legacy' ? './legacy-image.js' : '../scripts/image.js',
    '../scripts/clock.js',
    '../scripts/week.js',
    './harness.js',
];

function loadScripts(index) {
    if (index >= scripts.length) return;
    const script = document.createElement('script');
    script.src = scripts[index];
    script.onload = () => loadScripts(index + 1);
    script.onerror = () => {
        console.error(`TEST_FAIL:failed to load ${scripts[index]}`);
    };
    document.head.appendChild(script);
}

loadScripts(0);
