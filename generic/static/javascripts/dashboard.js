
function addModule(column,url,title)
{
  //create module div
 var module_head="";
 var module_content=$("<div>").addClass('widget-content').load(url);
   var widget=$("<div>").addClass("widget").appendTo("#"+column);
   var title="<h3>"+title+"<a href='javascript:void(0)' class='close'>[X]</a></h3>";
   $("<div>").addClass("widget-head  module").append(title).appendTo(widget).append(module_content);

}
function removeDiv(this){
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
            revert: true,
            delay: 100,
            opacity: 0.8,
            cancel: 'button',
            dropOnEmpty: false,
            containment: 'document',
            start: function (e,ui) {
                $(ui.helper).addClass('dragging');
            },
            stop: function (e,ui) {
                $(ui.item).css({width:''}).removeClass('dragging');
                $('.column').sortable('enable');
                $col_orders=$("#column1").sortable("serialize",{key:"column1",attribute:'id'}) + "&" + $("#column2").sortable("serialize", {key:"column2",attribute:'id'})+ "&" + $("#column3").sortable("serialize", {key:"column3",attribute:'id'});


                alert($col_orders);

            }
        });

    
  });

