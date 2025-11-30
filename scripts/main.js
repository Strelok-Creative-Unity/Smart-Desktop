
update();
function update() {
    dayContainer.style.fontSize = scopeLetters + "vh";
    dayContainer.style.lineHeight = scopeLetters + "vh";

    clockContainer.style.fontSize = scopeClock + "vh";
    clockContainer.style.lineHeight = scopeClock + "vh";
    
    size = vh(scopeClock);
    daySize = vh(scopeLetters);
    colons.forEach(el => el.update());


    createDayClock();
    updateDayClock();
    lastDay = getCurrentDay();


    createClock();
    updateClock();



    setPosition();
}



window.onresize = () => {
    size = vh(scopeClock);
    daySize = vh(scopeLetters);
    colons.forEach(el => el.update());
    updateDayClock();
    setPosition();
};

initializeImage().then(() => {
    setPosition();
    updateProgress();
});
setInterval(() => {updateProgress();}, 4000);


setInterval(updateClock, 200 + Math.E * 10);
setInterval(checkAndUpdateDay, 1000);

function setPosition() {
    clockContainer.style.right = clockRight + "px";
    clockContainer.style.top = - clockContainer.offsetHeight * 0.8 + clockTop + "px";


    dayContainer.style.left = weekLeft + "px";
    dayContainer.style.top = - dayContainer.offsetHeight + weekTop + "px";
}

function setSizes(){

}