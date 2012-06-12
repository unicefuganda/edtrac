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

function scheduleSpecialScript(elem, link){
    var atLeastOneIsChecked = $('input[name="results"]:checked').length > 0
    var allChecked = $('input[id=input_select_all]:checked').length > 0
    if (allChecked || atLeastOneIsChecked){
        if(allChecked){
            checked = 'all'
        }else if(atLeastOneIsChecked){
            // checked = $('input[name="results"]:checked');
            checked_boxes = new Array()
            checked = $('input[type=checkbox]:checked')
            tmp_var = ''
            checked.each(function(index) {
                checked_boxes = $(this).val()
                //tmp_var += '<input type="hidden" name="checked_' + checked_boxes +'" value="'+checked_boxes +'"/>'
                tmp_var += '<input type="hidden" name="checked_numbers" value="'+checked_boxes +'"/>'
                $('div#selected_reporters').html(tmp_var)
            })

        }
        $('#myModal').modal('show') // show modal when all validated
    }else{
        alert("Select at least one reporter before clicking this button!")
    }
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