function toggle_select_all()
{
    $('#users ul').find('input').each(function(){

        if(!$(this).attr("checked"))
			    {

				 $(this).attr("checked",true);

			    }
			 else{
				 $(this).attr("checked",false);
			 }




    });
}

function load_users(){
    $('#new_contact').hide();
    $('#users').show();


}

function load_contacts(){
   $('#contacts_list').load('/contact/contact_list')
}
function load_new(){

    $('#users').hide();
    $('#new_contact').load('/contact/new/');
    $('#new_contact').show();


}

$(document).ready(function() {
 load_contacts();

});
