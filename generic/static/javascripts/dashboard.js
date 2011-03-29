
function addModule(column,url,title,pk)
{
  //create module div
 var module_head="";
 var module_content=$("<div>").addClass('widget-content').load(url);
   var widget=$("<div>").addClass("widget").attr('id','mod'+String(pk)).appendTo("#"+column);
   var title="<h3>"+title+"<a href='javascript:void(0)' class='close'>[X]</a></h3>";
   $("<div>").addClass("widget-head  module").append(title).appendTo(widget).append(module_content);

}
function removeDiv(elem){
    return $(this).remove();
}
$(function() {



addModule('column3','/cvs/charts/1/epi/ma/','Malaria Stats')

$('.column').sortable({
            items: '> div',
            connectWith: $('.column'),
            handle: '.widget-head',
            placeholder: 'widget-placeholder',
            forcePlaceholderSize: true,
            delay: 100,
            opacity: 0.8,
            dropOnEmpty: true,
            containment: 'document',
            start: function (e,ui) {
                $(ui.helper).addClass('dragging');
                var orig=ui.item;
            },
            stop: function (e,ui) {
                $(ui.item).css({width:''}).removeClass('dragging');
                $('.column').sortable('enable');
            },
            update: function(e, ui) {
                
                var columns=$('.column');
                var col_orders=[];
                jQuery.each(columns, function(key,value)
                {
                    
                    var mods=$('#'+value.id).sortable('toArray');
                    jQuery.each(mods,function(k,v)
                    {
                       col_orders.push('col'+key+1+'[' + k + ']=' + v);

                    });
                });

                var data = col_orders.join('&');
                $.post("/cvs/dashboard", data);

                
            }
        });

    
  });

