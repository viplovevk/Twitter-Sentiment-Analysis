
function loader(seconds){
  let atPercent = 0;
  var x = document.getElementById("myProgress");
  x.style.display = "block";
  const bar = document.getElementById("myBar")
  const interval = setInterval(() => {
    bar.style.width = atPercent + '%';
    atPercent++;
    console.log('clicked')
    if (atPercent == 100) {
      x.innerHTML = "Tweets loaded from spark & processing. . .";
      clearInterval(interval)
    }
  }, (seconds * 1000)/100)
}