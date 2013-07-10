function deleteSchool(elem, pk, name, url) {
	alert('here');
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('tr').remove();
        $.post(url, function(data) {});
    }
}

function editSchool(elem, pk, url) {
    overlay_loading_panel($(elem).parents('tr'));
    $(elem).parents('tr').load(url, '', function () {
        $('#div_panel_loading').hide();    
    });
}

function submitForm(link, action, resultDiv) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultDiv.load(action, form_data);
}

function deleteSchool(elem,link,name) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('p').remove();
        $.post(link, function(data) {});
    }
}

function newSchool(elem, link) {
	$('#add_school_form').load(link);
    $('#add_school_anchor_row').hide();
}

function addSchools(elem, action) {
    form = $(elem).parents("form");
    form_data = form.serializeArray();
    $('#add_school_form').load(action, form_data);
}

function addSchoolElm(elem){
	rowelem = $(elem).parents('tr')
    rowelem.after('<tr></tr>')
    name_form = $('#name_elms').html()
    location_form = $('#location_elms').html()
    id_form = $('#id_elms').html()
    rowelem.next().html('<td>Name: </td><td>'+name_form+'</td><td>Location: </td><td>'+location_form+'</td>');
}

function getStats(url){
    start_date = new Date(parseInt($('select#start').val())*1000);
    end_date = new Date(parseInt($('select#end').val())*1000);
    start_str = start_date.getFullYear() + "-" + (start_date.getMonth() + 1) + "-" + start_date.getDate();
    end_str =  end_date.getFullYear() + "-" + (end_date.getMonth() + 1) + "-" + end_date.getDate();
    url = url+start_str+'/'+end_str;
    window.location.href=url;
}

function reschedule_polls(url, x){
    $('#'+x+'_results').html('Loading...')
    $('#'+x+'_results').load(url)
}

function check_clicked(clicked){
    // alert($(clicked).parents('form').attr('id'))
    $(clicked).parents('form').submit()
    
}
