function filter(elem) {
    form = $(elem).parents("form");
    form_data = form.serializeArray();
    $('#div_results_loading').show();
    $('#object_list').load("./", form_data, function() {
        $('#div_results_loading').hide();
    });
}

function overlay_loading_panel(elem) {
    var off = elem.offset();
    var parent_off = $('#div_panel_loading').parent().offset();
    $('#div_panel_loading').css({
        left:   (off.left - parent_off.left) + 'px',
        top:    (off.top - parent_off.top) + 'px',
        width:  elem.outerWidth() + 'px',
        height: elem.outerHeight() + 'px'
    })
    $('#div_panel_loading').show();
}

function page(elem, num) {
    $('#input_page_num').val(num);
    $('#input_page_action').val('true');
    filter(elem);
}

function sort(elem, col, ascending) {
    $('#input_sort_column').val(col);
    $('#input_sort_action').val('true');
    $('#input_sort_ascending').val(ascending);
    filter(elem);
}

function action(elem, action) {
   
    if (!($(elem).is('.delete')) ||
            (confirm("Are you sure?"))) {

        $('#input_action').val(action);
        form = $(elem).parents("form");
        form_data = form.serializeArray();
        $('#div_results_loading').show();
        overlay_loading_panel($('#actions'));
        $('#object_list').load("./", form_data, function() {
            $('#div_results_loading').hide();
            $('#div_panel_loading').hide();
        });
    }
    else {
        //user clicked no
    }
}

function select_all() {
    if ($('#input_select_all').attr('checked')) {
        $('#span_select_everything').show();
        $('input:checkbox[name=results]').attr('checked', 'checked');
    } else {
        $('#span_select_everything').hide();
        $('input:checkbox[name=results]').attr('checked', false);
    }
}

function deselect_all() {
    $('#input_select_all').attr('checked', false);
    $('#span_select_everything').hide()
}

function select_everything(count) {
    $('#input_select_everything').val('true');
    $('#span_select_everything').html('All ' + count + ' items are selected. <a href="javascript:void(0)" onclick="deselect_everything(' + count + ')">Clear selection</a>');
}

function deselect_everything(count) {
    $('#input_select_everything').val('');
    $('#span_select_everything').html('You have selected all items on this page.  <a href="javascript:void(0)" onclick="select_everything(' + count + ')">Click here</a> to select all ' + count + ' items.');
    $('#input_select_all').attr('checked', false);
    select_all();
}

function disable_enter() {
    if ($.browser.mozilla) {
        $('#filters input:text').keypress(function(event) {
            if (event.keyCode == 13) return false;
        });
        $('#actions input:text').keypress(function(event) {
            if (event.keyCode == 13) return false;
        });
    } else {
        $('#filters input:text').keydown(function(event) {
            if (event.keyCode == 13) return false;
        });
        $('#actions input:text').keydown(function(event) {
            if (event.keyCode == 13) return false;
        });
    }
}
