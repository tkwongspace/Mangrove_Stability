# Find intersection of polygons from two shapefiles

import geopandas as gpd

# load shapefiles
shp1 = gpd.read_file(r'/Volumes/TKssd/dataBackup/Satellites/Global_mangrove/Global_2020/ChinaMangrove2020/' +
                     'ChinaMangrove2020.shp')
shp2 = gpd.read_file(r'/Volumes/TKssd/dataBackup/Satellites/Global_mangrove/Mangrove_ProtectedArea_CN/' +
                     'MANGROVES_CN.shp')

# ensure both shapefiles have the same CRS
if shp1.crs != shp2.crs:
    shp2 = shp2.to_crs(shp1.crs)

# find areas that are protected
pa = gpd.overlay(shp1, shp2, how='intersection')

# find areas that are not protected
npa = gpd.overlay(shp1, pa, how='difference')

# save the intersection as a new shapefile
pa.to_file('../data/pa.shp')
npa.to_file('../data/npa.shp')
