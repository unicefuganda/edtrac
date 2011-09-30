#! /bin/sh
# script to setup the postgis database and setup the respective database tables


#create a postgis spatial database template

POSTGIS_SQL_PATH=/usr/share/postgresql/8.4/contrib/postgis-1.5
createdb -U postgres -E UTF8 template_postgis # Create the template spatial database.
createlang -U postgres -d template_postgis plpgsql # Adding PLPGSQL language support.
psql -U postgres -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis';"
psql -U postgres -d template_postgis -f $POSTGIS_SQL_PATH/postgis.sql # Loading the PostGIS SQL routines
psql -U postgres -d template_postgis -f $POSTGIS_SQL_PATH/spatial_ref_sys.sql
psql -U postgres -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;" # Enabling users to alter spatial tables.
psql -U postgres  -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

# create the database (first drop the old one, if it exists)
#
dropdb  -U postgres geoserver
createdb  -U postgres geoserver -T template_postgis

#create a table to contain district name, slug,and poll info (yes,or no)
psql -d geoserver -U postgres -c "create table district (id char(5), district varchar(100), slug varchar(100),iso_code varchar(5), poll_id integer ,poll_result varchar(3));"

# load the shapefile
#
ogr2ogr -f  "PostgreSQL" -t_srs EPSG:900913 PG:"dbname=geoserver user=postgres" Uganda_District2010/Uganda_districts2010.shp  -nlt multipolygon -nln Uganda_districts2010

