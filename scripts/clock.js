let size = vh(scopeClock);
const container = document.getElementById('clockContainer');
let classList = ['visible', 'close', 'far', 'far', 'distant', 'distant'];
const colons = [];

function vh(percent) {
    return (percent * window.innerHeight) / 100;
}

function createClock() {
    for (let j = 0; j < 6; j++) {
        let column = document.createElement('div');
        column.classList.add('column');
        let limit = j === 0 ? 3 : 10 - !(j % 2) * 4;
        for (let i = 0; i < limit; i++) {
            let num = document.createElement('div');
            num.classList.add('num');
            num.textContent = i;
            column.appendChild(num);
        }
        container.appendChild(column);

        if (j % 2 === 1 && j < 5) {
            let colon = document.createElement('div');
            colon.classList.add('colon');
            colon.style.transform = `translateY(calc(50vh - ${size / 2}px))`;
            colon.update = () => colon.style.transform = `translateY(calc(50vh - ${size / 2}px))`;
            colons.push(colon);
            container.appendChild(colon);
        }
    }
}

function padClock(p, n) {
    return p + ('0' + n).slice(-2);
}

function getClock() {
    let d = new Date();
    return [use24HourClock ? d.getHours() : d.getHours() % 12 || 12, d.getMinutes(), d.getSeconds()].reduce(padClock, '');
}

function getClass(n, i2) {
    return classList.find((_, classIndex) => Math.abs(n - i2) === classIndex) || '';
}

function updateClock() {
    let columns = Array.from(document.getElementsByClassName('column'));
    let c = getClock();
    columns.forEach((ele, i) => {
        let n = +c[i];
        let offset = -n * size;
        ele.style.transform = `translateY(calc(50vh + ${offset}px - ${size / 2}px))`;
        Array.from(ele.children).forEach((ele2, i2) => {
            ele2.className = 'num ' + getClass(n, i2);
        });
    });
}

createClock();
updateClock()
setInterval(updateClock, 200 + Math.E * 10);