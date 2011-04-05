function ajax_loading(element) {
    var t = $(element);
    var offset = t.offset();
    var dim = {
        left:    offset.left,
        top:    offset.top,
        width:    t.outerWidth(),
        height:    t.outerHeight()
    };
    $('<div class="ajax_loading"></div>').css({
        position:    'absolute',
        left:        dim.left + 'px',
        top:        dim.top + 'px',
        width:        dim.width + 'px',
        height:        dim.height + 'px'
    }).appendTo(document.body).show();


}
function loadModule(elem, module_name) {
    var to_element=$('#mod').find('.column')[0];
    ajax_loading(to_element);
    form = $('#form_' + module_name);
    form.children('.input_action').val('createmodule');
    form.children('.input_module_type').val($('#select_module').val());
    form_data = form.serializeArray();
    $.post('./', form_data, function(data, i, j) {
            $(to_element).append(data);
    });
     $('.ajax_loading').remove();
}

function removeDiv(elem) {
    $(elem).remove();
    sync_data();
}

function sync_data() {
    var columns = $('.column');
    var col_orders = [];
    jQuery.each(columns, function(key, value) {
        var mods = $('#' + value.id).sortable('toArray');
        jQuery.each(mods, function(k, v) {
            col_orders.push(key + '=' + v);
        });
    });
    var data = col_orders.join('&');
    $.post("./", data);
}

function make_draggable() {
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
        start: function (e, ui) {
            $(ui.helper).addClass('dragging');
            var orig = ui.item;
        },
        stop: function (e, ui) {
            $(ui.item).css({width:''}).removeClass('dragging');
            $('.column').sortable('enable');
        },
        update: function(e, ui) {
            sync_data();
        }
    });
}

