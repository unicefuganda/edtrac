var attendance_chart;
$(document).ready(function(){
    attendance_chart = new Highcharts.Chart(
        {
            chart:{
                renderTo:'attendance_container',
                type:'bar',
                marginRight:130,
                marginBottom:30
            },
            title:{text:'Attendance of Boys'},
            xAxis : {
                categories:["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
                
            },
            yAxis : {
                title : {text : 'Volume of attendance'}
            },
            // json needs to be serialized here
            series:[{
                name:'Jane',
                data: [1,0,4]
            },{
                name:'John',
                data:[5,7,3]
            }
            ]
        }
    );
});