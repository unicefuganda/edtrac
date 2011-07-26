/** The GMap2 object dictionary, element IDs to dictionaries */
var MAPS = {};

/** These placeholders are in URL templates, to be substituted with actual time
 *  ranges passed to the associated API call.
 */
var START_TEMPLATE = "<start_ts>";
var END_TEMPLATE = "<end_ts>";

/**
 * A dictionary of objects.
 * The keys are google.maps.LatLng objects, storing what
 * should be displayed at a particular map point (Overlays, Popup descriptions
 * and Icon Markers.
 * 
 * The value is a location object, containing:
 *  - location_name : The name of the location, for display at the top of 
 *  -                 an informational popup
 *  - location_id : Currently unused, but could be used to trigger additional
 *                  API callbacks
 *  - layers: A dictionary of layer urls to overlay info objects, containing:
 *             - description : HTML markup in a string to be added to a popup
 *             - overlays : A list of Overlay objects
 * 
 * This dictionary is build over time as new layers are loaded in, but
 * here is an example of the potential structure after two overlays are loaded: 
 * LAYER_OVERLAYS = {
 *     LatLng(1,1): {
 *         'location_id': 1,
 *         'location_name': 'Patongo',
 *         'layers' : {
 *             '/cvs/stats/healthfacility/':{
 *                 description:'',
 *                 overlays:[Icon, Marker, Circle, etc...],
 *             },
 *             '/cvs/stats/<start_ts>/<end_ts>/muac/':{
 *                 description:'Malnutrition: 2 cases',
 *                 overlays:[]
 *             },
 *         },
 *     LatLng(2,2): {...},
 * };
 */
var LAYER_OVERLAYS = {};


/*
 * Initializes a Google Maps Map object
 * (http://code.google.com/apis/maps/documentation/javascript/reference.html)
 * within a div of a given ID.
 *
 * @param map_id The id of the Div to create a map inside of
 */
function init_map(map_id, minLat, maxLat, minLon, maxLon) {                           
    if ($('#' + map_id).hasClass('init')) {
        clat = (parseFloat(minLat) + parseFloat(maxLat)) / 2.0;
        clon = (parseFloat(minLon) + parseFloat(maxLon)) / 2.0;
        center = new google.maps.LatLng(clat, clon);
        mapOptions = {
            zoom: 11,
            center: center,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        map = new google.maps.Map(document.getElementById(map_id), mapOptions);

        //make sure the zoom fits all the points
        var bounds = new google.maps.LatLngBounds();
        bounds.extend(new google.maps.LatLng(parseFloat(minLat), parseFloat(minLon)));
        bounds.extend(new google.maps.LatLng(parseFloat(maxLat), parseFloat(maxLon)));
        map.fitBounds(bounds);
        $('#' + map_id).removeClass('init');
        
        MAPS[map_id] = map;
        google.maps.event.addListener(map, 'zoom_changed', update_circle_overlays(map));
    }
}

/* A lookup mapping zoom levels on a map to maximum radii (in meters) that will 
 * display "well" at that zoom level */
var RADIUS_LOOKUP = {}


/**
 * Gets the appropriate radius to display a particular (normalized, [0-1]) value,
 * based on the current zoom level of the map.
 * 
 * @param map_id the ID of the map div, to be passed to the maps global.
 * @param value a normalized [0,1] value, to be changed into a circle radius.
 * @return the radius to display the circle, in meters.
 */
function get_radius(map, value) {
    if (!(map.getZoom() in RADIUS_LOOKUP)) {
        // This function was heuristically determined to fit well at usable zoom
        // levels (typically the [6,12] range)
        RADIUS_LOOKUP[map.getZoom()] = Math.pow(1.88, 12-map.getZoom()) * 2830;
    }
    return (RADIUS_LOOKUP[map.getZoom()] * value);
}


/**
 * Iterates over all overlays to make sure that
 * Circles dynamically size to fit their map's zoom level.
 * This uses a dynamically added property to the Circle object,
 * `value`, to find the normalized value [0,1] and scale it
 * using the map's zoom level and get_radius.
 *
 */
function update_circle_overlays(map) {
    return function () {
        $.each(LAYER_OVERLAYS, function(point,pointobj) {
           $.each(pointobj['layers'], function(layer,value) {
                for (i = 0; i < value['overlays'].length; i++) {
                    overlay = value['overlays'][i];
                    if ('setRadius' in overlay) {
                        overlay.setRadius(get_radius(map, overlay.value));
                    }
                }
           });
        });
    }
}


var CATEGORY_COLORS = [];
var CATEGORY_COLOR_LOOKUP = {};
var CATEGORY_OFFSET = 0;

/**
 * Registers a category name with a particular color,
 * for consistency across multiple visualizations.  If the
 * category name hasn't been passed to this function yet, it
 * will be added to category_color_lookup (as a key), and
 * the next available color from the color list will be
 * the value.  See ureport/templates/layout.html for the
 * loading of the colors into the CATEGORY_COLORS based on
 * the values in ureport/settings.py
 * @param category the category name, e.g. 'yes','no',etc
 * @return the color value in css form e.g., '#ABff07'
 */
function get_color(category) {
    if (!CATEGORY_COLOR_LOOKUP[category]) {
        if (CATEGORY_COLORS.length <= CATEGORY_OFFSET) {
        	CATEGORY_COLOR_LOOKUP[category] = '#000000';
        } else {
        	CATEGORY_COLOR_LOOKUP[category] = CATEGORY_COLORS[CATEGORY_OFFSET];
        	CATEGORY_OFFSET += 1;
        }
    }
    return CATEGORY_COLOR_LOOKUP[category];
}


/**
 * Registers a category name with a particular color,
 * as specified by urlpatterns.
 * @param layer the layer name, e.g. 'muac','ma',etc
 * @param color the color value in css form e.g., '#ABff07'
 */
function set_color(layer, color) {
	CATEGORY_COLOR_LOOKUP[layer] = color;
}


/**
 * Returns a click listener function (no parameters)
 * that dynamically creates a popup, based on the description markup
 * in LAYER_OVERLAYS.
 * 
 * @param point the LatLng object that contains descriptions in LAYER_OVERLAYS
 * @param overlay the overlay object being clicked (over which to display the popup)
 * @param map the map to open the popup on
 */
function get_description_popup(point, map) {
    return function() {
        info="<h4>" + LAYER_OVERLAYS[point].location_name + "</h4>";
        $.each(LAYER_OVERLAYS[point]['layers'], function(key,value) {
            info += value.description;
        });
        new google.maps.InfoWindow({content:info}).open(map,
            /* This is a hack.  We don't actually pop an info 
             * window up on any particular overlay, because only
             * Marker overlays expose a position property with
             * getProperty(), necessary for displaying a Window.
             * This dummy marker will be garbage collected when the
             * info window closes.
             */
            new google.maps.Marker({
                position:point,
                map:map,
                visible:false
            }));
    }
}


/**
 * Labels are basic custom Overlays to display some text on the map
 * (yes, I'm also surprised this isn't built-in to the Google Maps API).
 * @param point The center point (LatLng) that the label should be displayed at.
 *              The label will dynamically position itself to be centered around this
 *              based on text width and height.
 * @param text The text of the label (any HTML is valid here).
 * @param map The map to play the overlay on
 */
function Label(point, text, map) {
    this.point = point;
    this.text = text;
    this.div = null;
    this.setMap(map);
}
Label.prototype = new google.maps.OverlayView();
Label.prototype.onAdd = function() {
    div = document.createElement("div");
    div.style.position = "absolute";
    div.innerHTML = '<div><b>' + this.text + '<b/></div>';
    div.style.cursor = 'pointer';
    div.style.position = "absolute";
    this.div = div;
    var panes = this.getPanes();
    panes.overlayLayer.appendChild(div);
}
Label.prototype.draw = function() {
    var overlayProjection = this.getProjection();
    var center = overlayProjection.fromLatLngToDivPixel(this.point);

    var div = this.div;
    // Offset width isn't perfect, but serves a good enough purpose
    // for getting the label div *almost* centered at Lat,Lng
    div.style.left = (center.x - (div.offsetWidth / 2)) + 'px';
    div.style.top = (center.y - (div.offsetHeight / 2)) + 'px';
}
Label.prototype.onRemove = function() {
	// Garbage collect!
    this.div.parentNode.removeChild(this.div);
    this.div = null;
}


/**
 * Plots categorized data, of the type that comes from,
 * for example, yes/no poll statistics.  The idea is that one point
 * has several values for each category within one layer, and only the
 * category with the maximum percentage will be rendered as an overlay.
 * For instance, if there are 10 "yes" responses and 5 "no" responses, 
 * A circle rendered in the "yes" category color will be displayed, and 
 * it will be larger than the minimal size (the minimal size is displayed
 * when yes responses are 51%, the minimal majority)
 * This function expects response.data to be in the following format, for each location:
 * {"location_name": "Amuru", "lon": "31.95000", "value": 2, "category__name": "no",
 *  "category__color": "", "lat": "2.73333", "location_id": 1115},
 * {"location_name": "Amuru", "lon": "31.95000", "value": 12,
 *  "category__name": "yes", "category__color": "", "lat": "2.73333", "location_id": 1115},
 *
 * @param map the Google Maps object to plot overlays to
 * @param response the JSON response data
 * @param layer_name The user-friendly name of this layer
 * @param layer_key The key to store this layer under within `LAYER_OVERLAYS`.
 *                  For dateless layers, this will be the same as the layer's URL.  For
 *                  layers that need a date, this will be the layer template (with
 *                  <start_ts> and <end_ts> placeholders.
 */
function plot_categorized_data(map, response, layer_name, layer_key) {
    data = response['data'];

    circle_options_prototype = {
        strokeOpacity: 0.8,
        strokeWeight: 1,
        fillOpacity: 0.35,
        map: map
    };

    point = new google.maps.LatLng(parseFloat(data[0].lat), parseFloat(data[0].lon));
    location_id = data[0].location_id;
    if (!(point in LAYER_OVERLAYS)) {
        LAYER_OVERLAYS[point] = {
            'location_id':data[0].location_id,
            'location_name':data[0].location_name,
            'layers':{},
        }
    }
    current_layer = {'description':'<ul>'}
    LAYER_OVERLAYS[point].layers[layer_key] = current_layer;

    max = 0;
    category = data[0].category__name;
    total = 0;

    for (i = 0; i < data.length; i++) {
        if (location_id != data[i].location_id) {
            d = max / total;
            current_layer['description'] += "<li><i>Total number of responses</i>:"+total+"</li></ul>";
            circle = new google.maps.Circle($.extend({
                strokeColor: get_color(category),
                fillColor: get_color(category),
                center: point,
                radius: get_radius(map, d)
            }, circle_options_prototype));
            circle.value = d;
            current_layer['overlays'] = [circle]
            google.maps.event.addListener(circle, 'click', get_description_popup(point, map));

            // FIXME figure out how to do this
            label = new Label(point, parseInt(d * 100) + "%", map);
            current_layer['overlays'].push(label)

            point = new google.maps.LatLng(parseFloat(data[i].lat), parseFloat(data[i].lon));
            location_id = data[i].location_id;
            if (!(point in LAYER_OVERLAYS)) {
                LAYER_OVERLAYS[point] = {
                    'location_id':data[i].location_id,
                    'location_name':data[i].location_name,
                    'layers':{},
                }
            }
            current_layer = {'description':'<ul>'}
            LAYER_OVERLAYS[point].layers[layer_key] = current_layer;
            max = 0;
            total = 0;
            category = data[i].category__name;
        }
        current_layer['description'] += "<li>" + data[i].category__name + ":" + data[i].value + "</li>";
        total += data[i].value;
        if (data[i].value > max) {
            max = data[i].value;
            category = data[i].category__name;
        }
    }
    d = max / total;
    current_layer['description'] += "<li><i>Total number of responses</i>:"+total+"</li><ul>";
    circle = new google.maps.Circle($.extend({
        strokeColor: get_color(category),
        fillColor: get_color(category),
        center: point,
        radius: get_radius(map, d)
    }, circle_options_prototype));
    circle.value = d;
    current_layer['overlays'] = [circle]
    google.maps.event.addListener(circle, 'click', get_description_popup(point, map));

    // FIXME add legend
    // $('#' + map_id + "_legend").show();
    // $('#' + map_id + '_legend table').html(' ');
    // for (category in category_color_lookup) {
    //    category_span = '<span style="width:15px;height:15px;background-color:' + category_color_lookup[category] + ';float:left;display:block;margin-top:10px;"></span>'
    //    $('#' + map_id + '_legend table').append('<tr><td>' + category + '</td><td>' + category_span + '</td></tr>')
    // }
}


/**
 * Plots marker data, of the type that comes from,
 * for example, a list of health facilities.  This layer will typically
 * serve as the click listener and root overlay for several circle-based
 * overlays, as is the case with, for instance, epidemiological data vs.
 * the reporting health facility.  Each location has an icon associated with
 * it.
 * This function expects response.data to be in the following format, for each location:
 * {"location_name": "Oguta HCII", "lon": "3.02628", "lat": "32.92164", "location_id": 4,
 *  "icon": "2"}, ...
 *
 * it further expects response.icons to exist, as an icon=>url lookup:
 *
 * "icons": {"d": "/static/cvs/icons/HOSPITAL.png",
 *           "H": "/static/cvs/icons/HOSPITAL.png",
 *           "2": "/static/cvs/icons/HCII.png",... 
 * @param map the Google Maps object to plot overlays to
 * @param response the JSON response data
 * @param layer_name The user-friendly name of this layer
 * @param layer_key The key to store this layer under within `LAYER_OVERLAYS`.
 *                  For dateless layers, this will be the same as ths layer's URL.  For
 *                  layers that need a date, this will be the layer template (with
 *                  <start_ts> and <end_ts> placeholders.
 */
function plot_marker_data(map, response, layer_name, layer_key) {
    // FIXME figure out how to make these always on top (check bindTo)
    icons = response['icons'];
    data = response['data'];
    for (i = 0; i < data.length; i++) {
        point = new google.maps.LatLng(parseFloat(data[i].lat),parseFloat(data[i].lon));

        if (!(point in LAYER_OVERLAYS)) {
            LAYER_OVERLAYS[point] = {
                'location_id':data[i].location_id,
                'location_name':data[i].location_name,
                'layers':{},
            }
        }
        current_layer = {'description':''}
        LAYER_OVERLAYS[point].layers[layer_key] = current_layer;
        mIcon  = new google.maps.MarkerImage(icons[data[i].icon],new google.maps.Size(20, 20));
        var marker = new google.maps.Marker({
            position: point,
            map: map,
            icon: mIcon,
        });
        marker.setIcon(mIcon);
        current_layer['overlays'] = [marker];

        google.maps.event.addListener(marker, 'click', get_description_popup(point, map));
    }
}


/**
 * This function plots value-driven data, of the type that comes from,
 * for example, epidemiological statistics.  The idea is that each point
 * has one normalized value within the layer, and each Circle object
 * will be rendered in comparison to the max reported value.
 * This function expects response.data to be in the following format, for each location:
 * {"location_name": "Parabongo HCII", "location_id": 72, "lon": "2.90939",
 * "value": 46, "lat": "32.15269"}, ...
 *
 * @param map the Google Maps object to plot overlays to
 * @param response the JSON response data
 * @param layer_name The user-friendly name of this layer
 * @param layer_key The key to store this layer under within `LAYER_OVERLAYS`.
 *                  For dateless layers, this will be the same as layer's URL.  For
 *                  layers that need a date, this will be the layer template (with
 *                  <start_ts> and <end_ts> placeholders.
 */
function plot_flat_data(map, response, layer_name, layer_key) {
    data = response['data'];
    layer_title = response['layer_title'];
    circle_options_prototype = {
        strokeOpacity: 0.8,
        strokeColor:get_color(layer_name),
        strokeWeight: 1,
        fillOpacity: 0.35,
        fillColor: get_color(layer_name),
        map: map
    };
    
    // first pass over the data establishes
    // layer-wide max for normalization.
    max = 0;
    for (i = 0; i < data.length; i++) {
        if (data[i].value > max) {
            max = data[i].value;
        }
    }

    for (i = 0; i < data.length; i++) {
        point = new google.maps.LatLng(parseFloat(data[i].lat), parseFloat(data[i].lon));
        if (!(point in LAYER_OVERLAYS)) {
            LAYER_OVERLAYS[point] = {
                'location_id':data[i].location_id,
                'location_name':data[i].location_name,
                'layers':{},
            }
        }
        current_layer = {'description':layer_title + ' : ' + data[i].value}
        LAYER_OVERLAYS[point].layers[layer_key] = current_layer;
        var circle = new google.maps.Circle($.extend({
            center:point,
            radius:get_radius(map, (data[i].value / max)),
        }, circle_options_prototype));
        circle.value = data[i].value / max;
        current_layer['overlays'] = [circle];
        google.maps.event.addListener(circle, 'click', get_description_popup(point, map));
    }
}


/**
 * Removes the overlays associated with a particular layer key.  This walks through
 * the LAYER_OVERLAYS data structure, calling `setMap(null)` on any associated
 * overlays, and then deleting the entire layer structure from each point in the
 * LAYER_OVERLAYS array.
 * @param layer_key The layer to remove, either a URL or URL template (in the case
 *                  of a date-based layer)
 */
function remove_layer(layer_key) {
    $.each(LAYER_OVERLAYS, function(point,pointobj) {
    	for (layer in pointobj['layers']) {
    		if (layer == layer_key) {
    			overlays = pointobj['layers'][layer]['overlays'];
    			for (i = 0; i < overlays.length; i++) {
    				overlays[i].setMap(null);
    			}
    			delete pointobj['layers'][layer];
    		}
    	}
     });
}


/**
 * This is the generic function for plotting JSON-driven map layers. It expects
 * responses loaded (via AJAX) to be of the following format:
 * { 
 *     layer_type: [marker|categorized|flat],
 *     layer_title: 'An example description',
 *     data: [{
 *                location_name: 'Patongo HCIII',
 *                location_id: 1,
 *                lon: 72.0,
 *                lat: 32.12,
 *                [optional_parameters]
 *            }, ...]
 * }
 * 
 * Where `optional_parameters` will vary based on `layer_type` (see additional documentation
 * in plot_categorized_data, plot_flat_data, plot_marker_data), and also for the LAYER_OVERLAYS
 * global.
 *
 * @param map_id The element id containing a google map (potentially uninitialized).
 * @param layer_url The URL from which to fetch JSON map content.
 * @param layer_name The user-friendly name of this layer
 * @param layer_key The key to store this layer under within `LAYER_OVERLAYS`.
 *                  For dateless layers, this will be the same as layer_url.  For
 *                  layers that need a date, this will be the layer template (with
 *                  <start_ts> and <end_ts> placeholders.
 */
function plot_layer(map_id, layer_name, layer_url, layer_key) {
    if (!(map_id in MAPS)) {
        console.error('map ID ' + map_id + ' not found!');                 
        return;
    }
    map = MAPS[map_id];
    
    // Remove any previously plotted data for this layer
    remove_layer(layer_key);

    $.ajax({
        type: "GET",
        url:layer_url,
        dataType: "json",
        success: function(response) {
            switch(response['layer_type']) {
                case 'categorized':
                    plot_categorized_data(map, response, layer_name, layer_key);
                    break;
                case 'flat':
                    plot_flat_data(map, response, layer_name, layer_key);
                    break;
                case 'marker':
                    plot_marker_data(map, response, layer_name, layer_key);
                    break;
            }
        }
    });
}


/**
 * Plot a layer that has `needs_date` set to true.  This requires updating the
 * layer's URL template to be something that has start and end timestamps
 * (rather than placeholders for these values).  Passes the updated url to
 * `plot_layer`.
 * @param map_id The id of the map on which to plot this layer
 * @param layer_name The name of the layer, used for display purposes
 * @param layer_url_template The url template (containing START_TEMPLATE and
 *                           END_TEMPLATE placeholders)
 * @param start_date The start timestamp (integer milliseconds since 1-1-1970)
 *                   of the date range
 * @param end_date The end timestamp (integer milliseconds since 1-1-1970) of
 *                 the date range
 */
function plot_layer_with_date(map_id, layer_name, layer_url_template, start_date, end_date) {  
	layer_url = layer_url_template.replace(START_TEMPLATE, start_date);
	layer_url = layer_url.replace(END_TEMPLATE, end_date);
	plot_layer(map_id, layer_name, layer_url, layer_url_template);
}


/**
 * Remove or plot a layer, as necessary, determined by the state of a checkbox.
 * @param map_id The id (string) of the map this layer is associated with.
 * @param layer_name The name of the layer, for display purposes
 * @param layer_url_template The URL or URL template of this layer
 * @param needs_date True of the layer has a URL template requiring dates
 * @param checkbox The checkbox whose state has changed
 */
function toggle_layer(map_id, layer_name, layer_url_template, needs_date, checkbox) {
	if (checkbox.checked) {
		if(needs_date) {
			var start_date = $("select#start").val();
			var end_date = $("select#end").val();
			plot_layer_with_date(map_id, layer_name, layer_url_template, start_date, end_date);
		} else {
			plot_layer(map_id, layer_name, layer_url_template, layer_url_template);
		}
	} else {
		remove_layer(layer_url_template);
	}
}