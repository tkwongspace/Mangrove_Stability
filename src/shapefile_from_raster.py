# Create shapefile from raster based on band values

import numpy as np
import fiona
import rasterio
from rasterio.features import shapes
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from shapely.geometry import shape, mapping
from tqdm import tqdm


path_to_tif = input("Path to the raster file: ")
path_for_export = input("Path to the export file (Remember with .shp): ")

try:
    # load the raster data
    with rasterio.open(path_to_tif) as f:
        # display current resolution
        current_resolution = f.res
        print(f"-- Current resolution: {current_resolution} meters.")
        # ask if perform resampling
        resample = input("   Resample the raster? (yes/no): ").strip().lower()

        if resample == "yes":
            # ask for target resolution
            target_resolution = float(input("-- Target resolution (in meters): ").strip())

            # calculate new transform and dimensions
            transform, width, height = calculate_default_transform(
                f.crs, f.crs, f.width, f.height,
                resolution=(target_resolution, target_resolution),
                dst_width=f.width * f.res[0] / target_resolution,
                dst_height=f.height * f.res[1] / target_resolution
            )
            profile = f.profile
            profile.update(transform=transform, width=width, height=height)

            # create a new array for the resampled data
            data = np.empty((height, width), dtype=f.dtypes[0])

            print(">> Resampling the raster..")

            # resample the data to the target resolution
            reproject(
                source=rasterio.band(f, 1),
                destination=data,
                src_transform=f.transform,
                src_crs=f.crs,
                dst_transform=transform,
                dst_crs=f.crs,
                resampling=Resampling.mode
            )

            print(">> Resample finished.")

        else:
            # no resampling, use the original data
            image = f.read(1)
            transform = f.transform
            profile = f.profile
            print(">> Original raster loaded.")

        crs = f.crs

    # extract the forest class
    mask = image == 2

    # convert the mask to polygons
    print(">> Reading shapes of pixels in target class...")
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

    print(">> Ready to start conversion..")

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
    print(f"An unexpected error occurred: {e}.")
