#!/usr/bin/env python

"""Block operations.

https://haesleinhuepf.github.io/BioImageAnalysisNotebooks/32_tiled_image_processing/tiled_area_mapping.html

"""

import os
import sys
import argparse
import logging
import shutil
import multiprocessing

import math
import numpy as np
from itertools import product
from copy import deepcopy
from pathlib import Path
import json 
from skimage.measure import label

sys.path.append('/app/scripts/')
from image_handling import get_image,save_image,view_napari
from skimage.segmentation import relabel_sequential


def segment(image):
    mask = image > 0
    segments = label(mask)
    return(segments)

class Zipp3r(object):
    def __init__(self, image_path, output_path):
        
        ### Create a way to start from 3 options:
        ### 1. From an image_path
        ### 2. From a folder with images and a BlockInfo.json
        ### 3. From a Excel with the images and their respective positions
        self.image_path = Path(image_path)
        self.image_folder = Path(output_path)
        self.image_name = self.image_path.stem
        self.image = get_image(self.image_path)
        self.ext = self.image_path.suffix
    
    def segment_image(
        self, 
        seg_function, 
        out_folder=None
        ):
        if out_folder is None:
            segfolder = Path(image_folder, "segments")
        else:
            segfolder = out_folder
        if not segfolder.exists():
                segfolder.mkdir()
                
        seginfo_out = Path(segfolder, "BlockInfo.json")
        
        for block in blocks:
            img=get_image(block["BlockPath"])
            block["SegmentedBlockName"] = f"{Path(block['BlockName']).stem}_segments.tiff"
            block["SegmentedBlockPath"] = str(Path(segfolder,  block["SegmentedBlockName"]))
            seg_img = seg_function(img)
            # max_segment = np.max(seg_img)
            nr_segments = len(np.unique(seg_img[seg_img!=0]))
            # block["max_segment_id"]=str(max_segment)
            block["nr_segments"]=str(nr_segments)
            save_image(seg_img, block["SegmentedBlockPath"])

        max_blocks_segment_id = relabel_unique_segments_all_blocks(blocks)
        max_segment_id = max_blocks_segment_id
        with open(seginfo_out, 'w') as f:
            json.dump(blocks, f, indent=4)
            
    def set_zip_blocks():
        ### Set zipblock combination
        ### Per dimension there will be two sets, go over final grid with stride 2 from index 0 and index 1
        ### Resegment the border/seam of these two blocks, then recalculate the border segments
        
        lines=None
        quads=None
        octs=None
        
        #Lines
        lines = {idx: {"linetype1":[], "linetype2":[]} for idx, _ in enumerate(nr_blocks)}
        shaped_block_indices = np.arange(np.prod(nr_blocks)).reshape(nr_blocks)
        for idx, dim_nr in enumerate(nr_blocks):
            patch_size = int(np.prod(nr_blocks[idx+1:]))
            line1 = []
            line2 = []
            # shaped_block_indices = np.arange(24).reshape(2,3,4)
            if dim_nr > 1:
                # Slice out all indices for block1 of the pair
                # If number of blocks is uneven, dont take the last row of that dimension
                # as block1, as there is no corresponding pair
                slices_line1 = create_slice_object(
                    ndim=len(nr_blocks), 
                    axis=idx, 
                    start=None, 
                    end=dim_nr-dim_nr%2,
                    step=2
                    )
                line1_start_idc = shaped_block_indices[slices_line1].flatten().tolist()
                line1_pairs = [[blocks[start].copy(), blocks[start+patch_size].copy()] for start in line1_start_idc]

                slices_line2 = create_slice_object(
                    ndim=len(nr_blocks), 
                    axis=idx, 
                    start=1, 
                    end=dim_nr-dim_nr%2-1,
                    step=2
                    )
                line2_start_idc = shaped_block_indices[slices_line2].flatten().tolist()
                line2_pairs = [[blocks[start], blocks[start+patch_size]] for start in line2_start_idc]
                
                lines[idx]["linetype1"]=line1_pairs
                lines[idx]["linetype2"]=line2_pairs

        # Quads
        # Resegment the corner of 4(2x2) blocks between all dimensions
        blocked_dims = len([nr_blocks_dim for nr_blocks_dim in nr_blocks if nr_blocks_dim>=2])
        
        quad_dim_order = [[2,1], [1,0], [2,0]] #Corresponds to xy, yz, xz axis
        quadtype_offsets = [[0,0], [1,0], [0,1], [1,1]]
        
        if blocked_dims==1 or blocked_dims>3:
            pass
        elif blocked_dims==3:
            quads = {
                idx: {
                    "quadtype1":[], 
                    "quadtype2":[], 
                    "quadtype3":[], 
                    "quadtype4":[]
                    } for idx in range(3)
                }
        elif blocked_dims>1:
            quads = {
                0: {
                    "quadtype1":[], 
                    "quadtype2":[], 
                    "quadtype3":[], 
                    "quadtype4":[]
                    }
            }
            
        def get_quad_blocks(array, coord):
                slice_list = [[x,x+1] for x in coord]
                for idx in axis:
                    slice_list[idx][1]+=1
                slice_obj = create_slice_object(
                    slice_list=slice_list,
                    step=1
                )
                block_idc = list(array[slice_obj].flatten())
                return(block_idc)

        for idx, quadtypes in quads.items():
            for quadtype, quadname in enumerate(quadtypes.keys()):
                quad_order=[]
                axis = quad_dim_order[idx]
                dim_steps = [1]*len(nr_blocks)
                for d in dim_steps:
                    dim_steps[d]=2
                
                quad_coords = [list(range(0, dim_nr, 1)) for dim_nr in nr_blocks]
                for i, ax in enumerate(axis):
                    quad_offset = quadtype_offsets[quadtype][i]
                    quad_coords[ax] = list(range(quad_offset, nr_blocks[ax], 2))
                quad_coords = list(product(*quad_coords))
                
                for coord in quad_coords:
                    block_idc = get_quad_blocks(shaped_block_indices, coord)
                    quad_blocks=[blocks[idx] for idx in block_idc]
                    if len(quad_blocks)==4:
                        quads[idx][quadname].append(quad_blocks)
            
        # Octs
        # Resegment the corner of 8(2x2x2) blocks between
        # if len([nr_blocks_dim for nr_blocks_dim in nr_blocks if nr_blocks_dim>=2])>2:
        #     pass
        # quads = {
        #     idx: {
        #         "cornertype1":[], 
        #         "cornertype2":[], 
        #         "cornertype3":[], 
        #         "cornertype4":[]
        #         } for idx, _ in enumerate(nr_blocks)
        #     }
        # zip_order = []
               
        
    def resegment_all_lines(lines):
        ### Calculate the zip of the lines between two blocks and return the line image
        if out_folder is None:
            zipfolder = Path(image_folder, "zipping")
        else:
            zipfolder = out_folder
        if not zipfolder.exists():
            zipfolder.mkdir()
        
        zipped_intermediate_folder=Path(zipfolder, "zipped_intermediates")
        if not zipped_intermediate_folder.exists():
            zipped_intermediate_folder.mkdir()
        # Loop through dimension in the image
        for dim in lines.keys():
            print(f"Dim: {dim}")
            # Loop through the linetypes in the image (1: 1+2, 3+4 and 2: 2+3, 4+5 etc.)
            for linetype in lines[dim].keys():
                lines_info=[]
                # Create subzipfolder for that dimension and linetype
                subzipfolder = Path(zipfolder, f"zipping_lines_dim{dim}_{linetype}")
                if not subzipfolder.exists():
                    subzipfolder.mkdir()
                print(f"Linetype: {linetype}")
                # Go through each pair for this linetype
                ziplist=[]
                for line in lines[dim][linetype]:
                    
                    block1_info = line[0]
                    block2_info = line[1]
                    
                    # If there has already been a zipping performed by earlier lines/quads
                    # It uses this immediate files, otherwise it will use the original segmented blocks
                    block1_intermediate_path = Path(zipped_intermediate_folder, block1_info["SegmentedBlockName"])
                    if block1_intermediate_path.exists():
                        block1_info["SegmentedBlockPath"] = str(block1_intermediate_path)
                    block2_intermediate_path = Path(zipped_intermediate_folder, block2_info["SegmentedBlockName"])
                    if block2_intermediate_path.exists():
                        block2_info["SegmentedBlockPath"] = str(block2_intermediate_path)
                    
                    # Resegment the seam of these two blocks and return this seam as an image
                    print(block1_info["BlockID"],block2_info["BlockID"])
                    block1_removed_seg, block2_removed_seg, resegmented_line, line_info = resegment_line(
                        block1_info, 
                        block2_info, 
                        dim=dim,
                        outfolder=Path(zipfolder, subzipfolder)
                        )

                    save_image(block1_removed_seg, path=block1_intermediate_path)
                    save_image(block2_removed_seg, path=block2_intermediate_path)
                    line_info["block1"]=str(block1_intermediate_path)
                    line_info["block2"]=str(block2_intermediate_path)
                    
                    line_name = f"zipping_dim{dim}_{linetype}_{block1_info['BlockID']}_{block2_info['BlockID']}"+ext
                    line_outpath = str(Path(subzipfolder, line_name))
                    if resegmented_line is not None:
                        line_info["line"]=line_outpath
                        line_info["nr_segments"]=len(np.unique(resegmented_line[resegmented_line!=0]))
                        save_image(resegmented_line, path=line_outpath)
                        ziplist+=[line_outpath]
                    else:
                        line_info["nr_segments"]=0
                    lines_info.append(line_info)
                
                # Output the zipinfo to a .json file
                with open(Path(subzipfolder, "Zip_info.json"), 'w') as f:
                    json.dump(lines_info, f, indent=4)

                # If any pair needs zipping, relabel all lines for unique segments 
                # by taking the max segment id of the blocks and then continueing from there
                # And perform the zipping of the two blocks
                # This removes the border segments and places the seam segments in the original
                # 2 blocks and saves those partially zipped blocks
                
                linelist = [{"nr_segments":line["nr_segments"],"img":line["line"]} for line in lines_info if line["line"] is not None]
                # linelist = [Path(subzipfolder, line) for line in os.listdir(subzipfolder) if ".tiff" in line]
                if len(linelist) > 0:
                    max_segment_id = relabel_unique_segments_all_zipblocks(linelist, max_segment_id)
                    for zip_info in lines_info:
                        block1_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block1']).name}")
                        block2_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block2']).name}")
                        # block1_zipped_path = Path(subzipfolder, f"{Path(zip_info['block1']).name}")
                        # block2_zipped_path = Path(subzipfolder, f"{Path(zip_info['block2']).name}")
                        if line is not None:
                            block1_zipped, block2_zipped = zip_line(zip_info) 
                            save_image(block1_zipped, path=block1_zipped_path)
                            save_image(block2_zipped, path=block2_zipped_path)
                        else:
                            shutil.copyfile(zip_info['block1'], block1_zipped_path)
                            shutil.copyfile(zip_info['block2'], block2_zipped_path)

    def resegment_all_quads(quads):
        ### Calculate the zip of the lines between two blocks and return the line image
        if out_folder is None:
            zipfolder = Path(image_folder, "zipping")
        else:
            zipfolder = out_folder
        if not zipfolder.exists():
            zipfolder.mkdir()
        
        zipped_intermediate_folder=Path(zipfolder, "zipped_intermediates")
        if not zipped_intermediate_folder.exists():
            zipped_intermediate_folder.mkdir()
        # Loop through dimension in the image
        for dim in quads.keys():
            dim_name=''.join(str(x) for x in quad_dim_order[dim])
            print(f"Quad dimensions: {dim_name}")
            # Loop through the linetypes in the image (1: 1+2, 3+4 and 2: 2+3, 4+5 etc.)
            for quad_idx, quadtype in enumerate(quads[dim].keys()):
                quads_info=[]
                # Create subzipfolder for that dimension and linetype
                
                subzipfolder = Path(zipfolder, f"zipping_quads_dim{dim_name}_{quadtype}")
                if not subzipfolder.exists():
                    subzipfolder.mkdir()
                print(f"Quadtype: {quadtype}")
                # Go through each pair for this linetype
                ziplist=[]
                for quad in quads[dim][quadtype]:
                    block1_info = quad[0]
                    block2_info = quad[1]
                    block3_info = quad[2]
                    block4_info = quad[3]
                    
                    # If there has already been a zipping performed by earlier lines/quads
                    # It uses this immediate files, otherwise it will use the original segmented blocks
                    block1_intermediate_path = Path(zipped_intermediate_folder, block1_info["SegmentedBlockName"])
                    if block1_intermediate_path.exists():
                        block1_info["SegmentedBlockPath"] = str(block1_intermediate_path)
                    block2_intermediate_path = Path(zipped_intermediate_folder, block2_info["SegmentedBlockName"])
                    if block2_intermediate_path.exists():
                        block2_info["SegmentedBlockPath"] = str(block2_intermediate_path)
                    block3_intermediate_path = Path(zipped_intermediate_folder, block3_info["SegmentedBlockName"])
                    if block3_intermediate_path.exists():
                        block3_info["SegmentedBlockPath"] = str(block3_intermediate_path)
                    block4_intermediate_path = Path(zipped_intermediate_folder, block4_info["SegmentedBlockName"])
                    if block4_intermediate_path.exists():
                        block4_info["SegmentedBlockPath"] = str(block4_intermediate_path)
                        
                    # Resegment the seam of these two blocks and return this seam as an image
                    print(block1_info["BlockID"],block2_info["BlockID"],block3_info["BlockID"],block4_info["BlockID"])
                    (   block1_removed_seg, 
                        block2_removed_seg, 
                        block3_removed_seg, 
                        block4_removed_seg, 
                        resegmented_quad, 
                        quad_info) = resegment_quad(
                        block1_info, 
                        block2_info, 
                        block3_info, 
                        block4_info, 
                        dims=quad_dim_order[dim],
                        outfolder=Path(zipfolder, subzipfolder)
                        )

                    save_image(block1_removed_seg, path=block1_intermediate_path)
                    save_image(block2_removed_seg, path=block2_intermediate_path)
                    save_image(block3_removed_seg, path=block3_intermediate_path)
                    save_image(block4_removed_seg, path=block4_intermediate_path)
                    
                    quad_info["block1"]=str(block1_intermediate_path)
                    quad_info["block2"]=str(block2_intermediate_path)
                    quad_info["block3"]=str(block3_intermediate_path)
                    quad_info["block4"]=str(block4_intermediate_path)
                    
                    quad_name = f"zipping_dim{dim}_{quadtype}_{block1_info['BlockID']}_{block2_info['BlockID']}_{block3_info['BlockID']}_{block4_info['BlockID']}"+ext
                    quad_outpath = str(Path(subzipfolder, quad_name))
                    if resegmented_quad is not None:
                        quad_info["quad"]=quad_outpath
                        quad_info["nr_segments"]=len(np.unique(resegmented_quad[resegmented_quad!=0]))
                        save_image(resegmented_quad, path=quad_outpath)
                        ziplist+=[quad_outpath]
                    else:
                        quad_info["nr_segments"]=0
                    quads_info.append(quad_info)
                
                # Output the zipinfo to a .json file
                with open(Path(subzipfolder, "Zip_info.json"), 'w') as f:
                    json.dump(quads_info, f, indent=4)

                # If any pair needs zipping, relabel all lines for unique segments 
                # by taking the max segment id of the blocks and then continueing from there
                # And perform the zipping of the two blocks
                # This removes the border segments and places the seam segments in the original
                # 2 blocks and saves those partially zipped blocks
                quadlist = [{"nr_segments":quad["nr_segments"],"img":quad["quad"]} for quad in quads_info if quad["quad"] is not None]
                # linelist = [Path(subzipfolder, line) for line in os.listdir(subzipfolder) if ".tiff" in line]
                if len(quadlist) > 0:
                    max_segment_id = relabel_unique_segments_all_zipblocks(quadlist, max_segment_id)
                    for zip_info in quads_info:
                        block1_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block1']).name}")
                        block2_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block2']).name}")
                        block3_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block3']).name}")
                        block4_zipped_path = Path(zipped_intermediate_folder, f"{Path(zip_info['block4']).name}")
                        # block1_zipped_path = Path(subzipfolder, f"{Path(zip_info['block1']).name}")
                        # block2_zipped_path = Path(subzipfolder, f"{Path(zip_info['block2']).name}")
                        if quad is not None:
                            block1_zipped, block2_zipped, block3_zipped, block4_zipped = zip_quad(zip_info) 
                            save_image(block1_zipped, path=block1_zipped_path)
                            save_image(block2_zipped, path=block2_zipped_path)
                            save_image(block3_zipped, path=block3_zipped_path)
                            save_image(block4_zipped, path=block4_zipped_path)
                        else:
                            shutil.copyfile(zip_info['block1'], block1_zipped_path)
                            shutil.copyfile(zip_info['block2'], block2_zipped_path)
                            shutil.copyfile(zip_info['block3'], block3_zipped_path)
                            shutil.copyfile(zip_info['block4'], block4_zipped_path)
                        
        # relabel_unique_segments_from_file(
        #     sorted([Path(zipfolder, line) for line in os.listdir(zipfolder) if ".tiff" in line])
        #     )
            

    def relabel_unique_segments_from_file(
        image_path_list
        ):
        segment_max = 0
        for image_path in image_path_list:
            image = get_image(image_path).astype(np.int64)
            image = relabel_sequential(image)[0]
            image[image!=0]+=segment_max
            segment_max = int(np.max(image))
            save_image(image, path=image_path)
                   
    def resegment_line(block1_info, block2_info, dim, outfolder)    :
        ### Calculate which segment overlap the border of both blocks of the seam pair
        ### Calculate the extent of the segments into both blocks
        ### Create a seam cutout with margin that will be resegmented
        
        block1_img = get_image(block1_info["SegmentedBlockPath"])
        block2_img = get_image(block2_info["SegmentedBlockPath"])
        
        block1_list = block1_info["relative_block"].copy()

        # Get only the part of the block where segments touch that border of the block
        block1_list[dim] = [block1_list[dim][1], block1_info["block_shape"][dim]]
        # block1_list[dim] = [block1_list[dim][1], block1_info["block_with_margins"][dim][1]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block1_slices = create_slice_object(block1_list)
        block1_segment_ids = [int(x) for x in np.unique(block1_img[block1_slices][block1_img[block1_slices]!=0])]
        
        block2_list = block2_info["relative_block"].copy()
        # Get only the part of the block where segments touch that border of the block
        block2_list[dim] = [0, block2_list[dim][0]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block2_slices = create_slice_object(block2_list)
        block2_segment_ids = [int(x) for x in np.unique(block2_img[block2_slices][block2_img[block2_slices]!=0])]
                
        ### If there are no border segments, return the original segment images
        if len(block1_segment_ids)==0 and len(block2_segment_ids)==0:
            zip_info={
            "block1": block1_info["SegmentedBlockPath"],
            "block2": block2_info["SegmentedBlockPath"],
            "line": None,
            "block1_margins": None,
            "block2_margins": None,
            "block1_bordersegments":[],
            "block2_bordersegments": [],
            "line_blocksizes":[]
        } 
            return(block1_img, block2_img, None, zip_info)
        else:
            if len(block1_segment_ids)>0:
                block1_segments = np.isin(block1_img, block1_segment_ids)
                block1_furthest_segment_index = np.min(np.nonzero(np.any(
                    block1_segments, axis=tuple(i for i in range(block1_segments.ndim) if i != dim)
                    )))
                block1_img[block1_segments]=0
            else:
                block1_furthest_segment_index = 0
                
            linepart1_with_margin = [
                block1_furthest_segment_index - margins[dim], 
                block1_list[dim][0]
                ]

            line1_block_slice_margin = create_slice_object(
                ndim=block1_img.ndim, 
                axis=dim, 
                start = block1_furthest_segment_index-margins[dim],
                end=block1_list[dim][0]
                )
            
        
            if len(block2_segment_ids)>0:
                block2_segments = np.isin(block2_img, block2_segment_ids)
                block2_furthest_segment_index=np.max(np.nonzero(np.any(
                    block2_segments, axis=tuple(i for i in range(block2_segments.ndim) if i != dim)
                    )))
                block2_img[block2_segments]=0
            else:
                block2_furthest_segment_index=0
            
            linepart2_with_margin = [
                block2_list[dim][1], 
                block2_furthest_segment_index+margins[dim]
                ]
            
            line2_block_slice_margin = create_slice_object(
                ndim=block2_img.ndim, 
                axis=dim, 
                start = block2_list[dim][1],
                end=block2_furthest_segment_index+margins[dim]
                )

        block1_raw_img = get_image(block1_info["BlockPath"])
        block2_raw_img = get_image(block2_info["BlockPath"])
        line = np.concatenate([block1_raw_img[line1_block_slice_margin], block2_raw_img[line2_block_slice_margin]], axis=dim)
        line = segment(line)
        
        zip_info={
            "dim": dim,
            "block1": block1_info["SegmentedBlockPath"],
            "block2": block2_info["SegmentedBlockPath"],
            "line": None,
            "margin": margins[dim],
            "block1_margins": [int(block1_furthest_segment_index-margins[dim]), int(block1_list[dim][0]+margins[dim])],
            "block2_margins": [0, int(block2_furthest_segment_index+margins[dim])],
            # "block1_margins": [int(block1_furthest_segment_index-margins[dim]), int(block1_list[dim][0])],
            # "block2_margins": [int(block2_list[dim][1]), int(block2_furthest_segment_index+margins[dim])],
            "block1_bordersegments":block1_segment_ids,
            "block2_bordersegments": block2_segment_ids,
            "line_blocksizes": [
                int(linepart1_with_margin[1]-linepart1_with_margin[0]),
                int(linepart2_with_margin[1]-linepart2_with_margin[0])
            ],          
        }
        
        return(block1_img, block2_img, line, zip_info)
    
    def resegment_quad(block1_info, block2_info, block3_info, block4_info, dims, outfolder)    :
        ### Calculate which segment overlap the border of both blocks of the seam pair
        ### Calculate the extent of the segments into both blocks
        ### Create a seam cutout with margin that will be resegmented
        
        block1_img = get_image(block1_info["SegmentedBlockPath"])
        block2_img = get_image(block2_info["SegmentedBlockPath"])
        block3_img = get_image(block3_info["SegmentedBlockPath"])
        block4_img = get_image(block4_info["SegmentedBlockPath"])
        
        block1_list = block1_info["relative_block"].copy()
        # Get only the part of the block where segments touch that border of the block
        block1_list[dims[0]] = [block1_list[dims[0]][1], block1_info["block_shape"][dims[0]]]
        block1_list[dims[1]] = [block1_list[dims[1]][1], block1_info["block_shape"][dims[1]]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block1_slices = create_slice_object(block1_list)
        block1_segment_ids = [int(x) for x in np.unique(block1_img[block1_slices][block1_img[block1_slices]!=0])]
        
        block2_list = block2_info["relative_block"].copy()
        # Get only the part of the block where segments touch that border of the block
        block2_list[dims[0]] = [0, block2_list[dims[0]][0]]
        block2_list[dims[1]] = [block2_list[dims[1]][1], block2_info["block_shape"][dims[1]]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block2_slices = create_slice_object(slice_list=block2_list)
        block2_segment_ids = [int(x) for x in np.unique(block2_img[block2_slices][block2_img[block2_slices]!=0])]
        
        block3_list = block3_info["relative_block"].copy()
        # Get only the part of the block where segments touch that border of the block
        block3_list[dims[0]] = [block3_list[dims[0]][1], block3_info["block_shape"][dims[0]]]
        block3_list[dims[1]] = [0, block3_list[dims[1]][0]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block3_slices = create_slice_object(block3_list)
        block3_segment_ids = [int(x) for x in np.unique(block3_img[block3_slices][block3_img[block3_slices]!=0])]
        
        block4_list = block4_info["relative_block"].copy()
        # Get only the part of the block where segments touch that border of the block
        block4_list[dims[0]] = [0, block4_list[dims[0]][0]]
        block4_list[dims[1]] = [0, block4_list[dims[1]][0]]
        # Slice this part and get all unique segment IDs that touch that specific block border
        block4_slices = create_slice_object(block4_list)
        block4_segment_ids = [int(x) for x in np.unique(block4_img[block4_slices][block4_img[block4_slices]!=0])]
        
                
        ### If there are no border segments, return the original segment images
        if len(block1_segment_ids)==0 and len(block2_segment_ids)==0 and len(block3_segment_ids)==0 and len(block4_segment_ids)==0:
            zip_info={
            "block1": block1_info["SegmentedBlockPath"],
            "block2": block2_info["SegmentedBlockPath"],
            "block3": block3_info["SegmentedBlockPath"],
            "block4": block4_info["SegmentedBlockPath"],
            "quad": None,
            "block1_margins": None,
            "block2_margins": None,
            "block3_margins": None,
            "block4_margins": None,
            "block1_bordersegments":[],
            "block2_bordersegments": [],
            "block3_bordersegments":[],
            "block4_bordersegments": [],
            "quad_blocksizes":[]
            } 
            return(block1_img, block2_img, block3_img, block4_img, None, zip_info)
        else:
            if len(block1_segment_ids)>0:
                block1_segments = np.isin(block1_img, block1_segment_ids)
                block1_furthest_segment_idc = [
                    np.min(np.nonzero(np.any(
                        block1_segments, axis=tuple(i for i in range(block1_segments.ndim) if i != dims[0])
                    ))),
                    np.min(np.nonzero(np.any(
                        block1_segments, axis=tuple(i for i in range(block1_segments.ndim) if i != dims[1])
                    )))
                ]
                block1_img[block1_segments]=0
            else:
                block1_furthest_segment_idc = [0,0]
                
            quadpart1_with_margin = [
                    [
                        int(block1_furthest_segment_idc[0] - margins[dims[0]]), 
                        int(block1_list[dims[0]][0])   
                    ],
                    [
                        int(block1_furthest_segment_idc[1] - margins[dims[1]]), 
                        int(block1_list[dims[1]][0])   
                    ]
                ]
                    
            if len(block2_segment_ids)>0:
                block2_segments = np.isin(block2_img, block2_segment_ids)
                block2_furthest_segment_idc = [
                    np.max(np.nonzero(np.any(
                        block2_segments, axis=tuple(i for i in range(block2_segments.ndim) if i != dims[0])
                    ))),
                    np.min(np.nonzero(np.any(
                        block2_segments, axis=tuple(i for i in range(block2_segments.ndim) if i != dims[1])
                    )))
                ]
                block2_img[block2_segments]=0
            else:
                block2_furthest_segment_idc = [0,0]
                
            quadpart2_with_margin = [
                    [
                        int(block2_list[dims[0]][1]), 
                        int(block2_furthest_segment_idc[0]+margins[dims[0]])
                    ],
                    [
                        int(block2_furthest_segment_idc[1] - margins[dims[1]]), 
                        int(block2_list[dims[1]][0])   
                    ]
                ]
            
            if len(block3_segment_ids)>0:
                block3_segments = np.isin(block3_img, block3_segment_ids)
                block3_furthest_segment_idc = [
                    np.min(np.nonzero(np.any(
                        block3_segments, axis=tuple(i for i in range(block3_segments.ndim) if i != dims[0])
                    ))),
                    np.max(np.nonzero(np.any(
                        block3_segments, axis=tuple(i for i in range(block3_segments.ndim) if i != dims[1])
                    )))
                ]
                block3_img[block3_segments]=0
            else:
                block3_furthest_segment_idc = [0,0]
                
            quadpart3_with_margin = [
                    [
                        int(block3_furthest_segment_idc[0] - margins[dims[0]]), 
                        int(block3_list[dims[0]][0])   
                    ],
                    [
                        int(block3_list[dims[1]][1]), 
                        int(block3_furthest_segment_idc[1]+margins[dims[1]])
                    ]
                ]            
            
            if len(block4_segment_ids)>0:
                block4_segments = np.isin(block4_img, block4_segment_ids)
                block4_furthest_segment_idc = [
                    np.max(np.nonzero(np.any(
                        block4_segments, axis=tuple(i for i in range(block4_segments.ndim) if i != dims[0])
                    ))),
                    np.max(np.nonzero(np.any(
                        block4_segments, axis=tuple(i for i in range(block4_segments.ndim) if i != dims[1])
                    )))
                ]
                block4_img[block4_segments]=0
            else:
                block4_furthest_segment_idc = [0,0]
                
            quadpart4_with_margin = [
                    [
                        int(block4_list[dims[0]][1]), 
                        int(block4_furthest_segment_idc[0]+margins[dims[0]])
                    ],
                    [
                        int(block4_list[dims[1]][1]), 
                        int(block4_furthest_segment_idc[1]+margins[dims[1]])
                    ]
                ]
            
            # Because it is a quad, take the maximum value if segments extend further in adjacent blocks
            quad_1_3_min = min(quadpart1_with_margin[0][0], quadpart3_with_margin[0][0])
            quadpart1_with_margin[0][0] = quad_1_3_min
            quadpart3_with_margin[0][0] = quad_1_3_min

            quad_1_2_min = min(quadpart1_with_margin[1][0], quadpart2_with_margin[1][0])
            quadpart1_with_margin[1][0] = quad_1_2_min
            quadpart2_with_margin[1][0] = quad_1_2_min
            
            quad_2_4_max = max(quadpart2_with_margin[0][1], quadpart4_with_margin[0][1])
            quadpart2_with_margin[0][1] = quad_2_4_max
            quadpart4_with_margin[0][1] = quad_2_4_max
            
            quad_3_4_max = max(quadpart3_with_margin[1][1], quadpart4_with_margin[1][1])
            quadpart3_with_margin[1][1] = quad_3_4_max
            quadpart4_with_margin[1][1] = quad_3_4_max
            
            # Set block slices based on the segment extensions
            quad1_block_slice_margins = [None] * block1_img.ndim
            quad1_block_slice_margins[dims[0]]=quadpart1_with_margin[0]
            quad1_block_slice_margins[dims[1]]=quadpart1_with_margin[1]
            
            quad2_block_slice_margins = [None] * block2_img.ndim
            quad2_block_slice_margins[dims[0]]=quadpart2_with_margin[0]
            quad2_block_slice_margins[dims[1]]=quadpart2_with_margin[1]
            
            quad3_block_slice_margins = [None] * block3_img.ndim
            quad3_block_slice_margins[dims[0]]=quadpart3_with_margin[0]
            quad3_block_slice_margins[dims[1]]=quadpart3_with_margin[1]
            
            quad4_block_slice_margins = [None] * block4_img.ndim
            quad4_block_slice_margins[dims[0]]=quadpart4_with_margin[0]
            quad4_block_slice_margins[dims[1]]=quadpart4_with_margin[1]
            
            slice_quad1_block_slice_margins = create_slice_object(slice_list=quad1_block_slice_margins)
            slice_quad2_block_slice_margins = create_slice_object(slice_list=quad2_block_slice_margins)
            slice_quad3_block_slice_margins = create_slice_object(slice_list=quad3_block_slice_margins)
            slice_quad4_block_slice_margins = create_slice_object(slice_list=quad4_block_slice_margins)
        
        block1_raw_img = get_image(block1_info["BlockPath"])
        block2_raw_img = get_image(block2_info["BlockPath"])
        block3_raw_img = get_image(block3_info["BlockPath"])
        block4_raw_img = get_image(block4_info["BlockPath"])
        
        def get_slice_size(slice_list):
            slice_sizes=[]
            for dim in slice_list:
                if dim is None:
                    slice_sizes.append(None)
                else:
                    dimsize = dim[1]-dim[0]
                    slice_sizes.append([0,int(dimsize)])
            return(slice_sizes)
        
        quad_blocksizes= [
                # Position of part1 quad end to size of part2 of quad
                get_slice_size(quad1_block_slice_margins),
                get_slice_size(quad2_block_slice_margins),
                get_slice_size(quad3_block_slice_margins),
                get_slice_size(quad4_block_slice_margins)
            ]

        quad_blocksizes[1][dims[0]]=[x+quad_blocksizes[0][dims[0]][1] for idx, x in enumerate(quad_blocksizes[1][dims[0]])]
        quad_blocksizes[2][dims[1]]=[x+quad_blocksizes[0][dims[1]][1] for idx, x in enumerate(quad_blocksizes[2][dims[1]])]
        quad_blocksizes[3][dims[0]]=[x+quad_blocksizes[0][dims[0]][1] for idx, x in enumerate(quad_blocksizes[3][dims[0]])]
        quad_blocksizes[3][dims[1]]=[x+quad_blocksizes[0][dims[1]][1] for idx, x in enumerate(quad_blocksizes[3][dims[1]])]
            
        quadpart1= np.concatenate([block1_raw_img[slice_quad1_block_slice_margins], block2_raw_img[slice_quad2_block_slice_margins]], axis=dims[0])
        quadpart2= np.concatenate([block3_raw_img[slice_quad3_block_slice_margins], block4_raw_img[slice_quad4_block_slice_margins]], axis=dims[0])
        quad = np.concatenate([quadpart1, quadpart2], axis=dims[1])
        quad = segment(quad)
        
        zip_info={
            "dim": dim,
            "block1": block1_info["SegmentedBlockPath"],
            "block2": block2_info["SegmentedBlockPath"],
            "block3": block3_info["SegmentedBlockPath"],
            "block4": block4_info["SegmentedBlockPath"],
            "quad": None,
            "margin": margins[dim],
            "block1_margins": quad1_block_slice_margins,
            "block2_margins": quad2_block_slice_margins,
            "block3_margins": quad3_block_slice_margins,
            "block4_margins": quad4_block_slice_margins,
            # "block1_margins": [int(block1_furthest_segment_index-margins[dim]), int(block1_list[dim][0])],
            # "block2_margins": [int(block2_list[dim][1]), int(block2_furthest_segment_index+margins[dim])],
            "block1_bordersegments":block1_segment_ids,
            "block2_bordersegments": block2_segment_ids,
            "block3_bordersegments": block3_segment_ids,
            "block4_bordersegments": block4_segment_ids,
            "quad_blocksizes": quad_blocksizes,          
        }
        
        return(block1_img, block2_img, block3_img, block4_img, quad, zip_info)
        
    def zip_line(zip_info):
        
        block1_img=get_image(zip_info["block1"])
        block2_img=get_image(zip_info["block2"])
        line_img=get_image(zip_info["line"])
        dim = zip_info["dim"]
        line_block1_size = zip_info["line_blocksizes"][0]
        line_block2_size = zip_info["line_blocksizes"][1]
        
        block1_margins = create_slice_object(
                ndim=block1_img.ndim, 
                axis=dim, 
                start = zip_info["block1_margins"][0],
                end= zip_info["block1_margins"][1]
                )

        block2_margins = create_slice_object(
                ndim=block1_img.ndim, 
                axis=dim, 
                start = zip_info["block2_margins"][0],
                end= zip_info["block2_margins"][1]
                )
        
        linepart1_slice = create_slice_object(ndim=line_img.ndim, axis = dim, end = line_block1_size+zip_info["margin"])
        block1_img[block1_margins] = np.where(
            block1_img[block1_margins]==0, 
            line_img[linepart1_slice],
            block1_img[block1_margins]
            )
        
        linepart2_slice = create_slice_object(ndim=line_img.ndim, axis = dim, start = -(line_block2_size+zip_info["margin"])) 
        block2_img[block2_margins] = np.where(
            block2_img[block2_margins]==0, 
            line_img[linepart2_slice],
            block2_img[block2_margins]
            )
        return(block1_img, block2_img)
    
        ### TEST ZIPPING TODO CONTINUE HERE!!! NOT EXACTLYBUT
        # block1_rel = create_slice_object(slice_list=block1_info["relative_block"])
        # block2_rel = create_slice_object(slice_list=block2_info["relative_block"])
        # zip_block = np.concatenate([block1_img[block1_rel], block2_img[block2_rel]], axis=dim)
    
    def zip_quad(zip_info):
        
        block1_img=get_image(zip_info["block1"])
        block2_img=get_image(zip_info["block2"])
        block3_img=get_image(zip_info["block3"])
        block4_img=get_image(zip_info["block4"])
        quad_img=get_image(zip_info["quad"])
        dim = zip_info["dim"]
        
        quad_block1_size = zip_info["quad_blocksizes"][0]
        quad_block2_size = zip_info["quad_blocksizes"][1]
        quad_block3_size = zip_info["quad_blocksizes"][2]
        quad_block4_size = zip_info["quad_blocksizes"][3]
        
        block1_margins = create_slice_object(
                slice_list=zip_info["block1_margins"]
                )

        block2_margins = create_slice_object(
                slice_list=zip_info["block2_margins"]
                )

        block3_margins = create_slice_object(
                slice_list=zip_info["block3_margins"]
                )
        
        block4_margins = create_slice_object(
                slice_list=zip_info["block4_margins"]
                )
        
        quadpart1_slice = create_slice_object(slice_list=quad_block1_size)
        block1_img[block1_margins] = np.where(
            block1_img[block1_margins]==0, 
            quad_img[quadpart1_slice],
            block1_img[block1_margins]
            )
        
        quadpart2_slice = create_slice_object(slice_list=quad_block2_size) 
        block2_img[block2_margins] = np.where(
            block2_img[block2_margins]==0, 
            quad_img[quadpart2_slice],
            block2_img[block2_margins]
            )

        quadpart3_slice = create_slice_object(slice_list=quad_block3_size)
        block3_img[block3_margins] = np.where(
            block3_img[block3_margins]==0, 
            quad_img[quadpart3_slice],
            block3_img[block3_margins]
            )
        
        quadpart4_slice = create_slice_object(slice_list=quad_block4_size)
        block4_img[block4_margins] = np.where(
            block4_img[block4_margins]==0, 
            quad_img[quadpart4_slice],
            block4_img[block4_margins]
            )
        
        return(block1_img, block2_img, block3_img, block4_img)  
    
    def relabel_unique_segments(
        image_list
        ):
        segment_max = 0
        for idx, image in enumerate(image_list):
            image = relabel_sequential(image)[0]
            image[image!=0]+=segment_max
            segment_max = int(np.max(image))
            image_list[idx]=image
        return image_list
        
    def relabel_unique_segments_all_blocks(
            blocks
        ):
        
        def get_segment_start(blocks, block_idx):
            segment_start=0
            for block in blocks[:block_idx]:
                segment_start+=int(block["nr_segments"])
            return(segment_start)
        
        for idx, block in enumerate(blocks):
            segment_start=get_segment_start(blocks, idx)
            seg_img=get_image(block["SegmentedBlockPath"])
            seg_img = relabel_sequential(seg_img)[0]
            seg_img[seg_img!=0]+=segment_start
            save_image(seg_img, block["SegmentedBlockPath"])
            if idx == len(blocks)-1:
                max_blocks_segment_id = np.max(seg_img)
        return(max_blocks_segment_id)
        
    def relabel_unique_segments_all_zipblocks(
        linelist,
        max_blocks_segment_id,
        ):
        
        def get_segment_start(lines, line_idx):
            segment_start=0
            for line in lines[:line_idx]:
                segment_start+=int(line["nr_segments"])
            return(segment_start)
        
        for idx, line in enumerate(linelist):
            segment_start=get_segment_start(linelist, idx)
            segment_start+=max_blocks_segment_id
            print(segment_start)
            seg_img=get_image(line["img"])
            seg_img = relabel_sequential(seg_img)[0]
            seg_img[seg_img!=0]+=segment_start
            save_image(seg_img, line["img"])
            if idx == len(linelist)-1:
                max_zipping_segment_id = np.max(seg_img)
        return(max_zipping_segment_id)
      
    def split_image(self):
        blockfolder = Path(self.image_folder, "blocks")
        if not blockfolder.exists():
            blockfolder.mkdir(parents=True, exist_ok=True)

        blockinfo_out = Path(blockfolder, "BlockInfo.json")

        if not hasattr(self, 'blocks') or not self.blocks:
            raise ValueError("Blocks are not set. Please call set_block_slices first.")

        blocks = self.blocks  # Usa el atributo de la instancia

        with open(blockinfo_out, 'w') as f:
            json.dump(blocks, f, indent=4)

        for block in blocks:
            block_slice = self.create_slice_object(slice_list=block["block_with_margins"])
            block_img = self.image
            block_img = self.image[block_slice]
            save_image(block_img, path=block["BlockPath"])

    def create_slice_object(
        self,
        slice_list=None,
        ndim=None,
        axis=None,
        start=None,
        end=None,
        step=1
    ):
        if slice_list is not None:
            slices = [slice(dim_slice[0], dim_slice[1]) if dim_slice is not None else slice(None) for dim_slice in slice_list]
            slices = tuple(slices)
        else:
            slices = (slice(None),) * (axis % ndim) + (slice(start, end, step),)

        return slices
    
    def slice_axis(array, axis, start=None, end=None, step=1):
        return array[(slice(None),) * (axis % array.ndim) + (slice(start, end, step),)]
    
    def set_block_slices(
        self, 
        image_shape, 
        blocksize,
        margins
        ):
        ## If image has more dimensions than provided blocksize or margins 
        ## (e.g. [20,20,60,2000,2000] for blocksize [60, 1000, 1000])
        ## Add dimensions so that over that dimension only 1 block is created ([20,20,60,1000,1000])
        ## or a margin of 0 is added (e.g. [0,0,0,64,64] for margins [64,64])
        image_shape = list(image_shape)
        blocksize = list(image_shape[:len(image_shape)-len(blocksize)]) + blocksize
        margins = [0]*(len(image_shape)-len(margins))+ margins

        blockfolder = Path(self.image_folder, "blocks") 
        
        ## Set the number of blocks by dividing each dimension with the
        ## image size of that dimensions and rounding up
        nr_blocks = [math.ceil(img_size/dim_size) for img_size, dim_size in zip(image_shape, blocksize)]
        
        ## Create the empty list where each block dictionary will be added
        ## Initialize default dictionary for each block
        blocks = []
        setup_block_dict = {
            "BlockID": "",
            "BlockName": "",
            "BlockPath": "",
            # "Block": None,
            "slice_nr":[],
            "block_with_margins":[],
            "relative_block":[],
            # "slices": [],
            "block_shape" : [],
            "supplied_margin": margins,
            "supplied_blocksize": blocksize,  
            "nr_blocks": nr_blocks
            }
        
        
        ## Calculate all blocksize top-left corner positions
        ## Calculate a list of all the block IDs
        block_positions = []
        block_ids = []
        for dim, nr_blocks_dim in enumerate(nr_blocks):
            dim_slices=[[blocknr*blocksize[dim],blocknr*blocksize[dim]+blocksize[dim]] for blocknr in range(nr_blocks_dim)]
            dim_ids = [blocknr for blocknr in range(nr_blocks_dim)]
            block_positions.append(dim_slices)
            block_ids.append(dim_ids)
        block_positions = list(map(list, product(*block_positions)))
        block_ids = list(map(list, product(*block_ids)))
        
        ## Calculate the blocksizes with margins added, limit to actual image_shape 
        blocks_with_margins = [] 
        blockshapes = [] 
        relative_blocks = []
        for block_pos in block_positions:
            # Create the block with added margins (limit to borders of the original image)
            margin_block =[
                    [
                    max(0, pos[0]-margins[dim]),
                    min(image_shape[dim], pos[1]+margins[dim])
                    ] for dim,pos in enumerate(block_pos)
                ]
            blocks_with_margins.append(margin_block)
            # Add the relative positions within this block of the actual data without margins
            relative_blocks.append([
                    [
                        abs(dim_margin_block[0]-dim_block[0]), 
                        dim_margin_block[1]-dim_margin_block[0]-abs(dim_margin_block[1]-dim_block[1]), 
                    ] for dim_margin_block, dim_block in zip(margin_block, block_pos)
                ]
            )
            
            # Add the final shape of the block with margins
            blockshapes.append(
                [pos[1] - pos[0] for pos in margin_block]
            )
        
        ## Create slice objects out of blocks_with_margins
        # slices = []
        # for block_pos in blocks_with_margins:
        #     block_slices = [slice(dim_pos[0], dim_pos[1]) for dim_pos in block_pos]
        #     slices.append(block_slices)
        
        ## Calculate the max digits needed in the ID for each dimension for ID naming
        max_digits = [len(str(nr_blocks_dim)) for nr_blocks_dim in nr_blocks]
        
        ## Zip all block info and per block add the info to a dictionary
        block_info = zip(
            block_positions,
            blocks_with_margins,
            relative_blocks,
            block_ids,
            blockshapes
        )
        for block_pos, block_pos_margin, relative_block, block_id, blockshape in block_info:
            block_dict = deepcopy(setup_block_dict)
            block_dict["slice_nr"]=block_id
            block_id = "x".join([f"{i:0{digits}d}" for digits, i in zip(max_digits, block_id)])
            block_dict["BlockID"] = block_id
            block_dict["BlockName"] = f"{self.image_name}_block{block_id}{self.ext}"
            block_dict["BlockPath"] = str(Path(blockfolder, block_dict["BlockName"]))
            block_dict["block_positions"]=block_pos
            block_dict["block_with_margins"]=block_pos_margin
            block_dict["relative_block"]=relative_block
            block_dict["block_shape"]=blockshape
            blocks.append(block_dict)

        self.blocks = blocks

    # def get_border_segments():
    #     for block in blocks:
    #         seg_img=get_image(block["SegmentedBlockPath"])
            
    #         ### Set border segments ids and extent to None if there is not block at that border
    #         border_segment_ids=[[None,None] for dim in range(len(block["block_shape"]))]
    #         border_segment_extent = [[None,None] for dim in range(len(block["block_shape"]))]
    #         for dim in range(len(block["block_shape"])):
    #             if block["nr_blocks"][dim]>1:
    #                 ## Get border touching segments from the 0 (start) border
    #                 start_segment_ids=None
    #                 start_furthest_segment_index=None
                
    #                 ## Check if the image is not the border of the original image
    #                 if block["block_with_margins"][dim][0] != block["block_positions"][dim][0]:
    #                     start_list = block["relative_block"].copy()
    #                     # Get only the part of the block where segments touch that border of the block
    #                     start_list[dim] = [0, start_list[dim][0]]
    #                     # Slice this part and get all unique segment IDs that touch that specific block border
    #                     start_slices = create_slice_object(start_list)
    #                     start_segment_ids = list(np.unique(seg_img[start_slices][seg_img[start_slices]!=0]))     
                        
    #                     # If there are any segments touching the border, get the extend of the furthest
    #                     # Any of these segments protrude into the block from that border
    #                     if len(start_segment_ids)>0:
    #                         start_segments = np.isin(seg_img, start_segment_ids)
    #                         start_furthest_segment_index=[0,np.max(np.nonzero(np.any(start_segments, axis=tuple(i for i in range(start_segments.ndim) if i != dim))))]
 
    #                 ## Get border-touching segments from the max value for that dimension (end) border
    #                 end_segment_ids=None
    #                 end_furthest_segment_index=None
    #                 if block["block_with_margins"][dim][1] != block["block_positions"][dim][1]:
    #                     end_list = block["relative_block"].copy()
    #                     # Get only the part of the block where segments touch that border of the block
    #                     end_list[dim] = [end_list[dim][1], block["block_with_margins"][dim][1]]
    #                     # Slice this part and get all unique segment IDs that touch that specific block border
    #                     end_slices = create_slice_object(end_list)
    #                     end_segment_ids = list(np.unique(seg_img[end_slices][seg_img[end_slices]!=0]))

    #                     if len(end_segment_ids)>0:
    #                         end_segments = np.isin(seg_img, end_segment_ids)
    #                         end_furthest_segment_index = [np.min(np.nonzero(np.any(end_segments, axis=tuple(i for i in range(end_segments.ndim) if i != dim)))), block["block_shape"][dim]]
    #                 border_segment_ids[dim] = [start_segment_ids, end_segment_ids]
    #                 border_segment_extent[dim] = [start_furthest_segment_index, end_furthest_segment_index]
    #         print(border_segment_ids)
    #         print(border_segment_extent)
    #         block["BorderSegments"]=border_segment_ids
    #         block["BorderSegmentsExtend"]=border_segment_extent
            ### Get coordinates of the most protruding segment and add margin and save it