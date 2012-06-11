function deleteReporter(elem, pk, name, url) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('tr').remove();
        $.post(url, function(data) {});
//        $.post('../reporter/' + pk + '/delete/', function(data) {});
    }
}

function editReporter(elem, pk, url) {
    overlay_loading_panel($(elem).parents('tr'));
    $(elem).parents('tr').load(url, '', function () {
//    $(elem).parents('tr').load('../reporter/' + pk + '/edit/', '', function () {
        $('#div_panel_loading').hide();    
    });
}

function submitForm(link, action, resultDiv) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultDiv.load(action, form_data);
}

function deleteConnection(elem,link,name) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('p').remove();
        $.post(link, function(data) {});
    }
}

function newConnection(elem, link) {
	$('#add_contact_form').load(link);
    $('#add_contact_anchor_row').hide();
}

function scheduleSpecialScriptTermly(elem, link){
    $('#myModal').modal('show');
}

function scheduleSpecialScriptMonthly(elem, link){
    alert('hello');
}


function addNumbers(elem, action) {
    form = $(elem).parents("form");
    form_data = form.serializeArray();
    $('#add_contact_form').load(action, form_data);
}

function addPhoneElm(elem){
	rowelem = $(elem).parents('tr')
    rowelem.after('<tr></tr>')
    rowelem.next().html('<td>Phone Number: </td><td><input name="other_nums" /></td>');
}