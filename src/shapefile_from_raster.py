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


# def get_selection_criteria(d):
#     criteria_type = input("Select a range or a specific band value? (value/range): ").strip().lower()
#     if criteria_type == 'value':
#         value = int(input("Please enter the band value to select: ").strip())
#         return d == value
#     elif criteria_type == 'range':
#         min_val = float(input("Please enter the lower range of band value: ").strip())
#         max_val = float(input("Please enter the upper range of band value: ").strip())
#         return (d >= min_val) & (d <= max_val)
#     else:
#         print("Invalid input. Please enter 'value' or 'range'.")
#         return get_selection_criteria(d)


try:
    # load the raster data
    with rasterio.open(path_to_tif) as src:
        # display current resolution
        current_resolution = src.res
        print(f"-- Current resolution: {current_resolution[0]} meters.")
        # ask if perform resampling
        resample = input("   Resample the raster? (yes/no): ").strip().lower()

        if resample == "yes":
            # ask for target resolution
            target_resolution = float(input("-- Target resolution (in meters): ").strip())

            # calculate new dimensions
            new_width = int((src.width * src.res[0]) / target_resolution)
            new_height = int((src.height * src.res[1]) / target_resolution)

            # calculate new transform
            scale_x = target_resolution / current_resolution[0]
            scale_y = target_resolution / current_resolution[1]
            new_transform = src.transform * src.transform.scale(scale_x, scale_y)

            # create a new array for the resampled data
            data = np.empty((new_height, new_width), dtype=src.dtypes[0])

            print(">> Resampling the raster..")

            # resample the data to the target resolution
            reproject(
                source=rasterio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=new_transform,
                dst_crs=src.crs,
                resampling=Resampling.mode
            )

            print(">> Resample finished.")

        else:
            # no resampling, use the original data
            data = src.read(1)
            new_transform = src.transform
            # profile = src.profile
            print(">> Original raster loaded.")

        crs = src.crs

    # extract the forest class
    # mask = get_selection_criteria(data)
    mask = data == 2

    # convert the mask to polygons
    print(">> Reading shapes of pixels in target class...")
    polygons = (
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) in enumerate(
            shapes(mask.astype(np.uint8), mask=mask, transform=new_transform))
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
