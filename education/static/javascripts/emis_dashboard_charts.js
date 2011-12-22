function smc_meetings() {
    meeting_chart = new Highcharts.Chart({
        chart: {
            renderTo: 'smc_meetings',
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false
        },
        title: {
            text: 'SMC Meetings this School Term'
        },
        tooltip: {
            formatter: function() {
                return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %';
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true
                },
                showInLegend: false
            }
        },
        series: [{
            type: 'pie',
            name: 'Browser share',
            data: [
                ['one meeting',  78],
                ['two meetings',       9],
                ['Three meetings', 13]
            ],
        }]
    });
}

function progress(){
    $.fn.animateProgress = function(progress, callback){
        return this.each(function(){
            $(this).animate(
                {
                    width:progress + '%'
                },
                {
                    duration:2000,
                    easing:'swing',
                    step: function(progress){
                        var labelE1 = $('.ui_label', this), valueE1 = $('.value', labelE1);
                        if (Math.ceil(progress) < 20 && $('.ui_label',this).is(":visible")){
                            labelE1.hide();
                        } else {
                            if (labelE1.is(":hidden")){
                                labelE1.fadeIn();
                            };
                        }

                        if (Math.ceil(progress) == 100){
                            labelE1.text('Finished');
                            // timeout might not be necessary
                            setTimeout(function(){
                                labelE1.fadeOut();
                            }, 1000);
                        } else {
                            valueE1.text(Math.ceil(progress) + "%");
                        }
                    },
                    complete: function(scope, i, elem){
                        if (callback){
                            callback.call(this, i, elem);
                        };
                    }
                }); // end animate function
        });} // end animate progress loop
}




(function( $ ){
    $.fn.animateProgress = function(progress, callback){
	return this.each(function(){
		$(this).animate(
			{
			width:progress + '%'
			}, 
			{
			duration:2000,
			easing:'swing',
			step: function(progress){
				var labelE1 = $('.ui_label', this), valueE1 = $('.value', labelE1);
				if (Math.ceil(progress) < 20 && $('.ui_label',this).is(":visible")){
					labelE1.hide();
				} else {
					if (labelE1.is(":hidden")){
						labelE1.fadeIn();
					};
				}
				
				if (Math.ceil(progress) == 100){
					labelE1.text('Finished');
					// timeout might not be necessary
					setTimeout(function(){
						labelE1.fadeOut();						
					}, 1000);
				} else {
					valueE1.text(Math.ceil(progress) + "%");
				}								
			},
			complete: function(scope, i, elem){
				if (callback){
					callback.call(this, i, elem);
				};
			}
		}); // end animate function
	});} // end animate progress loop
});