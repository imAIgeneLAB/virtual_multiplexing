from pathlib import Path
from skimage.filters import threshold_otsu
from general_segmentation_functions.image_handling import get_image,save_image,view_napari
import numpy as np
import os

def remove_boundaries(img):
    # Set connectivity to take diagonals as well
    bound = find_boundaries(img, connectivity=1, mode="inner")
    mask = (img>0).astype(np.int64)
    # mask = distance_transform_edt(mask)
    img[bound] = 0
    img = np.stack([img, mask], axis=0)
    return img

end = da.from_zarr(zarr.open("/Users/samdeblank/Downloads/realtest_segmented.zarr"))
zarr_seg_path = '/Users/samdeblank/Downloads/realtest_stardist.zarr'

raw = da.from_zarr(zarr.open("/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest.zarr"))
border = da.from_zarr(zarr.open("/Users/samdeblank/Downloads/realtest_border.zarr"))
stardist = da.from_zarr(zarr.open("/Users/samdeblank/Downloads/realtest_stardist.zarr"))

border_segments=border_segments.compute()
final_segments=final_segments.compute()
center = segments.map_blocks(
    func=remove_boundaries,
    dtype=np.float64,
    # chunks=(2,)+chunk_size,
    new_axis=0
)

center[0], _ = dask_ndmeasure.label(center[0])
center = center.compute()

border_segments.shape

end2=final_segments[:, 450:600, 900:1200]
raw2=img_dask[:, 450:600, 900:1200]
border2=border_segments[:, 450:600, 900:1200]
stardist2=segments[:, 450:600, 900:1200]
center2=center[:, :, 450:600, 900:1200]

# # border.ndim

# view_napari([np.asarray(img_dask),np.asarray(segments),np.asarray(border_segments), np.asarray(final_segments = da.map_blocks(
# )], ["image", "label","label","label"], names=["raw", "end", "border", "stardist"])


view_napari([np.asarray(raw2),np.asarray(end2),np.asarray(border2), np.asarray(stardist2), center2], ["image", "label","label","label", "label"], names=["raw", "end", "border", "stardist", "center"])



image.shape
img=get_image("/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest1000x1000.tiff")
img.shape
dask_array.chunks
image.shape
img = img[:, 0:400,0:400]
save_image(img, "/Users/samdeblank/Documents/1.projects/Zipping/stardist_test/realtest400x400.tiff")