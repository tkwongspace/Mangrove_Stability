# Main script to extract time series of NIRv from Landsat 7 imagery on Google Earth Engine
# (c) Zijian HUANG 2024

import time
from support_tools import *

# Initialize the Earth Engine module
ee.Initialize()

# List your shapefiles as assets
shapefiles = [
    'users/your_username/shapefile_part1',
    'users/your_username/shapefile_part2',
    'users/your_username/shapefile_part3',
    'users/your_username/shapefile_part4'
]

# Load the Landsat 7 image collection
ic = ee.ImageCollection('LANDSAT/LE07/C02/T2_L2') \
    .select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL'],
            ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'QA_PIXEL'])

# Iterate over each shapefile and process NDVI calculation
for vi in ['ndvi', 'nirv']:
    for shapefile in shapefiles:
        print(f'Processing {shapefile}')

        # Load the feature collection
        features = ee.FeatureCollection(shapefile)

        # Calculate mean vegetation indices for each feature
        result = features.map(lambda feature: get_vi_time_series(
            feature=feature,
            image_collection=ic,
            start_date='1999-01-01',
            end_date='2023-12-31',
            target=vi
        ))

        # Export the result to a CSV file
        task = ee.batch.Export.table.toDrive(
            collection=result,
            description=f'Mean_NDVI_{shapefile.split("/")[-1]}',
            folder='Mangrove',
            fileFormat='CSV'
        )
        task.start()

        # Wait for a while before processing the next shapefile to avoid rate limits
        time.sleep(10)  # Adjust the sleep time as necessary

print('--All shapefiles processed.')

