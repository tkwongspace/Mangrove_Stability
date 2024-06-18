import ee
import time
import logging

# Initialize GEE
ee.Initialize()

# Configure logging
logging.basicConfig(level=logging.INFO)


def log_task_times(task_description):
    start_time = time.time()
    task = ee.batch.Export.table.toDrive(
        collection=ee.FeatureCollection([]),  # Placeholder collection
        description=task_description,
        fileFormat='CSV'
    )
    task.start()
    logging.info(f"Task '{task_description}' started at {time.ctime(start_time)}")

    while task.active():
        time.sleep(5)  # Check status every 5 seconds
        logging.info(f"Checking task '{task_description}' status...")

    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Task '{task_description}' completed at {time.ctime(end_time)}, "
                 f"duration: {elapsed_time / 60:.2f} minutes")

    return elapsed_time


# Run a test task
task_duration = log_task_times('Test_Task')
