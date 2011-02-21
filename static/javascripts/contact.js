function toggle_select_all() {
    $('#users ul').find('input').each(
        function(){
            if(!$(this).attr("checked")) {
		        $(this).attr("checked",true);
	        } else {
			    $(this).attr("checked",false);
			}
        }
    );
}

function load_users() {
    $('#new_contact').hide();
    $('#users').show();
}

function load_contacts() {
    $('#contacts_list').load('/contact/contact_list')
}

function load_new() {
    $('#users').hide();
    $('#new_contact').load('/contact/new/');
    $('#new_contact').show();
}

function load_page(page_no) {
    var page="/contact/contact_list?page="+page_no
    $('#contacts_list').load(page);
}

function filter_contacts(elem) {
    form = $(elem).parents("form");
    form_data = form.serializeArray();
    $('#contacts_list').load(form.attr("action"), form_data, function() {
    });
}

$(document).ready(function() {
    //load_contacts();
});


