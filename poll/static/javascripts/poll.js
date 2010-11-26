function loadReportForLocation(poll_id, location_id) {
    $('#poll_report').load('/polls/' + poll_id + '/report/' + location_id + '/module/');
}