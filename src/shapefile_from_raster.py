# Create shapefile from raster based on band values

import numpy as np
import fiona
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from tqdm import tqdm


path_to_tif = input("Path to the raster file: ")
path_for_export = input("Path to the export file (Remember with .shp): ")
print(">> Ready to start conversion..")

try:
    # load the raster data
    with rasterio.open(path_to_tif) as f:
        image = f.read(1)
        transform = f.transform
        crs = f.crs

    # extract the forest class
    mask = image == 2

    # convert the mask to polygons
    polygons = (
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) in enumerate(
            shapes(mask.astype(np.uint8), mask=mask, transform=transform))
    )

    # define schema for the shapefile
    schema = {
        'geometry': 'Polygon',
        'properties': {'raster_val': 'int'},
    }

    # initialize progress bar
    total_polygons = np.sum(mask)
    pbar = tqdm(total=total_polygons, desc="Converting polygons")

    # write the polygons to a shapefile
    with fiona.open(path_for_export, 'w', driver='ESRI Shapefile', crs=crs, schema=schema) as out:
        for elem in polygons:
            out.write({
                'geometry': mapping(shape(elem['geometry'])),
                'properties': {'raster_val': elem['properties']['raster_val']}
            })
            pbar.update(1)

    pbar.close()  # close progress bar when done

    print(">> The polygons have been saved to the destination.")

except rasterio.errors.RasterioIOError as e:
    print(f"RasterioIOError: {e}. Please check the file path and format.")
except UnicodeDecodeError as e:
    print(f"UnicodeDecodeError: {e}. This may indicate an issue with the file encoding.")
except Exception as e:
    print(f"An unexpected error occured: {e}.")
