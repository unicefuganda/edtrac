function loadChart(action) {
    $.post(
        action,
        $("#date_range_form").serialize(),
        function(data) {
            
            $('#chart_container').html(data);
        }
    )
}

function tickEvery(num, offset){

    $('.ui-slider span.ui-slider-tic').each(function(index,elem)
    {
        if((index + 1) % (num + offset) == 0)
        {
            $(elem).css('display','block');
        }


    }


            );

}

function previous_date_range(timespan){
	var d = new Date();
	var last_date = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0)
	var last_timestamp = parseInt(last_date.getTime());
	var last_date_index = $('select#end option').index($('select#end option[value='+last_timestamp+']'));
	if(timespan == 'w'){
		var offset = last_date.getDay();
		var end_date = parseInt($('select#end option')[last_date_index-(1+offset)].value);
		var start_date = parseInt($('select#end option')[last_date_index-(7+offset)].value);
	}else{
		var month = last_date.getMonth();
		var year = last_date.getYear();
		var current_month_date = 32 - new Date(year, month, 32).getDate();
		var last_month_last_day = new Date((new Date(year, month,1))-1).getDate();
		var end_date = parseInt($('select#end option')[$('select#end option').length-(1+current_month_date)].value);
		var start_date = parseInt($('select#end option')[$('select#end option').length-(current_month_date+last_month_last_day)].value);
	}
	
//	update the hidden fields
	$('#id_start_ts').val(start_date);
	$('#id_end_ts').val(end_date);
	
//	move slider
	move_slider(start_date, end_date);
}

function move_slider(start, end)
{
    $('select#start option[value='+start+']').attr('selected','selected');
    $('select#end option[value='+end+']').attr('selected','selected');
    $('select#start option').change();
    $('select#end option').change();
    $('form#date_range_form').submit();
}