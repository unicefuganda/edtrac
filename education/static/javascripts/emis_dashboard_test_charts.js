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


function abuse_cases(districts, abuse_values){
    var abuse_chart;
    var dist = districts.split("','");
    var b = abuse_values.split(",");
    var abuse = [];
    for(i=0; i<b.length; i++){
        abuse.push(parseFloat(b[i]));
    }
    abuse_chart = new Highcharts.Chart(
    {
        chart: {
            renderTo:'abuse',
            defaultSeriesType:'column',
            margin:[50,50,100,80]
        },
        title :{
            text:'Abuse Cases Reported this Month'
        },
        xAxis:{
            categories: dist

        },
        labels:{
            rotation:-45,
            align:'right',
            style:{
                font:'normal 13px Verdana, sans-serif'
            }
        },
        yAxis:{
            min:0,
            title:{
                text: 'Number of Cases'
            }
        },
        legend:{
            enabled:false
        },
        tooltip:{
            formatter:function(){
                return '<b>'+ this.x+'</b><br/>'+ 'Abuse cases: '+Highcharts.numberFormat(this.y, 1) + ' cases';
            }
        },
        series:[
            {
                name: 'Numbers',
                data : abuse,
    dataLabels:{
        enabled:true,
                rotation:-90,
                color:'#FFFFFF',
                align:'right',
                x:-3,
                y:10,
                formatter:function(){
            return this.y;
        },
        style:{
            font:'normal 13px Verdana, sans-serif'
        }
    }
    }
    ]
    }
    );
}

function lunch(data) {
    var d = data.split(",");
    var lunch_data = [];
    for(i=0;i<d.length; i++){
        x = d[i].split('-');
        lunch_data.push([x[0],parseFloat(x[1])]);
    }
    var lunch_chart;
    lunch_chart = new Highcharts.Chart({
        chart: {
            renderTo: 'lunch',
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false
        },
        title: {
            text: 'Lunch at School this Month'
        },
        tooltip: {
            formatter: function() {
                return this.percentage +' % \n didn\'t have meals';
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true
                },
                showInLegend:false
            }
        },
        series: [{
            type: 'pie',
            name: 'Lunch at School',
            data: lunch_data
                    
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