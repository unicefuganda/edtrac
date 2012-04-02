function smc_meetings(schools, meetings) {
    var schools;
    var meetings;
    meeting_chart = new Highcharts.Chart({
        chart: {
            renderTo: 'smc_meetings',
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false
        },
        title: {
            text: 'SMC Meetings Held this School Term'
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
            // iteration
            data: [
                ['one meeting',  78],
                ['two meetings',       9],
                ['Three meetings', 13]
            ]
        }]
    });
}


function violence_cases(xVals, yVals, title){
    var x_vals = xVals.split("','");
    var b = yVals.split(",");
    var violence = [];
    for(i=0; i<b.length; i++){
        violence.push(parseFloat(b[i]));
    }
    var violence_chart;
    violence_chart = new Highcharts.Chart(
        {
            chart: {
                renderTo:'violence',
                defaultSeriesType:'column',
                margin:[50,50,100,80]
            },
            title :{
                text : title
            },
            xAxis:{
                categories : x_vals

            },
            labels : {
                rotation : -45,
                align : 'right',
                style : {
                    font:'normal 13px Verdana, sans-serif'
                }
            },
            yAxis:{
                min: 0,
                title : {
                    text : 'Number of Cases'
                }
            },
            legend:{
                enabled:false
            },
            tooltip:{
                formatter:function(){
                    return '<b>'+ this.x+'</b><br/>'+ 'Violence cases: '+Highcharts.numberFormat(this.y, 1) + ' cases';
                }
            },
            series:[
                {
                    name: 'Numbers',
                    data : violence,
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


//pie chart
function pie(data, chart_title, series_title, selector_id, tooltip_text, showLegend) {
    var d = data.split(",");
    var data_array = [];
    for(i=0; i < d.length; i++){
        x = d[i].split('-');
        data_array.push([x[0], parseInt(x[1])]);
    }




    Highcharts.theme = {
      chart : {
          backgroundColor: '#f3efff',
          borderWidth: 0,
          plotBackgroundColor: '#f8efff',
          plotShadow:false,
          plotBorderWidth: 0
      }
    };

    var chart;

    chart = new Highcharts.Chart({
        chart: {
            //renderTo: 'lunch',
            renderTo: selector_id,
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false
        },
        title: {
            text: chart_title
        },
        legend:{
          layout: 'vertical',
            align: 'right',
            verticalAlign: 'top',
            x : -10,
            y: 100,
            borderWidth:0
        },
        tooltip: {
            formatter: function() {
                //return this.percentage +' % \n didn\'t have meals';
                return this.percentage.toFixed(1) + '%'+ tooltip_text;
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true
                },
                showInLegend:showLegend
            }
        },
        series: [{
            type: 'pie',
            //name: 'Lunch at School',
            name: series_title,
            data: data_array
        }]
    });
}

function load_progress_chart(value){
    var value;
    if (value > 100){
        // pervasive checking...
        alert("Progress chart can't load for values greater than 100 denied");
    }
    else{
        $("#progress_p3").progressbar({value: value});
        $("#progress_p3 > div").append(value + '%').addClass('pretify');
    }
}


function load_line_graph(title, subtitle, selector, yLabel, xLabel){
    line_chart = new Highcharts.Chart({
          chart: {
             renderTo: selector,
             defaultSeriesType: 'line'
          },
          title: {
             text: title
          },
          subtitle: {
             text: subtitle
          },
          xAxis: {
              title : {
                text: xLabel
              },
             categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
          },
          yAxis: {
             title: {
                text: yLabel
             }
          },
          tooltip: {
             enabled: true,
             formatter: function() {
                return '<b>'+ this.series.name +'</b><br/>'+
                   this.x +': '+ this.y +' cases';
             }
          },
          plotOptions: {
             line: {
                dataLabels: {
                   enabled: true
                },
                enableMouseTracking: true
             }
          },
          series: [{
             name: 'Kaboong',
             data: [0, 0,0,0,0,0,0,0,0,0,0,0]
          }]
       });
}

function load_column(title, selector, yLabel, xLabel, category, data_list){
    var category_array =  [];
    var data_array = [];
    for (i=0; i<category.length; i++){
        x = parseFloat(category[i])
        category_array.push(x.toString());
    }
    for (i=0; i<data_list.length; i++){
        data_array.push(parseFloat(data_list[i]));
    }
    bar_chart = new Highcharts.Chart({
        chart : {
            renderTo: selector,
            defaultSeriesType:'column'
        },
        title : {
            text: title
        },
        xAxis:{
            title:{
                text : xLabel
            },
            categories:category_array
        },
        yAxis: {
            min: 0,
            title: {
                text: yLabel
            }
        },
        legend: {
            layout:'vertical',
            backgroundColor:'#FFFFFF',
            align:'left',
            verticalAlign:'top',
            x:100,
            y:20,
            floating:true,
            shadow:true
        },
        tooltip:{
            formatter:function(){
                return ''+this.x+': '+this.y + ' districts'
            }
        },
        plotOptions:{
            column:{
                pointPadding:0.2,
                borderWidth:0
            }
        },

        series:[
            {
            name:'Sub theme',
            data: data_array
            }
        ]
    });
}

