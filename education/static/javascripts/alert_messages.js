$(document).ready(function(){
    $.ajax({
        url:'/edtrac/error_messages',
contentType: 'application/json'

}).done(function(data){
    if(data.length === 0){
    $("#top_5_error_messages").append('<div class="item">' +
    '<span class="call-out"></span>' +
    '<p class="date">Notice</p>' +
    '<p class="description">There are currently no Alerts to display</p>' +
    '</div>');
    }
$.each(data,function(index,item){
    $("#top_5_error_messages").append('<div class="item">' +
        '<span class="call-out"></span>' +
        '<p class="date">Notice</p>' +
        '<p class="description" style="color:#FF0000">'+item.fields.text+'</p>' +
        '</div>');
    });
});
});
