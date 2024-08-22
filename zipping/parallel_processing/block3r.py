"""
This code uses the "dask" and "zarr" packages to perform parallel processing of images.

Benefits:
- Converting normal images to the .zarr format, you can load separate blocks of the image to lower memory usage
- Based on supplied parallel processes, memory usage can be varied by loading only X blocks at once
- These blocks are closed when processing the next blocks, keeping memory low
"""
import os
import sys
import logging
from pathlib import Path
from itertools import product
import numpy as np
import pandas as pd

import dask
from dask.distributed import Client, LocalCluster
if sys.platform == "linux":
    from dask_cuda import LocalCUDACluster
import dask.array as da

# from dask_cuda import LocalCUDACluster
from dask_jobqueue import SLURMCluster
from dask.diagnostics import ProgressBar
from dask_image import ndmeasure as dask_ndmeasure
from dask_image import imread as dask_imread

from dask_image.imread import imread as da_imread

import zarr
import tifffile

from skimage.segmentation import find_boundaries, watershed, expand_labels
from skimage.morphology import binary_closing, binary_opening
from skimage.measure import label
from scipy.ndimage import generate_binary_structure

import tensorflow as tf
# from rdcnet.postprocessing.voting import embeddings_to_labels
# from deep_learning.stardist.stardist_model import StarDist3r

import tracemalloc
tracemalloc.start()

class Block3r():
    def __init__(self, img_path="", outfolder="", **kwargs):
        
        if img_path != "":
            self.image_path = Path(img_path)
            self.outfolder = self.image_path.parent
            if self.image_path.suffix != ".zarr":
                print("Recommend converting supplied image to zarr: Run 'convert_to_zarr(img_path, zarr_path)'")
            else:
                self.image = self._load_zarr_image(self.image_path)
                self.chunksize = self.image.chunksize
            
        if outfolder != "":
            self.outfolder = Path(outfolder)
            self.outfolder.mkdir(parents=True, exist_ok=True)
               
        self.client = None

    def rdcnet_segmentation(
        self, 
        rdcnet_model_folder,
        overlap = (0, 100, 100),
        outpath=None,
        skip_finished_steps=True,
        recombine_to_tiff=True
    ):
        """
        Use dask for the parralel, blockwise rdcnet segmentation and merging of resulting segmented blocks.
        (See 'stitch_segmentation' function for explanation on stitching)
        
        Input: .zarr file
        Output: .zarr file or .tiff file
        
        Segmentation consist of a few steps:
        - Load the .zarr
        - Match supplied blocksizes and overlap to image dimensions
        - Perform blockwise RDCnet segmentation
        - Perform stitching of segments across blocks
        - (Optionally) Output to a stitched .tiff image
    
        """
        # Check if active dask client is running
        # self._assert_active_client()
        self.rdcnet_model = rdcnet_model_folder
        # Load the image_path if it is not loaded yet
        if self.image is None:
            self.image = self._load_zarr_image()
        
        # Create default outpath if none is supplied
        if outpath is None:
            rdcnet_outpath = Path(self.outfolder, f"{self.image_path.stem}_rdcnet-segmented.zarr")
        else:
            rdcnet_outpath = Path(self.outfolder, f"{outpath.stem}_rdcnet-segmented.zarr")
            
        overlap = self.match_dimensions_to_image(
                overlap,
                self.image,
                fill_with_imagedim=False
            )
        
        # Set up RDCnet segmentation in parallel     
        segments = self.image.map_overlap(
            func=self.predict_rdcnet,
            dtype=np.int64,
            depth=overlap,
            model_dir=self.rdcnet_model
        )
        
        if rdcnet_outpath.exists() and skip_finished_steps:
            print(f"RDCnet results are already available.\n{rdcnet_outpath}\nSkipping...")
        else:
            # Perform RDCnet segmentation in parallel and write output to zarr to keep memory low
            with ProgressBar():
                segments.to_zarr(rdcnet_outpath, overwrite=True, compute=True)

        # Update image and image_path
        self.image =  da.from_zarr(zarr.open(rdcnet_outpath))
        self.image_path = rdcnet_outpath
        
        if outpath is None:
            stitched_outpath = Path(self.outfolder, f"{self.image_path.stem}_rdcnet-stitched.zarr")
        else:
            stitched_outpath = outpath
        # Stitch the segments over all blocks to get correct segment IDs
        self.stitch_segmentation(
            outpath=stitched_outpath
        )
        
        if recombine_to_tiff:
            if outpath is None:
                stitched_outpath = Path(self.outfolder, f"{self.image_path.stem}_rdcnet-segmented.tiff")
            else:
                stitched_outpath = outpath
            self.recombine_to_tiff(img=self.image, out_path=None)
            
    def stitch_segmentation(
        self, 
        outpath=None,
        ):      

        """
        Use dask for the parralel 'stitching' of segmentation results.
        This performs resegmentation to connect segments between blocks to connect them
        
        It consist of a few steps:
        
        - Remove the boundaries of all segments to disconnect them 
            (except the part touching the block borders)
        - For each segment, only keep the largest conected component
            (So dask labelling does not relabel disconnected segments from original segment)
        - Stack with original segment mask for relabeling
        - Connected component relabeling over blocks with dask
        - Refill original segments using new segments as seeds
            (expand_labels to equally grow each segment to better get original shape)
            (watershed to make sure last possible remaining voxels of the original mask is fully filled)
            (Any segment voxels outside the original segment mask are removed)
            
        Outpath is a .zarr file
        """
        
        # Check if active dask client is running
        # self._assert_active_client()
        
        # Open the existing zarr array
        if self.image is None:
            self.image = self._load_zarr_image()
        
        if outpath is None:
            outpath = Path(self.outfolder, f"{self.image_path.stem}_stitched.zarr")
        else:
            outpath = Path(outpath)    
                 
        outpath.mkdir(parents=True, exist_ok=True)
        
        def keep_largest_connected_components(img):
            """
            Select all separate connected components of the same segment ID
            Only keep the largest one, set other subsegments to 0
            """
            img_subsegments = label(img>0, connectivity=3)
            for segment in np.unique(img):
                if segment == 0: 
                    continue
                mask = img == segment

                # Calculate the size of the connected component and only keep the largest
                subsegments, subsizes = np.unique(img_subsegments[mask], return_counts=True)
                biggest_segment = subsegments[np.argmax(subsizes)]
                img[(mask) & (img_subsegments != biggest_segment)]=0
            return img

        def remove_boundaries(img):
            """
            Remove the boundaries of each segment.
            Keep the largest connected component per segment
            Stack the boundary-removed segments with the original segment mask image
            """
            bound = find_boundaries(img, connectivity=img.ndim, mode="inner")
            mask = (img>0).astype(np.int64)
            img[bound] = 0
            img = keep_largest_connected_components(img)
            img = np.stack([img, mask], axis=0)
            return img

        stitched_segments = self.image.map_blocks(
            func=remove_boundaries,
            dtype=np.float64,
            new_axis=0
        )
        
        # Structure of connection 2 needed, otherwise all segments are connected
        structure=generate_binary_structure(stitched_segments[0].ndim, 2)
        # Relabel over neighbouring blocks
        stitched_segments[0], _ = dask_ndmeasure.label(stitched_segments[0], structure=structure)

        def refill_full_segments(img):         
            """
            Refill the segment by first using the skimage "expand_labels" function
            Refill last remaining pixels with a watershed function
            """  
            img[0]=expand_labels(img[0], distance=12)
            img[0][img[1]==0]=0
            img[0] = watershed(
                image=img[1], 
                markers=img[0].astype(np.int64), 
                mask=img[1]>0
                )
            return img[0]

        stitched_segments = stitched_segments.map_blocks(
            func=refill_full_segments,
            dtype=np.int64,
            drop_axis=0
        )
        
        def recombine(full_segments, relabeled_segments):
            full_segments[relabeled_segments!=0]=relabeled_segments[relabeled_segments!=0]
            return(full_segments)

        stitched_segments = da.map_blocks(
            recombine, 
            self.image, 
            stitched_segments, 
            dtype=np.int64
            )

        stitched_segments.to_zarr(outpath, overwrite=True, compute=True)
        self.image =  da.from_zarr(zarr.open(outpath))
        self.image_path = outpath
        return(self.image)
        
    def _assert_active_client(self):
        assert self.client is not None, "Client not initialized yet, do so with 'initialize_cluster'"
    
    """
    Data loading
    """
    
    def convert_to_zarr(self, img_path=None, out_path=None, chunksize=None):
        """
        Convert an input image (.tiff) into the .zarr format for parallel processing
        """
        if img_path is not None:
            self.image_path = Path(img_path)
        
        assert self.image_path != "", "No img_path is supplied, please supply it in this function"
        if out_path is None:
            out_path = self.image_path.with_suffix(".zarr")
        
        
        if self.image_path.suffix==".zarr":
            print("Supplied image path is already in the .zarr format")
            print(self.image_path)
            print("Loading .zarr instead")
            self.image = self._load_zarr_image(self.image_path)
            self.chunksize = self.image.chunksize
            print(f"Using chunksize of supplied .zarr {self.chunksize}")
            if chunksize is not None and chunksize != self.chunksize:
                print("This is not the same as supplied chunksize {chunksize}")
                print("If that chunksize is wanted, reconvert to .zarr or rechunk .zarr")
        else:
            if chunksize is not None:
                self.chunksize = chunksize
            image = self._open_tiff_image(self.image_path)
            
            self.chunksize = self.match_dimensions_to_image(
                self.chunksize,
                image,
                fill_with_imagedim=True
            )
            
            dask_array = da.from_array(image, chunks=self.chunksize)
            zarr_store = zarr.DirectoryStore(out_path)
            da.to_zarr(dask_array, zarr_store, overwrite=True)
            self.image_path = out_path
            self.image =  self._load_zarr_image(self.image_path)           
        
    def recombine_to_tiff(self, img=None, img_path=None, out_path=None,):
        """
        Recombine the blocked .zarr image into a single stitched .tiff image
        """
        if img is not None:
            self.image = img
            
        if img_path is not None:
            self.image_path = Path(img_path)
            
        if self.image is None:
            assert self.image_path != "", "No img or img_path is supplied, please supply it in this function"
            self.image =  self._load_zarr_image(self.image_path)
        # assert self.image_path.suffix != ".zarr", f"img_path is not .zarr format\n{img_path}"

        if out_path is None:
            out_path = self.image_path.with_suffix(".tiff")
        
        self.image =  self._load_zarr_image(self.image_path)
        tifffile.imsave(out_path, np.asarray(self.image))
        
    def _load_zarr_image(self, img_path):
        dask_img = da.from_zarr(zarr.open(img_path))
        return(dask_img)
    
    def _open_tiff_image(self, img_path):
        return(tifffile.imread(img_path))
    
    """
    Segmentation algorithms
    """
    def predict_rdcnet(self, img, model_dir):
        """
        Perform segmentation using the RDCnet deep learnign network.
        
        Steps:
        - Load the trained RDCnet model
        - Predict segmentatio from supplied img using the RDCnet model
        - Perform post-processing on the resulting foreground mask to remove rough borders (pixelly borders) often resulting from RDCnet
        - Turn the output from the RCDnet prediction into segments
        """
        ## For 3D, image requires batch dimension (1,164,512,512)
        if img.ndim == 3:
            img=np.expand_dims(img, axis=0)
        
        reloaded_model = tf.keras.models.load_model(os.path.join(model_dir, 'trained_model'), compile=False)
        reloaded_model.load_weights(Path(model_dir, 'trained_model/checkpoints/weights_best')) 

        embeddings, classes = reloaded_model.predict(img, use_multiprocessing=True)

        fg_mask = np.argmax(classes, axis=-1)[0]
        # Remove small errorous segments that are sometimes the result of RDCnet
        # Remove noise segments and make them more smooth as expected
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
        """
        Perform segmenation using the StarDist deep learning module
        """
        stardist3r = StarDist3r()
        stardist3r.load_model("/hpc/pmc_rios/1.projects/SB1_ZippingOrganoidSegmentation/models/93_StarDistModel_HyperparameterTuning")
        labels, _ = stardist3r.predict(data=img, outpath=None, set_tiles=False)
        return(labels)  

    def close_client(self):
        if self.client is not None:
            self.client.close()
    
    def check_gpu_availablity(self):
        gpus = tf.config.list_physical_devices('GPU')
        assert len(gpus)!=0, "!!! No GPUs available, please check if tensorflow GPU is correctly installed and all CUDA versions match !!!"
        
        print("Available GPUs:")
        for gpu in gpus:
            print(gpu)
    
    def match_dimensions_to_image(self, dimension_list, image=None, fill_with_imagedim=True):
        """
        Matches the dimension_list (etc. chunksizes or overlap) to the full dimension of the image
        
        Example:
        ===============================================
        dimension_list = [100,100]
        image.dim = [60,100,100]
        
        Result with fill_with_imagedim=True:
        dimension_list = [60, 100, 100]
        
        Result with fill_with_imagedim=False:
        dimension_list = [0, 100, 100]
        ===============================================
        """
        if image is None:
            image=self.image()

        dimension_list = list(dimension_list)
        assert image is not None, 'No image loaded already or image is not specified'
        if fill_with_imagedim:
            dimension_list = list(image.shape[:image.ndim-len(dimension_list)]) + dimension_list
        else:
            dimension_list = [0] * (image.ndim-len(dimension_list)) + dimension_list
        return(dimension_list)
     
                
#######################################################
###### Initialize different types of Dask client ######
#######################################################

def initialize_local_dask_client(
        cpu_or_gpu="cpu",
        processes=False,
        n_workers=1,
        threads_per_worker=1,
        memory_limit="auto",
        **kwargs
    ):
    """
    processes: Whether to use processes (True) or threads (False)
    n_workers: Number of tasks to run in parallel
    memory_limit: Memory limit per worker (
        - if float provided --> percentage of memory per worker
        - if string ("1GiB") --> That amount of memory per worker
    threads_per_worker = Number of threads per worker
    """
 
    if cpu_or_gpu=="gpu" and sys.platform == "linux":
        cluster = LocalCUDACluster(
            processes=processes, 
            n_workers=n_workers, 
            threads_per_worker=threads_per_worker,
            memory_limit=memory_limit,
            # serializers=['dask'], 
            # deserializers=['dask'],
            **kwargs
            )
    else:
        cluster = LocalCluster(
            processes=processes, 
            n_workers=n_workers, 
            threads_per_worker=threads_per_worker,
            memory_limit=memory_limit,
            # serializers=['dask'], 
            # deserializers=['dask'],
            **kwargs
            )

    client = Client(cluster)
    return(client)

def initialize_hpc_dask_client(
        max_nr_of_processes=6,
        cpu_or_gpu="gpu",
        cores_per_process=1,
        memory_per_process="50GB",
        max_time_per_process="02:00:00",
        process_death_timeout=1000,
        gpu_name = "quadro_rtx_6000",
        **kwargs
    ):
    """
    processes: Whether to use processes (True) or threads (False)
    n_workers: Number of tasks to run in parallel
    memory_limit: Memory limit per worker (
        - if float provided --> percentage of memory per worker
        - if string ("1GiB") --> That amount of memory per worker
    threads_per_worker = Number of threads per worker
    """
    
    if cpu_or_gpu == "gpu":
        cluster = SLURMCluster(
            queue=cpu_or_gpu, 
            cores=cores_per_process, 
            memory=memory_per_process,
            walltime=max_time_per_process,
            death_timeout=process_death_timeout,
            job_extra_directives=[f'--gpus-per-node={gpu_name}:1'],
        )
    else:
        cluster = SLURMCluster(
            queue=cpu_or_gpu, 
            cores=cores_per_process, 
            memory=memory_per_process,
            walltime=max_time_per_process,
            death_timeout=process_death_timeout,
        )
    cluster.adapt(maximum_jobs=max_nr_of_processes)
    client = Client(cluster)
    return(client)

#######################################################
################## General Functions ##################
#######################################################
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
    """
    Prints:
    - Current memory uasge
    - Max memory used by any code run before this command
    - Reset the memory usage so next time command is run it traces only over code run after the previous
    """
    current_mem, max_mem = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    current_mem = convert_size(current_mem)
    max_mem = convert_size(max_mem)
    print(f"Current Memory used: {current_mem}\nMax Used Memory: {max_mem}")