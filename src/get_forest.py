# Create shapefile from raster based on band values

import numpy as np
import fiona
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from rasterio.enums import Resampling
from rasterio.warp import reproject
from shapely.geometry import shape, mapping
from tqdm import tqdm


def degrees_to_meters(latitude, longitude, latitude_resolution, longitude_resolution):
    """
    Converts resolution from degrees to meters at the given latitude and longitude.
    :param latitude:
    :param longitude:
    :param latitude_resolution:
    :param longitude_resolution:
    :return:
    """
    from pyproj import CRS
    from math import sqrt

    # define WGS84 coordinate system
    wgs84 = CRS.from_epsg(4326)
    # define a local UTM zone coordinate system
    utm_zone = int((longitude + 180) / 6) + 1
    utm = CRS.from_proj4(f"+proj=utm +zone={utm_zone} +datum=WGS84")

    transformer = Transformer.from_crs(wgs84, utm, always_xy=True)

    # convert latitude and longitude resolution to meters
    lon1, lat1 = transformer.transform(longitude, latitude)
    lon2, _ = transformer.transform(longitude + longitude_resolution, latitude)
    _, lat3 = transformer.transform(longitude, latitude_resolution + latitude)

    longitude_res_in_meter = sqrt((lon2 - lon1) ** 2)
    latitude_res_in_meter = sqrt((lat3 - lat1) ** 2)

    return longitude_res_in_meter, latitude_res_in_meter


def get_selection_criteria(d):
    criteria_type = input("Select a range or a specific band value? (value/range): ").strip().lower()
    if criteria_type == 'value':
        value = int(input("Please enter the band value to select: ").strip())
        return d == value
    elif criteria_type == 'range':
        min_val = float(input("Please enter the lower range of band value: ").strip())
        max_val = float(input("Please enter the upper range of band value: ").strip())
        return (d >= min_val) & (d <= max_val)
    else:
        print("Invalid input. Please enter 'value' or 'range'.")
        return get_selection_criteria(d)


path_to_tif = input("-- Path to the raster file: ")
path_for_export = input("-- Path to the export file (Remember with .shp): ")

# A divert-er for image process
divert = 0
while divert == 0:
    print("-- Please select the following pre-defined types of your input raster:")
    print("   [A] CLCD images (albert, 30m), [B] Global Plantation Products (WGS84, 0.0003deg), [C] Others.")
    choice = input('   A/B/C: ').strip().upper()
    if choice == "A":
        print(">> CLCD product selected.")
        tif_type = "CLCD"
        divert = 1
    elif choice == "B":
        print(">> Global Plantation product selected.")
        tif_type = "GP"
        divert = 1
    elif choice == "C":
        print(">> Not pre-defined product. Please set up the criteria for shapefile creation later.")
        tif_type = "others"
        divert = 1
    else:
        print("!! Invalid input. Please enter letter y or n.")

try:
    # load the raster data
    with rasterio.open(path_to_tif) as src:
        print(">> Reading raster...")
        # read the first band only
        data = src.read(1)

        # display current resolution
        if tif_type == 'CLCD':
            current_resolution = src.res
            print(f"-- Current resolution: {current_resolution[0]} meters.")
        else:
            lon_res, lat_res = src.res
            center_lat = (src.bounds.top + src.bounds.bottom) / 2
            center_lon = (src.bounds.left + src.bounds.right) / 2
            lon_res_m, lat_res_m = degrees_to_meters(center_lat, center_lon, lat_res, lon_res)
            print(f"-- Current resolution: {lon_res_m:.2f} meters x {lat_res_m:.2f} meters.")
        # ask if perform resampling
        resample = input("   Resample the raster? (yes/no): ").strip().lower()

        if resample == 'yes':
            print(">> Getting ready for resampling...")
            # ask for the target resolution
            target_resolution = float(input("-- Target resolution (in meters): ").strip())
            if tif_type == 'CLCD':
                # calculate new dimensions
                new_width = int((src.width * src.res[0]) / target_resolution)
                new_height = int((src.height * src.res[1]) / target_resolution)
                # calculate new transform
                scale_x = target_resolution / current_resolution[0]
                scale_y = target_resolution / current_resolution[1]
            elif tif_type == 'GP':
                # calculate new width and height
                new_width = int((src.width * lon_res_m) / target_resolution)
                new_height = int((src.height * lat_res_m) / target_resolution)
                # calculate new transform
                scale_x = target_resolution / lon_res_m
                scale_y = target_resolution / lat_res_m

            new_transform = src.transform * src.transform.scale(scale_x, scale_y)

            # create a new array for the resampled data
            resampled_data = np.empty((new_height, new_width), dtype=src.dtypes[0])

            print(">> Resampling the raster...")
            # resample data to the target resolution
            reproject(
                source=data,
                destination=resampled_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=new_transform,
                dst_crs=src.crs,
                resampling=Resampling.mode
            )
            data = resampled_data
            print(">> Resample finished.")
        else:
            new_transform = src.transform
            print(">> Original raster loaded.")

        crs = src.crs

    # extract the forest class
    if tif_type == "CLCD":
        forest_mask = data == 2
    elif tif_type == "GP":
        # select band values not equal to 0
        forest_mask = data != 0
    else:
        forest_mask = get_selection_criteria(data)

    # convert the mask to polygons
    print(">> Reading shapes of pixels in target class...")
    results = (
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) in enumerate(
            shapes(forest_mask.astype(np.uint8), mask=forest_mask, transform=new_transform))
    )

    # define schema for the shapefile
    schema = {
        'geometry': 'Polygon',
        'properties': {'raster_val': 'int'}
    }

    print(">> Ready to start conversion..")

    # initialize progress bar
    total_polygons = np.sum(forest_mask)
    pbar = tqdm(total=total_polygons, desc="Converting polygons")

    # write the polygons to a shapefile
    with fiona.open(path_for_export, 'w', driver='ESRI Shapefile', crs=crs, schema=schema) as out:
        for elem in results:
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
