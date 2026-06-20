const { transitionMs, cycleIntervalMs, cycles, logEvery, mode } = window.__TEST_CONFIG__;

const dayImages = Array.from({ length: 56 }, (_, i) => `../day/${i}.png`);
const nightImages = Array.from({ length: 39 }, (_, i) => `../night/${i}.png`);
const allImages = [...dayImages, ...nightImages];

let cycle = 0;
let finished = false;

window.__TEST_STATE__ = {
    cycle,
    finished,
    mode,
    memlogs: [],
};

function logMemory(label) {
    const state = getWallpaperState();
    const mem = performance.memory
        ? {
              usedJSHeapSize: performance.memory.usedJSHeapSize,
              totalJSHeapSize: performance.memory.totalJSHeapSize,
              jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
          }
        : null;

    const payload = {
        type: 'memlog',
        label,
        cycle,
        mode,
        transitionMs,
        cycleIntervalMs,
        timestamp: Date.now(),
        currentSrc: state.currentSrc,
        transitioning: state.transitioning,
        firstImageSrc: state.firstImageSrc,
        secondImageSrc: state.secondImageSrc,
        mem,
    };

    console.log(`MEMLOG:${JSON.stringify(payload)}`);
    window.__TEST_STATE__.cycle = cycle;
    window.__TEST_STATE__.memlogs.push(payload);
    return payload;
}

function finishTest() {
    if (finished) return;
    finished = true;
    logMemory('done');
    window.__TEST_STATE__.finished = true;
    window.__TEST_STATE__.cycle = cycle;
    console.log(`TEST_DONE:${JSON.stringify({ cycle, mode, cycles })}`);
}

function nextCycle() {
    if (finished || transitioning) return;

    cycle += 1;
    const src = allImages[(cycle - 1) % allImages.length];
    newImage(src);

    if (cycle % logEvery === 0 || cycle === 1 || cycle === cycles) {
        logMemory('tick');
    }

    if (cycle >= cycles) {
        setTimeout(finishTest, transitionMs + 100);
    }
}

setImage(allImages[0]);
logMemory('start');

setInterval(nextCycle, cycleIntervalMs);
