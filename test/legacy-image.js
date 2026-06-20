const image = document.getElementById('firstImage');
const secondImage = document.getElementById('secondImage');

const TRANSITION_MS = window.__TEST_CONFIG__?.transitionMs ?? 3000;

let currentSrc = '';
let transitioning = false;

function newImage(src) {
    if (!src || transitioning || src === currentSrc) return;

    transitioning = true;
    secondImage.src = src;
    secondImage.onload = () => {
        image.classList.add('hide');
        setTimeout(() => {
            image.classList.remove('hide');
            image.src = src;
            currentSrc = src;
            transitioning = false;
        }, TRANSITION_MS);
    };
    secondImage.onerror = () => {
        transitioning = false;
    };
}

function setImage(src) {
    if (!src) return;
    image.classList.remove('hide');
    image.src = src;
    currentSrc = src;
    transitioning = false;
}

function getWallpaperState() {
    return {
        currentSrc,
        transitioning,
        firstImageSrc: image.src,
        secondImageSrc: secondImage.src,
    };
}
