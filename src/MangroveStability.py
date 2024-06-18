# Main script to extract time series of NIRv from Landsat 7 imagery on Google Earth Engine
# (c) Zijian HUANG 2024
import ee
import time
import brdfCorrect


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
landsat7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
    .filterDate('2020-01-01', '2020-12-31')\
    .map(brdfCorrect)


# Function to calculate NDVI
def calculate_ndvi(image):
    ndvi = image.normalizedDifference(['B4', 'B3']).rename('NDVI')
    return image.addBands(ndvi)


# Apply the NDVI calculation to each image
ndvi_collection = landsat7.map(calculate_ndvi)


# Function to calculate mean NDVI for each feature
def mean_ndvi(feature, ndvi_collection):
    mean_ndvi = ndvi_collection.select('NDVI').mean() \
        .reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=feature.geometry(),
        scale=30,
        maxPixels=1e9
    )
    return feature.set(mean_ndvi)


# Iterate over each shapefile and process NDVI calculation
for shapefile in shapefiles:
    print(f'Processing {shapefile}')

    # Load the feature collection
    features = ee.FeatureCollection(shapefile)

    # Calculate mean NDVI for each feature
    result = features.map(lambda feature: mean_ndvi(feature, ndvi_collection))

    # Print the result (optional, for debug purposes)
    print(result.getInfo())

    # Export the result to a CSV file
    task = ee.batch.Export.table.toDrive(
        collection=result,
        description=f'Mean_NDVI_{shapefile.split("/")[-1]}',
        fileFormat='CSV'
    )
    task.start()

    # Wait for a while before processing the next shapefile to avoid rate limits
    time.sleep(10)  # Adjust the sleep time as necessary

print('All shapefiles processed.')
