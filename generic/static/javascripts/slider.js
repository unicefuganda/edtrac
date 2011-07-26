var update_date_layers = null;

function init_timeslider(min_ts) {
    //initialise ui slider
	$('select#start, select#end').selectToUISlider({
        labels: 0,
		sliderOptions: {
		    change:on_timeslider_change
        }
	});

	// Make tick marks at every Monday on the
	// time slider UI
	min_sdt = new Date(min_ts);
    tickEvery(7, min_sdt.getDay() - 1);

    // trigger the slider's label to update
    $('select#end option').change();
}


function on_timeslider_change(event, element) {
    start_date = new Date(parseInt($('select#start option').eq(element.values[0])[0].value));
    end_date = new Date(parseInt($('select#end option').eq(element.values[1])[0].value));

    start_str = start_date.getDate() + "-" + (start_date.getMonth() + 1) + "-" + start_date.getFullYear();
    end_str = end_date.getDate() + "-" + (end_date.getMonth() + 1) + "-" + end_date.getFullYear();	
	$( "#date_slider_value" ).text( "From " + start_str + " to " + end_str );
}


function tickEvery(num, offset){
    $('.ui-slider span.ui-slider-tic').each(function(index,elem){
        if (((index + offset) % num) == 0) {
            $(elem).css('display','block');
        }
    });
}


var DAY_MS = 86400000;

function previous_date_range(timespan) {
	now = new Date();
	base = new Date(now.getFullYear(), now.getMonth(), now.getDate());
	switch (timespan) {
	case 'w':
		end_date = base;
		while (end_date.getDay() != 0) {
			end_date = new Date(end_date.getTime() - DAY_MS);
		}
		start_date = new Date(end_date.getTime() - (7 * DAY_MS));
		move_slider(start_date, end_date);
		break;
	case 'm':
		end_date = new Date(base.getFullYear(), base.getMonth(), 1);
		end_date = new Date(end_date.getTime() - DAY_MS);
		start_date = new Date(end_date.getFullYear(), end_date.getMonth(), 1);
		move_slider(start_date, end_date);
		break;
	}
}


function move_slider(start_date, end_date) {
    $('select#start').val(start_date.getTime());
    $('select#end').val(end_date.getTime());
    $('select#start').change();
    $('select#end').change();
    update_date_layers();
}
