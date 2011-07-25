function slider_select_box(box_name, min_ts, max_ts, selected){

	//	Hidden Time Slider timestamp selection boxes

	html = '<label for='+box_name+'></label><select name='+box_name+' id='+box_name+' style="display:none;">';
	var min_date = new Date(min_ts);
	var max_date = new Date(max_ts);
	var selected_date = new Date(selected);
	var sel_date = new Date(selected_date.getFullYear(), selected_date.getMonth()+1, selected_date.getDate(), 0, 0, 0, 0);
	var monthNames = new Array('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec');
	for(year = min_date.getFullYear(); year <= max_date.getFullYear(); year++){
		html = html + '<optgroup label="'+year+'">';
		if(year==min_date.getFullYear()){
            for(month = min_date.getMonth()+1; month <= 12; month++){
                html = html + '<optgroup label="'+monthNames[month-1]+'">';
                for(day = 1; day <= 32 - new Date(year, month, 32).getDate(); day++){
                	var day_date = new Date(year, month, day, 0, 0, 0, 0);
                	var day_timestamp = parseInt(day_date.getTime());
                    html = html + '<option value='+day_timestamp+' '+((parseInt(sel_date.getTime()) == day_timestamp)? 'selected="selected"':'')+'>'+day+'-'+monthNames[month-1]+'-'+year+'</option>';
                }
                html = html + '</optgroup>';
            }
		}else if(year==max_date.getFullYear()){
			for(month = 1; month <= max_date.getMonth()+1; month++){
                html = html + '<optgroup label="'+monthNames[month-1]+'">';
                for(day = 1; day <= 32 - new Date(year, month, 32).getDate(); day++){
                	var day_date = new Date(year, month, day, 0, 0, 0, 0);
                	var day_timestamp = parseInt(day_date.getTime());
                    html = html + '<option value='+day_timestamp+' '+((parseInt(sel_date.getTime()) == day_timestamp)? 'selected="selected"':'')+'>'+day+'-'+monthNames[month-1]+'-'+year+'</option>';
                }
                html = html + '</optgroup>';
            }	
		}else{
			for(month = 1; month <= 12; month++){
                html = html + '<optgroup label="'+monthNames[month-1]+'">';
                for(day = 1; day <= 32 - new Date(year, month, 32).getDate(); day++){
                	var day_date = new Date(year, month, day, 0, 0, 0, 0);
                	var day_timestamp = parseInt(day_date.getTime());
                    html = html + '<option value='+day_timestamp+' '+((parseInt(sel_date.getTime()) == day_timestamp)? 'selected="selected"':'')+'>'+day+'-'+monthNames[month-1]+'-'+year+'</option>';
                }
                html = html + '</optgroup>';
            }
		}
		html = html + '</optgroup>';
	}
	html = html + '</select>';
	return html;
}

function selected_layer(data){
	$('#date_slider').append('<input type="hidden" class="layer_data" name="layer_data" value="'+data+'" />');
}

function submit_date_range(){
	var selected_start_date = $("select#start option:selected").val();
	var selected_end_date = $("select#end option:selected").val();
	var map_id = 'map';
	var layer_name = 'muac';
	var layer_url = '/cvs/stats/'+selected_start_date+'/'+selected_end_date+'/'+layer_name+'/';
	plot_layer(map_id, layer_name, layer_url);
}

function tickEvery(num, offset){

    $('.ui-slider span.ui-slider-tic').each(function(index,elem){
        if((index + 1) % (num + offset) == 0){
            $(elem).css('display','block');
        }
    });
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