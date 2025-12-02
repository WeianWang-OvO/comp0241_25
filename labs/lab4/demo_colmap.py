"""
An example for running incremental SfM on images with the pycolmap interface.
"""
import shutil
import urllib.request
import zipfile
from pathlib import Path
import enlighten
import pycolmap 
from pycolmap import logging
from visualizer import visualize_reconstruction  # Import the visualization function


def incremental_mapping_with_pbar(database_path, image_path, sfm_path):
    num_images = pycolmap.Database(database_path).num_images
    with enlighten.Manager() as manager:
        with manager.counter(
            total=num_images, desc="Images registered:"
        ) as pbar:
            pbar.update(0, force=True)
            reconstructions = pycolmap.incremental_mapping(
                database_path,
                image_path,
                sfm_path,
                initial_image_pair_callback=lambda: pbar.update(2),
                next_image_callback=lambda: pbar.update(1),
            )
    return reconstructions


def choose_dataset():
    print("Choose a dataset:")
    print("1. Fountain (will download if not found)")
    print("2. South Building")
    print("3. Custom path")
    
    choice = input("Enter choice (1-3): ")
    
    if choice == '1':
        return "fountain", "Fountain/images", "https://cvg-data.inf.ethz.ch/local-feature-evaluation-schoenberger2017/Strecha-Fountain.zip"
    elif choice == '2':
        return "south-building", "south-building/images", "https://demuc.de/colmap/datasets/south-building.zip"
    elif choice == '3':
        custom_path = input("Enter path to image folder: ")
        folder_name = Path(custom_path).name
        return folder_name, custom_path, None
    else:
        print("Invalid choice, defaulting to Fountain")
        return "fountain", "Fountain/images", "https://cvg-data.inf.ethz.ch/local-feature-evaluation-schoenberger2017/Strecha-Fountain.zip"


def run():
    base_path = Path(__file__).resolve().parent / "example"
    dataset_name, image_dir, data_url = choose_dataset()
    
    # Create dataset-specific paths
    dataset_path = base_path / dataset_name
    image_path = base_path / image_dir
    database_path = dataset_path / "database.db"
    sfm_path = dataset_path / "sfm"

    # Create necessary directories
    base_path.mkdir(exist_ok=True)
    dataset_path.mkdir(exist_ok=True)
    
    # Set up logging for this dataset
    logging.set_log_destination(logging.INFO, dataset_path / "INFO.log")

    if data_url and not image_path.exists():
        logging.info("Downloading the data.")
        zip_path = base_path / "data.zip"
        urllib.request.urlretrieve(data_url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as fid:
            fid.extractall(base_path)
        logging.info(f"Data extracted to {base_path}.")

    if database_path.exists():
        database_path.unlink()
    pycolmap.set_random_seed(0)
    # SIFT extraction options
    # Initialize an empty SiftExtractionOptions instance
    sift_extraction_options = pycolmap.SiftExtractionOptions()

    # Assign individual options
    sift_extraction_options.num_threads = 8
    sift_extraction_options.max_image_size = 640
    sift_extraction_options.max_num_features = 1000  # Increased to detect more features

    sift_extraction_options.normalization = pycolmap.Normalization.L1_ROOT

    pycolmap.extract_features(database_path, image_path, sift_options=sift_extraction_options)

    MatchingOptions = pycolmap.ExhaustiveMatchingOptions()
    MatchingOptions.block_size = 150
    pycolmap.match_exhaustive(database_path,matching_options=MatchingOptions)

    if sfm_path.exists():
        shutil.rmtree(sfm_path)
    sfm_path.mkdir(exist_ok=True)

    recs = incremental_mapping_with_pbar(database_path, image_path, sfm_path)
    
    for idx, rec in recs.items():
        logging.info(f"#{idx} {rec.summary()}")
        # Launch visualization for this reconstruction
        reconstruction_path = sfm_path / str(idx)
        print(f"\nLaunching visualization for reconstruction {idx}...")
        visualize_reconstruction(reconstruction_path, image_path)


if __name__ == "__main__":
    run()