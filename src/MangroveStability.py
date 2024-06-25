# Main script to extract time series of NIRv from Landsat 7 imagery on Google Earth Engine
# (c) Zijian HUANG 2024

import time
import geopandas as gpd
from support_tools import *

# Initialize the Earth Engine module
ee.Initialize()

# List your shapefiles as assets
base_path = r"/Volumes/TKssd"
shp0_path = r"/dataBackup/Satellites/Global_mangrove/Global_2020/ChinaMangrove2020/ChinaMangrove2020.shp"
export_path = r"./data"

# Dates to proceed
start_date = '1999-01-01'
end_date = '2023-12-31'

# Read shapefile
full_mangrove = gpd.read_file(shp0_path).to_crs("epsg:4326")

# Load the Landsat 7 image collection
ic = ee.ImageCollection('LANDSAT/LE07/C02/T2_L2') \
    .select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL'],
            ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'QA_PIXEL'])

# split and process on every 40 features
shp_idx = 0
for i in range(0, len(full_mangrove), 40):
    shp_idx += 1
    # --- Get features ready
    # slice the geo-dataframe
    gdf = full_mangrove.iloc[i:i+40]
    # first export the sliced geo-dataframe into a new shapefile
    export_slice = f"ChinaMangrove_part_{shp_idx}.shp"
    gdf.to_file(f"{export_path}/{export_slice}", driver="ESRI Shapefile")
    # --- Calculate indices based on features
    # Iterate over each shapefile and process calculation of vegetation indices
    for vi in ['ndvi', 'nirv']:
        print(f'Processing #{i}/{len(full_mangrove)/40}')
        # convert the geo-dataframe to a list of dictionaries
        features = gdf.to_json()["features"]
        # create a list of Earth Engine features
        ee_features = []
        for feature in features:
            # extract geometry and properties
            geometry = ee.Geometry.MultiPolygon(feature['geometry']['coordinates'])
            properties = feature['properties']
            # create an earth engine feature
            ee_feature = ee.Feature(geometry, properties)
            # append to the list
            ee_features.append(ee_feature)
        # create the feature collection
        features = ee.FeatureCollection(ee_features)

        # Calculate mean vegetation indices for each feature
        result = features.map(lambda f: get_vi_time_series(
            feature=f,
            image_collection=ic,
            start_date=start_date,
            end_date=end_date,
            target=vi
        ))

        # Export the result to a CSV file
        task = ee.batch.Export.table.toDrive(
            collection=result,
            description=f'Mean_NDVI_{shp_idx}',
            folder='Mangrove',
            fileFormat='CSV'
        )
        task.start()

        # Wait for a while before processing the next shapefile to avoid rate limits
        time.sleep(30)  # Adjust the sleep time as necessary

print('--All shapefiles processed.')

