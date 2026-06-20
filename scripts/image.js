const image = document.getElementById('firstImage');
const secondImage = document.getElementById('secondImage');

const BLANK_IMAGE = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
const TRANSITION_MS = 3000;

let currentSrc = '';
let transitioning = false;

function releaseImage(img) {
    img.onload = null;
    img.src = BLANK_IMAGE;
}

function newImage(src) {
    if (!src || transitioning || src === currentSrc) return;

    transitioning = true;
    secondImage.onload = () => {
        image.classList.add('hide');
        setTimeout(() => {
            image.classList.remove('hide');
            image.src = src;
            currentSrc = src;
            releaseImage(secondImage);
            transitioning = false;
        }, TRANSITION_MS);
    };
    secondImage.onerror = () => {
        releaseImage(secondImage);
        transitioning = false;
    };
    secondImage.src = src;
}

function setImage(src) {
    if (!src) return;
    releaseImage(secondImage);
    image.classList.remove('hide');
    image.src = src;
    currentSrc = src;
    transitioning = false;
}
