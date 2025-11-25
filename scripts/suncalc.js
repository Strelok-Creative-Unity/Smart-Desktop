async function sunProgress() {
    const now = new Date();
    const times = SunCalc.getTimes(now, latitude, longitude);

    let start, end, time;

    if (now > times.sunrise && now < times.sunset) {
        start = times.sunrise;
        end = times.sunset;
        time = true;
    } else if (now > times.sunset) {
        const nextDay = new Date(now);
        nextDay.setDate(now.getDate() + 1);
        const nextSunrise = SunCalc.getTimes(nextDay, latitude, longitude).sunrise;
        start = times.sunset;
        end = nextSunrise;
        time = false;
    } else if (now < times.sunrise) {
        const previousDay = new Date(now);
        previousDay.setDate(now.getDate() - 1);
        const previousSunset = SunCalc.getTimes(previousDay, latitude, longitude).sunset;
        start = previousSunset;
        end = times.sunrise;
        time = false;
    }

    return [Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100)), time];
}

const images = {
    night: new Array(38).fill(undefined).map((_, i, array) => ({
        src: `night/${i}.png`,
        index: i,
        percentage: ((i + 1) / array.length) * 100,
    })),
    day: new Array(56).fill(undefined).map((_, i, array) => ({
        src: `day/${i}.png`,
        index: i,
        percentage: ((i + 1) / array.length) * 100,
    })),
    current: null,
    currentIsDay: null,
};

function getNewLast(isDay, percent) {
    let i = 0;
    while (images[isDay ? 'day' : 'night'][i].percentage < percent) i++;
    return images[isDay ? 'day' : 'night'][i];
}

async function initializeImage() {
    try {
        const [percent, isDay] = await sunProgress();

        const initImage = getNewLast(isDay, percent);

        images.current = initImage;
        images.currentIsDay = isDay;

        image.src = initImage.src;

    } catch (error) {
        console.error("Ошибка при инициализации изображения:", error);
    }
}

async function updateProgress() {
    try {
        const [percent, isDay] = await sunProgress();
        if (percent > images.current?.percentage || images.currentIsDay !== isDay) {
            if (images.currentIsDay !== isDay) {
                images.currentIsDay = isDay;
                const last = getNewLast(isDay, percent);
                newImage(last.src);
                images.current = last;
                return;
            } else {
                const last = images[isDay ? 'day' : 'night'][images.current.index + 1];
                newImage(last.src);
                images.current = last;
            }
        }
    } catch (error) {
        console.error(error.stack);
    }
}
