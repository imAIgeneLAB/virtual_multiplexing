"""
Ideas for zipping:

Use dask which already parralellizes the image
- Perform segmentation (e.g. RDCnet) on blocks with enough overlap
- Remove boundaries to split touching organoids (leaves border touching intact)
- Relabel using dask connected labelling through blocks on non-boundary segments
- Refill original segments (boundary regions) with the new segment labels


TESTING:
on (27,500,500) shaped blocks (27,1000,1000) original (4 blocks):

N_workers 2, n_thread=1
max used memory = 5.1 Gb

N_workers 1, n_thread=1
max used memory = 2.9 Gb


https://j23414.github.io/jekyll_rtd/geospatial/session3-intro-to-python-dask-on-ceres.html

"""
import os
import dask
from dask.distributed import Client, LocalCluster
import logging
# from dask_cuda import LocalCUDACluster
from dask_jobqueue import SLURMCluster

from dask.diagnostics import ProgressBar
import zarr
import tifffile
import dask.array as da
from general_segmentation_functions.image_handling import get_image,save_image,view_napari
from deep_learning.stardist.stardist_model import StarDist3r
import cv2 
from itertools import product
from dask_image import ndmeasure as dask_ndmeasure
from pathlib import Path
from skimage.segmentation import find_boundaries, watershed, expand_labels, clear_border
from scipy.ndimage import distance_transform_edt, generate_binary_structure
import numpy as np

import tensorflow as tf
from rdcnet.postprocessing.voting import embeddings_to_labels

import tracemalloc
tracemalloc.start()

def convert_size(size_bytes, result_size=None, number_only=False):
    import math
    if size_bytes == 0:
        if number_only:
            return 0
        else:
            return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    if not result_size:
        i = int(math.floor(math.log(size_bytes, 1024)))
    else:
        i = size_name.index(result_size)
    p = math.pow(1024, i)
    # s = round(size_bytes / p, 2)
    if number_only:
        return(size_bytes / p)
    else:
        return "%s %s" % (round(size_bytes / p, 2), size_name[i])
    
def track_memory():
    current_mem, max_mem = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    current_mem = convert_size(current_mem)
    max_mem = convert_size(max_mem)
    print(f"Current Memory used: {current_mem}\nMax Used Memory: {max_mem}")

def tiff_to_zarr():
    image = tifffile.imread("/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest400x400.tiff")

    # chunk_size = (60, 400, 400)
    # overlap = (0, 50, 50)

    dask_array = da.from_array(image, chunks=chunk_size)
    # dask_array_overlapping = da.overlap.overlap(dask_array, depth=overlap, boundary=0)

    zarr_path = '/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest400x400.zarr'
    zarr_store = zarr.DirectoryStore(zarr_path)

    da.to_zarr(dask_array, zarr_store, overwrite=True)

def get_nonexisting_zarr_blocks(zarr_path, dask_img):
    existing_store = zarr.open(zarr_path, mode='r')
    existing_keys = existing_store.store.keys()
    existing_keys = [x for x in existing_keys if x!=".zarray"]
    num_blocks = dask_img.numblocks
    block_indices = list(product(*(range(n) for n in num_blocks)))
    block_indices = [".".join(map(str, tpl)) for tpl in block_indices]
    non_existent_blocks=list(set(block_indices).symmetric_difference(set(existing_keys)))
    return(non_existent_blocks)

def predict_rdcnet(img, model_dir):
    
    ## For 3D, image requires batch dimension (1,164,512,512)
    if img.ndim == 3:
        img=np.expand_dims(img, axis=0)
    
    reloaded_model = tf.keras.models.load_model(os.path.join(model_dir, 'trained_model'), compile=False)
    reloaded_model.load_weights(Path(model_dir, 'trained_model/checkpoints/weights_best')) 

    embeddings, classes = reloaded_model.predict(img, use_multiprocessing=True)

    fg_mask = np.argmax(classes, axis=-1)[0]
    fg_mask = binary_closing(fg_mask, footprint=generate_binary_structure(fg_mask.ndim, 3))
    fg_mask = binary_opening(fg_mask, footprint=generate_binary_structure(fg_mask.ndim, 3))
    embeddings = embeddings[0]
    labels = embeddings_to_labels(embeddings,
                                  fg_mask,
                                  peak_min_distance=15,
                                  spacing=(2,1,1))
    labels=labels.numpy()
    return(labels)

def stardist_segment(img):
    stardist3r = StarDist3r()
    stardist3r.load_model("/hpc/pmc_rios/1.projects/SB1_ZippingOrganoidSegmentation/models/93_StarDistModel_HyperparameterTuning")
    labels, _ = stardist3r.predict(data=img, outpath=None, set_tiles=False)
    return(labels)  
    # embeddings, classes = reloaded_model.predict(raw[None, ..., None][0], use_multiprocessing=True)
#######
# gpu_options = {
#     0: '0',  # GPU 0 for worker 0
#     1: '1'   # GPU 1 for worker 1
# }

# # Create a Dask CUDA cluster with specified GPUs for each worker
# cluster = SLURMCluster(
#     queue='gpu', 
#     cores=1, 
#     memory="50GB",
#     # account='sdeblank',
#     # job_cpu=4,
#     # job_mem="32GB", 
#     walltime="02:00:00",
#     death_timeout=1000,
#     job_extra_directives=['--gpus-per-node=quadro_rtx_6000:1'],  # Specify the number of GPUs to allocate
#     # env_extra=['CUDA_VISIBLE_DEVICES=0']  # Restrict worker to GPU 0
#     # scheduler_options={
#     #     "dashboard_address": f":{portdash}"
#     #     }
#     )

cluster = LocalCluster(processes=False, n_workers=2, threads_per_worker=1)  # Set the desired number of workers
# client = Client(processes=False, n_workers=1, threads_per_worker=4)
client = Client(cluster)

# Define chunk size and overlap
chunk_size = (27, 240, 240)
overlap = (0, 50, 50)
print(track_memory())
# Input and output paths
zarr_path = '/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest.zarr'
zarr_seg_path = '/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest_stardist.zarr'
zarr_border_path = '/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest_border.zarr'
zarr_final_out_path = '/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest_segmented.zarr'

zarr_path = Path(zarr_path)
zarr_seg_path = Path(zarr_seg_path)
zarr_border_path = Path(zarr_border_path)
zarr_final_out_path = Path(zarr_final_out_path)

# Open the existing zarr array
img_dask = da.from_zarr(zarr.open(zarr_path))

if not zarr_seg_path.exists():
    segment=predict_rdcnet
    segments = img_dask.map_overlap(
        func=segment,
        dtype=np.int64,
        depth=overlap
    )

    with ProgressBar():
        segments.to_zarr(zarr_seg_path, overwrite=True, compute=True)
else:
    print("RDCnet has already run on full image, using existing zarr")
print(track_memory())
segments = da.from_zarr(zarr.open(zarr_seg_path))
# Function to remove boundaries using find_boundaries

def keep_largest_connected_components(img):
    # Label connected components
    img_subsegments = label(img>0, connectivity=3)
    
    # Iterate through unique labels
    for segment in np.unique(img):
        if segment == 0:  # Skip background label
            continue

        # Create a binary mask for the current label
        mask = img == segment

        # Calculate the size of the connected component
        subsegments, subsizes = np.unique(img_subsegments[mask], return_counts=True)
        biggest_segment = subsegments[np.argmax(subsizes)]
        img[(mask) & (img_subsegments != biggest_segment)]=0

    return img


def select_border_segments(image, dist_from_border=1, axes=None):
    # Selects only the border segments and keep non-border segments as original
    borders = []
    # Iterate over axes (z, y, x)
    if axes==None:
        axes=range(image.ndim)
    for axis in axes:
        slice_1 = tuple(slice(0,dist_from_border) if i == axis else slice(None) for i in range(image.ndim))
        slice_2 = tuple(slice(-dist_from_border, None) if i == axis else slice(None) for i in range(image.ndim))

        borders.append(image[slice_1].ravel())
        borders.append(image[slice_2].ravel())

    border_segments = np.unique(np.concatenate(borders))
    border_mask=np.isin(image, border_segments)
    segments = image * border_mask
    return segments

def remove_boundaries(img):
    # Set connectivity to 1, otherwise too many small segments come to be
    bound = find_boundaries(img, connectivity=img.ndim, mode="inner")
    mask = (img>0).astype(np.int64)
    # mask = distance_transform_edt(mask)
    img[bound] = 0
    img = keep_largest_connected_components(img)
    img = np.stack([img, mask], axis=0)
    return img

def select_border_and_remove_boundaries(image, axes=None):
    image=select_border_segments(image, axes=axes)
    image=remove_boundaries(image)
    return(image)

borders = [axis for axis, numblocks in enumerate(segments.numblocks) if numblocks > 1]
border_segments = segments.map_blocks(
    func=select_border_and_remove_boundaries,
    dtype=np.float64,
    # chunks=(2,)+chunk_size,
    new_axis=0,
    axes=borders
)

# Structure of connection 2 needed, otherwise all segments are connected
structure=generate_binary_structure(border_segments[0].ndim, 2)

# structure = np.ones([3]*border_segments[0].ndim)
border_segments[0], _ = dask_ndmeasure.label(border_segments[0], structure=structure)

def filter_and_refill_full_segments(img):
    # !!! CHANGE WATERSHED TO EXPAND LABELS
    # img = watershed(
    #     image=img[1], 
    #     markers=img[0].astype(np.int64), 
    #     mask=img[1]>0
    #     )
    # for z, plane in enumerate(img[0]):
    #     img[0][z]=expand_labels(plane, distance=12)
    # df_img = pd.DataFrame(regionprops_table(img[0], properties=('label', 'num_pixels')))
    # small_labels = df_img[df_img["num_pixels"]<2000]["label"].tolist()
    # small_mask = np.isin(img[0], small_labels)
    # img[0][small_mask]=0
    
    img[0]=expand_labels(img[0], distance=12)
    img[0][img[1]==0]=0
    img[0] = watershed(
        image=img[1], 
        markers=img[0].astype(np.int64), 
        mask=img[1]>0
        )
    return img[0]

border_segments = border_segments.map_blocks(
    func=filter_and_refill_full_segments,
    dtype=np.int64,
    # chunks=chunk_size,
    drop_axis=0
)

def recombine(full_segments, refilled_border_segments):
    # !!!! MAKE SURE TO REMOVE BORDER SEGMENTS FIRST, OR EXPAND EVEN FURTHER, OTHERWISE SMALL SEGMENTS APPEAR
    full_segments[refilled_border_segments!=0]=refilled_border_segments[refilled_border_segments!=0]
    return(full_segments)

final_segments = da.map_blocks(
    recombine, 
    segments, 
    border_segments, 
    dtype=np.int64
    )

final_segments.to_zarr(zarr_final_out_path, overwrite=True, compute=True)
print(track_memory())
final_segments =  da.from_zarr(zarr.open(zarr_final_out_path))

client.close()