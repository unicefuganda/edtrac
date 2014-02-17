$(document).ready(function(){
    $('#water_source').click(function(){
        $('#general3').hide();
        $('#general1').show();
        $('#general2').show();
    });

    $('#sanitation').click(function(){
        $('#general1').hide();
        $('#general2').hide();
        $('#general3').show();
    });
});