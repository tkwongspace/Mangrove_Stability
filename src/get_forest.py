# Create shapefile from raster based on band values

import rasterio
from rasterio.mask import mask
from shapely.geometry import box
from get_forest_tools import *

path_to_tif = input("-- Path to the raster file: ")

# A divert-er for image process
tif_type = get_raster_type()

# Main process
try:
    with rasterio.open(path_to_tif) as src:
        # load the raster data
        print(">> Reading raster...")
        tif, lon_res, lat_res, target_resolution = get_resample_info(src, tif_type)

        # Local masks
        path_to_mask, path_to_export, prefix_for_export = whether_to_clip()

        # Process the raster
        if path_to_mask is None:
            # --> process the whole raster directly
            create_shapefile(
                src=src,
                data=tif,
                data_type=tif_type,
                longitude_in_meter=lon_res,
                latitude_in_meter=lat_res,
                transform=src.transform,
                target_resolution=target_resolution,
                path_to_export=path_to_export,
                prefix_to_export=None,
                roi=None,
                file_name=None
            )
        else:
            # --> clip before processing the data
            with fiona.open(path_to_mask, 'r') as roi:
                for province in roi:
                    roi_name = province['properties']['Province']
                    roi_geometry = shape(province['geometry'])
                    print(f">> Now clipping area of {roi_name}.")
                    # get the minimum bounding rectangle of the roi geometry
                    minx, miny, maxx, maxy = roi_geometry.bounds
                    bbox = box(minx, miny, maxx, maxy)
                    # clip the raster with the roi geometry
                    try:
                        clipped_image, clipped_transform = mask(src, [mapping(bbox)], crop=True)
                    except ValueError as e:
                        continue
                    # convert pixels and create shapefile
                    create_shapefile(
                        src=src,
                        data=clipped_image[0],  # first band only
                        data_type=tif_type,
                        longitude_in_meter=lon_res,
                        latitude_in_meter=lat_res,
                        transform=clipped_transform,
                        target_resolution=target_resolution,
                        path_to_export=path_to_export,
                        prefix_to_export=prefix_for_export,
                        roi=roi_geometry,
                        file_name=roi_name
                    )
    print(">> The polygons have been saved to the destination.")

except rasterio.errors.RasterioIOError as e:
    print(f"RasterioIOError: {e}. Please check the raster path and format.")
except UnicodeDecodeError as e:
    print(f"UnicodeDecodeError: {e}. This may indicate an issue with the raster encoding.")
except Exception as e:
    print(f"An unexpected error occurred: {e}.")
