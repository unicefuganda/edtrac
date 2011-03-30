function removeDiv(elem){
    return $(this).remove();
}
$(function() {
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
                   col_orders.push(key+'=' + v);

                });
            });
            var data = col_orders.join('&');
            $.post("/cvs/dashboard/", data);
        }
    });
});

