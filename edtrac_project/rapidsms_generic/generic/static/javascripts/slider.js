/**
 * This is a function reference, dynamically created on rendering
 * The container template for the time slider, based on the layers
 * that will require a reload upon clicking "update" or any of the
 * other time slider controls that trigger layer reloads for new
 * date ranges.  See `generic/templates/partials/time_slider.html`
 * for the declaration.
 */
var update_date_layers = function() { };

/**
 * Initializes the selectToUISlider UI component
 * (http://www.jquerylabs.com/selecttouislider-plugin.html)
 * from its html select elements.
 * @param min_ts This is the minimum javascript timestamp (milliseconds
 *               since 1970) that the UI slider displays.  Needed to make
 *               sure that there are horizontal lines at every Monday
 */
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
	min_sdt = new Date(min_ts * 1000);
    tickEvery(7, min_sdt.getDay() - 1);

    // trigger the slider's label to update
    $('select#end option').change();
}


/**
 * Timeslider change handler, updates the label reflecting
 * the date range in a human-readable format
 * @param event the change event (unused)
 * @param element the selectToUISlider element (has start and end values)
 */
function on_timeslider_change(event, element) {
    start_date = new Date(parseInt($('select#start').val()) * 1000);
    end_date = new Date(parseInt($('select#end').val()) * 1000);

    start_str = start_date.getDate() + "-" + (start_date.getMonth() + 1) + "-" + start_date.getFullYear();
    end_str = end_date.getDate() + "-" + (end_date.getMonth() + 1) + "-" + end_date.getFullYear();	
	$( "#date_slider_value" ).text( "From " + start_str + " to " + end_str );
}


/**
 * Tweak the selectToUISlider to have vertical tick markers
 * at regular intervals
 * @param num The number of options between each tick
 * @param offset The starting offset to begin ticking at
 */
function tickEvery(num, offset){
    $('.ui-slider span.ui-slider-tic').each(function(index,elem){
        if (((index + offset) % num) == 0) {
            $(elem).css('display','block');
        }
    });
}


/**
 * a constant, the number of milliseconds in a day.
 */
var DAY_MS = 86400000;

/**
 * Manually update slider values to convenient ranges.
 * Timespan can be one of the following two values:
 * 'w': The most recent full calendar week (Monday-Monday)
 * 'm': The most recent full calendar month (1st of a month to the last day
 *      of the month).
 * @param timespan A single character designating the pre-defined range,
 *                 ignored if not in ['w','m']
 */
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


/**
 * Manually set the slider to the appropriate start and end dates,
 * and update the slider UI
 * @param start_date a JS date object, the start date
 * @param end_date a JS date object, the ending date
 */
function move_slider(start_date, end_date) {
    $('select#start').val(start_date.getTime() / 1000);
    $('select#end').val(end_date.getTime() / 1000);

    // fire changes so the UI can update
    $('select#start').change();
    $('select#end').change();

    // re-load any visible date-driven layers
    update_date_layers();
}
