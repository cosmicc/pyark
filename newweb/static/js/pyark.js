function starttimer() {
    var sec, pTimer = null;
    starttimer = function() {
        sec = 0;
        clearInterval(pTimer);
        pTimer = setInterval( function(){
            $("#seconds").html(++sec);
            if (sec == -1) {
                clearInterval(pTimer);
            }
        }, 1000);
    };
    starttimer();
    }