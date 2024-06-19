# MUST RUN IN QGIS PYTHON API

from qgis.core import (
    QgsApplication,
    QgsVectorLayer,
    QgsProject,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFields,
    QgsFeatureSink
)

# Initialize QGIS application
app = QgsApplication([], True)
app.initQgis()

# Load shapefile
dataset_path = '/Volumes/TKssd/dataBackup/Satellites/Global_mangrove/'
shapefile_path = 'Global Mangrove 2020/ChinaMangrove2020/'
shp = QgsVectorLayer(
    path=dataset_path + shapefile_path + 'ChinaMangrove2020.shp',
    baseName='ChinaMangrove', 
    providerLib='ogr'
)

# Convert CRS
original_crs = QgsCoordinateReferenceSystem(102025)  # WGS_84_Albers
target_crs = QgsCoordinateReferenceSystem(4326)  # WGS_84
transform = QgsCoordinateTransform(original_crs, target_crs)
for f in shp.getFeature():
    g = f.geometry()
    if g.isMultipart():
        for part in g.parts():
            part.transform(transform)
    else:
        g.transform(transform)
    f.setGeometry(g)
    shp.dataProvider().changeGeometryValues({f.id(): g})
shp.commitChanges()

# save the reprojected shapefile
shp.saveToFile(f"{dataset_path + shapefile_path}/ChinaMangrove2020_wgs84.shp")

# Define the number of polygons per file
polygons_per_file = 40

# Iterate through polygons and create separate files
for i in range(0, shp.featureCount(), polygons_per_file):
    # create a new layer for the current batch of polygons
    new_layer_name = f"fc_{i + 1}_{i + polygons_per_file}"
    new_layer = QgsVectorLayer(
        new_layer_name,
        new_layer_name,
        QgsWkbTypes.MultiPolygon,
        shp.crs()
    )
    new_fields = QgsFields()
    for field in shp.fields():
        new_fields.append(QgsFields(field.name(), field.type()))
    new_fields.dataProvider().addAttributes(new_fields)
    new_layer.updateFields()

    # create a feature sink to write features to the new layer
    sink = QgsFeatureSink.fromLayer(new_layer)

    # Iterate through the current batch of polygons
    for j in range(i, min(i + polygons_per_file, shp.featureCount())):
        feature = shp.getFeature(j)
        sink.addFeature(feature)
    # Save the new layer to a shapefile
    new_layer.commitChanges()
    new_layer.saveToFile(f"{new_layer_name}.shp")

# Exit QGIS
QgsApplication.exitQgis()
