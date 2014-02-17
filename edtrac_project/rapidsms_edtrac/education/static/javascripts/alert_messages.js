$(document).ready(function(){
    $.ajax({
        url:'/edtrac/error_messages',
contentType: 'application/json'

}).done(function(data){
    if(data.length === 0){
    $("#top_5_error_messages").append('<div>' +
    '<p style="color:#468847;"">No alerts to display</p>' +
    '</div>');
    }    
$.each(data,function(index,item){
    $("#top_5_error_messages").append('<div>' +
    '<ul class="unstyled">' +
    '<li style="color:#b94a48;"">'+item.fields.text+'</li>' +
    '</ul>' +
    '</div>');
    });
});
});
