let daySize = vh(scopeLetters);
let dayClassList = ['visible', 'close', 'far', 'far', 'distant', 'distant'];
const dayContainer = document.getElementById('dayContainer');

const daysOfWeek = {
    ru: ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
    eng: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
};
const lang = () => useEnglishVersion ? "eng" : "ru";


const positionMap = {};

function createDayClock() {
    const maxLength = Math.max(...daysOfWeek[lang()].map((d) => d.length));
    for (let pos = 0; pos < maxLength; pos++) {
        positionMap[pos] = new Set();
        daysOfWeek[lang()].forEach((day) => {
            if (pos < day.length) {
                positionMap[pos].add(day[pos]);
            }
        });
    }
    dayContainer.innerHTML = "";
    for (let pos = 0; pos < maxLength; pos++) {
        let column = document.createElement('div');
        column.classList.add('dayColumn');
        column.dataset.position = pos;

        let letters = Array.from(positionMap[pos]).sort();
        letters.forEach((letter) => {
            let letterDiv = document.createElement('div');
            letterDiv.classList.add('dayLetter');
            letterDiv.textContent = letter;
            letterDiv.dataset.letter = letter;
            column.appendChild(letterDiv);
        });

        dayContainer.appendChild(column);
    }
}

function getCurrentDay() {
    let d = new Date();
    let dayIndex = d.getDay();
    dayIndex = dayIndex === 0 ? 6 : dayIndex - 1;
    return daysOfWeek[lang()][dayIndex];
}

function getDayClass(letter, targetLetter, index, targetIndex) {
    if (letter === targetLetter && index === targetIndex) {
        return dayClassList[0];
    }
    let distance = Math.abs(index - targetIndex);
    return dayClassList[distance] || '';
}

function updateDayClock() {
    let columns = Array.from(document.getElementsByClassName('dayColumn'));
    let currentDay = getCurrentDay();

    columns.forEach((column, pos) => {
        if (pos >= currentDay.length) {
            column.style.transform = `translateY(calc(50vh - ${daySize / 2}px))`;
            Array.from(column.children).forEach((letterDiv) => {
                letterDiv.className = 'dayLetter';
            });
            return;
        }

        let targetLetter = currentDay[pos];
        let letters = Array.from(column.children);
        let targetIndex = letters.findIndex((l) => l.dataset.letter === targetLetter);
        if (targetIndex === -1) return;

        let offset = -targetIndex * daySize;
        column.style.transform = `translateY(calc(50vh + ${offset}px - ${daySize / 2}px))`;

        letters.forEach((letterDiv, index) => {
            letterDiv.className = 'dayLetter ' + getDayClass(letterDiv.dataset.letter, targetLetter, index, targetIndex);
        });
    });
}

let lastDay = null;


function checkAndUpdateDay() {
    let currentDay = getCurrentDay();
    if (currentDay !== lastDay) {
        lastDay = currentDay;
        updateDayClock();
    }
}

