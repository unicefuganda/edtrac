#! /bin/sh
# script to setup the postgis database and setup the respective database tables


#create a postgis spatial database template

POSTGIS_SQL_PATH=/usr/share/postgresql/8.4/contrib
sudo -u postgres createdb  -E UTF8 template_postgis1 # Create the template spatial database.
sudo -u postgres createlang  -d template_postgis1 plpgsql # Adding PLPGSQL language support.
sudo -u postgres psql  -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis1';"
sudo -u postgres psql  -d template_postgis1 -f $POSTGIS_SQL_PATH/postgis.sql # Loading the PostGIS SQL routines
sudo -u postgres psql  -d template_postgis1 -f $POSTGIS_SQL_PATH/spatial_ref_sys.sql
sudo -u postgres psql  -d template_postgis1 -c "GRANT ALL ON geometry_columns TO PUBLIC;" # Enabling users to alter spatial tables.
sudo -u postgres psql   -d template_postgis1 -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

# create the database (first drop the old one, if it exists)
#
sudo -u postgres dropdb   geoserver
sudo -u postgres createdb   geoserver -T template_postgis1

#create a table to contain district name, slug,and poll info (yes,or no)
#sudo -u postgres psql -d geoserver  -c "create table district (id char(5), district varchar(100), slug varchar(100),iso_code varchar(5), poll_id integer ,poll_result varchar(3));"

# load the shapefile
#
sudo -u postgres ogr2ogr -f  "PostgreSQL" -t_srs EPSG:900913 PG:"dbname=geoserver" Uganda_District2010/Uganda_districts2010.shp  -nlt multipolygon -nln Uganda_districts2010

