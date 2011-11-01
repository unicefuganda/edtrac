var START_TEMPLATE = "<start_ts>";
var END_TEMPLATE = "<end_ts>";

/**
 * Convenience function for getting week of year from a Date
 */
Date.prototype.getWeek = function() {
    var onejan = new Date(this.getFullYear(),0,1);
    return Math.ceil((((this - onejan) / 86400000) + onejan.getDay()+1)/7);
}

/**
 * Wrapper function for getting individual, value-driven format strings
 * @param timespan one of "day","week","month", or "quarter"
 * @param a timestamp, millseconds since 1970
 * @return the particular formatted string to display for the given timestamp value
 */
function timespan_format(timespan, value) {
	o = {
		value: value,
		f : get_timespan_formatter(timespan),
	}
	return o.f();
}

/**
 * Creates a formatter function, based on the timespan passed in and expecting
 * this.value set appropriately
 * @param timespan one of "day","week","month" or "quarter"
 * @return a formatter function, taking no arguments and returning a string
 * based on this.value (which should be a timestamp).  The particular formatter
 * function (and its corresponding format) will be dependent on the timespan
 * passed in to the generator function.
 */
function get_timespan_formatter(timespan) {
	if (timespan == 'day') {
		return function() {
			var newDate = new Date();
			newDate.setTime(this.value);
			return Highcharts.dateFormat('%e. %b, %Y', newDate);
		}
	} else if (timespan == 'week') {
		return function() {
			var newDate = new Date();
			newDate.setTime(this.value);
			return 'Week '+newDate.getWeek();
		}		
	} else if (timespan == 'month') {
		return function() {
			var newDate = new Date();
			newDate.setTime(this.value);
			return Highcharts.dateFormat('%b, %Y', newDate);
		}		
	} else if (timespan == 'quarter') {
		return function() {
			var newDate = new Date();
			newDate.setTime(this.value);
			var month = newDate.getMonth();
	        var yr = Highcharts.dateFormat('%Y', newDate);
	        if ($.inArray(month, [0,1,2]) >= 0) {
	            return '1st Quarter, '+yr;
	        } else if ($.inArray(month, [3,4,5]) >= 0) {
	            return '2nd Quarter, '+yr;
	        } else if ($.inArray(month, [6,7,8]) >= 0) {
	            return '3rd Quarter, '+yr;
	        } else {
	            return '4th Quarter, '+yr;
	        }
		}		
	}
}

var MILLISECONDS_PER_DAY = 86400000;
var MILLISECONDS_PER_WEEK = 604800000;
var MILLISECONDS_PER_MONTH = 2592000000;
var MILLISECONDS_PER_QUARTER = 7776000000;

/**
 * Return how frequently a tick should be made on the line chart
 * @param timespan the timespan, one of ['day','week','month',or 'quarter']
 * @return the number of milliseconds between each tick mark on the x axis
 */
function get_tick_interval(timespan) {
    if (timespan == 'day') {
        return MILLISECONDS_PER_DAY;
    } else if (timespan == 'week') {
    	return MILLISECONDS_PER_WEEK;
    } else if (timespan == 'month') {
    	return MILLISECONDS_PER_MONTH;
    } else if (timespan == 'quarter') {
    	return MILLISECONDS_PER_QUARTER;
    }	
}

/*
 * Python timestamps are in milliseconds. Javascript's are in microseconds. 
 * This is sort of annoying, but unavoidably has to be cleaned up in the JS:
 * if you multiply timestamps in Python, you get Long values which aren't
 * JSON-ized properly with simplejson.  This iterates the highcharts-formatted
 * series object to correct the discrepancy between python and javascript
 * timestamps. 
 */
function series_milli_to_micro(series) {
	for (i = 0; i < series.length; i++) {
		for (j = 0; j < series[i].data.length; j++) {
			series[i].data[j][0] *= 1000;
		}
	}
	return series;
}

/**
 * Given a response (of the format necessary for the series attribute for highcharts
 * see (http://www.highcharts.com/ref/#series), this initializes all other options
 * for a timestamp-based line graph, and renders to div of id "chart."
 * @param response a JSON object containing the following members:
 * <li><b>series</b>: highcharts-formatted data for display in a line graph, appended
 * to static members of the options passed to the chart.</li>
 * <li><b>timespan</b>: one of 'day','week','month', or 'year', for use in formatting
 * the x axis.</li>
 * <li><b>title</b>: the title of the chart</li>
 * <li><b>subtitle</b>: the subtitle of the chart</li>
 * <li><b>yaxis</b>: the y axis label of the chart</li>
 * @return nothing
 */
function plot_chart(response) {
    options = {
        chart: {renderTo: 'chart',defaultSeriesType:'line',
    	        marginRight: 130,marginBottom: 100,borderColor :'#2fc4d6'},
        title: { text: response.title, x: -20 },
        subtitle: { text: response.subtitle, x: -20 },        
        xAxis: { type: 'datetime',
            tickInterval: get_tick_interval(response.timespan),
            labels: { rotation: -45, align: 'right',
                style: { font: 'normal 13px Verdana, sans-serif' },
                formatter: get_timespan_formatter(response.timespan),
            }
        },
        yAxis: {
        	title: { text: response.yaxis },
            plotLines: [{ value: 0, width: 1, color: '#2fc4d6'}],
            min:0
        },
        tooltip: {
            formatter: function() {
                return '<b>'+ this.series.name +'</b><br/>'+
                    this.x +': '+ this.y +'{{ label }}';
            }
        },
        credits:false,
        legend: { layout: 'vertical', align: 'right', verticalAlign: 'top',
                  x: -10, y: 100, borderWidth: 0 },
        series:[]
    };
    timespan = response.timespan;
    options.tooltip.formatter=function () {
         return '<b>' + this.series.name + '</b><br/>' +
                    timespan_format(timespan, this.x) + ': <b>' + 
                    parseInt(this.y) + '</b>';
    }
    options.series = series_milli_to_micro(response.series);
    chart = new Highcharts.Chart(options);	
}

var CURRENT_CHART_URL;

/**
 * Loads a chart via AJAX, potentially with start and end date values,
 * and then plots it to $('#div')
 * @param url The base url to $.load()
 * @param needs_date true or false, whether to attempt to load the start and end dates
 * into this url
 * @return nothing
 */
function load_chart(url) {
	CURRENT_CHART_URL = url;
    $.ajax({
        type: "POST",
        url:url,
        data: {
		    start : $("select#start").val(),
		    end : $("select#end").val(),
		    drill_key : $("#drill_key").val(),
        },
        dataType: "json",
        success: function(response) {
            plot_chart(response);
        }
    });
}

function drill(elem, key) {
	$('#drill_key').val(key);
	filter(elem);
    load_chart(CURRENT_CHART_URL);
}

function filter_report(elem) {
	filter(elem);
    load_chart(CURRENT_CHART_URL);
}
