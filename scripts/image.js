const image = document.getElementById('firstImage');
const secondImage = document.getElementById('secondImage');

function newImage(src) {
    if (!src) return;
    secondImage.src = src;
    secondImage.onload = () => {
        image.classList.add('hide');
        setTimeout(() => {
            image.classList.remove('hide');
            image.src = src;
        }, 3000);
    };
}