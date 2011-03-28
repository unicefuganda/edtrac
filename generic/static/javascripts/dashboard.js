
function addModule(column,url,title)
{
  //create module div
 var module_head="";
 var module_content=$("<div>").addClass('widget-content').load(url);
   var widget=$("<li>").addClass("widget").appendTo("#"+column);
   var title="<h3>"+title+"<a href='javascript:void(0)' class='close'>[X]</a></h3>";
   $("<div>").addClass("widget-head  module").append(title).appendTo(widget).append(module_content);

}
$(function() {



addModule('column3','/cvs/charts/1/epi/ma/','Malaria Stats')

$('.column').sortable({
            items: '> li',
            connectWith: $('.column'),
            handle: '.widget-head',
            placeholder: 'widget-placeholder',
            forcePlaceholderSize: true,
            revert: 300,
            delay: 100,
            opacity: 0.8,
            containment: 'document',
            start: function (e,ui) {
                $(ui.helper).addClass('dragging');
            },
            stop: function (e,ui) {
                $(ui.item).css({width:''}).removeClass('dragging');
                $('.column').sortable('enable');
            }
        });

    
  });

