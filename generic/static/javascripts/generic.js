function filter(elem) {
    form = $(elem).parents("form");
    form_data = form.serializeArray();
    $('#object_list').load("./", form_data);
}

function page(elem, num) {
    $('#input_page_num').val(num);
    $('#input_page_action').val('true');
    filter(elem);
}

function action(elem, action) {
    $('#input_action').val(action);
    filter(elem);
}