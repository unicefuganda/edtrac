var lineChart;
var barChart;

      //advanced options
    Highcharts.theme = {
       colors: ['#c15c74'],
       chart: {
          backgroundColor: '#f8efff',
          borderWidth: 0,
          plotBackgroundColor: '#f8efff',
          plotShadow: false,
          plotBorderWidth: 0
       },
       title: {
          style: { 
             color: '#000',
             font: 'bold 16px "Trebuchet MS", Verdana, sans-serif'
          }
       },
       subtitle: {
          style: { 
             color: '#666666',
             font: 'bold 12px "Trebuchet MS", Verdana, sans-serif'
          }
       },
       xAxis: {
          gridLineWidth: 0,
          lineColor: '#371c37',
          tickColor: '#371c37',
          labels: {
             style: {
                color: '#371c37',
                font: '11px Trebuchet MS, Verdana, sans-serif',
                padding: '5px 10px'
             }
          },
          title: {
             style: {
                color: '#333',
                fontWeight: 'bold',
                fontSize: '12px',
                fontFamily: 'Trebuchet MS, Verdana, sans-serif'
    
             }            
          }
       },
       
       legend: {
          itemStyle: {         
             font: '9pt Trebuchet MS, Verdana, sans-serif',
             color: '#371c37'
    
          },
          itemHoverStyle: {
             color: '#371c37'
          },
          itemHiddenStyle: {
             color: 'gray'
          }
       },
       labels: {
          style: {
             color: '#99b'
          }
       }
    };

// Apply the theme
    
$(document).ready(function() {
    var highchartsOptions = Highcharts.setOptions(Highcharts.theme);
    //bar chart
      barChart = new Highcharts.Chart({
      chart: {
         renderTo: 'barChart',
         defaultSeriesType: 'column'
      },
      title: {
         text: ''
      },
      xAxis: {
         categories: [
            'Unit Item', 
            'Unit Item', 
            'Unit Item', 
            'Unit Item', 
            'Unit Item', 
            'Unit Item', 
         ]
      },
      yAxis: {
         min: 20,
         title: {
            text: 'Number of Cases'
         }
      },
      legend: {
         layout: 'vertical',
         align: 'left',
         verticalAlign: 'top',
         x: 100,
         y: 70,
         floating: true,
         shadow: true
      },
      plotOptions: {
         column: {
            pointPadding: 0.2,
            borderWidth: 0
         }
      },
        series: [{
         name: 'Number of Cases',
         data: [44, 32, 38, 34, 52, 38]
   
      }]
   });
   
   //line chart
    lineChart = new Highcharts.Chart({
         chart: {
            renderTo: 'lineChart',
            type: 'line'
         },
         title: {
            text: ''
         },
         xAxis: {
            categories: ['Unit Item', 'Unit Item', 'Unit Item', 'Unit Item', 'Unit Item', 'Unit Item']
         },
         yAxis: {
            title: {
               text: 'Number of Cases'
            }
         },
         series: [{
            name: 'Number of Cases',
            data: [44, 32, 38, 34, 52, 38]
         }]
      });
});
   