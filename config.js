let latitude = 40, longitude = 30,
  scopeClock = 5, scopeLetters = 5,
  use24HourClock = true,
  clockRight = 0, clockTop = 0,
  weekLeft = 0, weekTop = 0,
  useEnglishVersion = true;

window.wallpaperPropertyListener = {
  applyUserProperties(props) {
    if (props.latitude) latitude = props.latitude.value;
    if (props.longitude) longitude = props.longitude.value;
    if (props.scopeClock) scopeClock = props.scopeClock.value;
    if (props.scopeLetters) scopeLetters = props.scopeLetters.value;
    if (props.use24HourClock) use24HourClock = props.use24HourClock.value;
    if (props.clockRight) clockRight = props.clockRight.value;
    if (props.clockTop) clockTop = props.clockTop.value;
    if (props.weekLeft) weekLeft = props.weekLeft.value;
    if (props.weekTop) weekTop = props.weekTop.value;
    if (props.useEnglishVersion) useEnglishVersion = props.useEnglishVersion.value;
    update();
  }
};