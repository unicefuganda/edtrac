#! /bin/sh
# script to setup the postgis database and setup the respective database tables

# create the database (first drop the old one, if it exists)
#
dropdb geoserver
createdb geoserver -T template_postgis

#create a table to contain district name, slug,and poll info (yes,or no)
psql -d geoserver -c "create table population (id char(5), district varchar(100), slug varchar(100),iso_code varchar(5), poll_id integer ,poll_result varchar(3));"

# load the shapefile
#
ogr2ogr -f PostgreSQL PG:dbname=geoserver Uganda_Districts2010/Uganda_districts2010.shp -t_srs EPSG:900913 -nlt multipolygon -nln Uganda_districts2010

