def insert_array(array, insert_array, coords=None, coords_center=None, only_foreground=False):
    """
    Insert array X somehwere in array Y
    
    e.g. Create a dot at specific at coordinates over another image
    """
    import numpy as np
    
    if not coords and not coords_center:
        print("Supply either coords (starts from lowest indeces on each axis) or coords_center")
   
    if insert_array.ndim < array.ndim:
        insert_array=np.expand_dims(insert_array, axis=0)
    elif insert_array.ndim > array.ndim:
        print("!!! Insert has more dimensions than input array")
        return
    
    array_shape = array.shape
    insert_shape = insert_array.shape
    start_end_coords=[]
    if coords:
        for idx, i in enumerate(coords):
            start = i
            end = i+insert_shape[idx]
            if end > array_shape[idx]:
                end = array_shape[idx]
                insert_array = insert_array.take(indices=range(0,end-start), axis=idx)
            start_end_coords.append(slice(start, end))
    elif coords_center:
        for idx, i in enumerate(coords_center):
            start = i-int(insert_shape[idx]/2)
            end = i+int(insert_shape[idx]/2)+1
            if start < 0:
                diff = abs(start)
                start = 0
                insert_array = insert_array.take(indices=range(diff,insert_shape[idx]), axis=idx)
            if end > array_shape[idx]:
                end = array_shape[idx]
                insert_array = insert_array.take(indices=range(0,end-start), axis=idx)
            start_end_coords.append(slice(start, end))
    
    insert_array_fg_mask = insert_array != 0
    start_end_coords=tuple(start_end_coords)
    # print(insert_array)
    array[start_end_coords][insert_array_fg_mask]=insert_array[insert_array_fg_mask]
    return array

def center_crop(image, crop_shape):
    crop_shape=tuple(crop_shape)
    img_shape = image.shape
    shape_diff = len(img_shape) - len(crop_shape)
    if shape_diff > 0:
        crop_shape = img_shape[0:shape_diff] + crop_shape
    crop_coords = []
    for idx, ax in enumerate(crop_shape):
        assert ax <= img_shape[
            idx], f"{ax} in crop shape {crop_shape} is larger than original image {img_shape}"
        if ax == img_shape[idx]:
            crop_coords.append(slice(0, ax))
        else:
            test = []
            max_start = img_shape[idx] - ax
            test = test + [max_start]
            start = int(round(0.5 * max_start))
            test = test + [start]
            end = start + ax
            test = test + [end]
            crop_coords.append(slice(start, end))

    image = image[tuple(crop_coords)]
    return image
    
def smooth_channel(image, sigma, filter='median', elsize=[1,1,1], in_plane=False):
    if filter=='median':
        from general_segmentation_functions.image_processing import filter_median
        data_smooth=filter_median(image=image, radius=sigma, elsize=elsize, in_plane=in_plane)
    elif filter=="gaussian":
        from general_segmentation_functions.image_processing import filter_gaussian
        data_smooth=filter_gaussian(image=image, sigma=sigma, in_plane=in_plane)
    else:
        print("Unknown filter: {}".format(filter))

    return(data_smooth)

def trim_zeros(arr):
    import numpy as np
    slices = tuple(slice(idx.min(), idx.max()+1) for idx in np.nonzero(arr))
    return(arr[slices])

def normalize_image(image, pmin=0, pmax=100, pmax_value=None, pmin_value=None, value_range=(), dtype=None):
    import numpy as np
    from general_segmentation_functions.image_handling import Image, get_image
    image = image.astype(np.float64)
    # Calculate minimal and maximum value of the resulting image (e.g. 0 to 1, or 0 to 16 bit)
    if value_range:
        vmin=value_range[0]
        vmax=value_range[1]
    else:
        vmin=0
        try:
            vmax=np.iinfo(image.dtype).max-1
        except:
            vmax=np.finfo(image.dtype).max-1
        else:
            print("Unknown image datatype: {}".format(image.dtype))
            return()

    if pmax_value is not None and pmin_value is not None:
        pass
    elif pmax_value is not None or pmin_value is not None:
        print("Only one of pmax_value or pmin_value defined. Please enter both pmax_value and pmin_value to manually set upper and lower percentiles")
        return
    else:
        pmax_value=np.percentile(image, pmax)
        pmin_value=np.percentile(image, pmin)
        print("Value of pmin({0})={1} and pmax({2})={3}".format(pmin, pmin_value, pmax, pmax_value))
    print(pmax_value, pmin_value)
    norm_image= abs(vmax-vmin) * (( image - pmin_value ) / ( pmax_value - pmin_value )) + vmin
    norm_image=np.clip(norm_image,vmin,vmax)

    if not dtype:
        dtype=image.dtype
        if value_range:
            print("No dtype specified, using dtype of provided image: {}".format(dtype))
            print("This might not correspond to wanted output range: {}".format(value_range))
    norm_image=norm_image.astype(dtype)

    return(norm_image)

def normalize_image_0_1(image, pmin=0, pmax=100, dtype=None):
    import numpy as np
    from general_segmentation_functions.image_handling import Image, get_image

    pmax_value=np.percentile(image, pmax)
    pmin_value=np.percentile(image, pmin)

    if dtype:
        pmax_value=dtype(pmax_value)
        pmin_value=dtype(pmin_value)

    norm_image= ( image - pmin_value ) / ( pmax_value - pmin_value )
    norm_image=np.clip(norm_image,0,1)
    return(norm_image)

def subtract_image(im, to_subtract, weight=0.2, elsize=[1,1,1], median_radius=3, median_in_plane=False):
    org_dtype=im.dtype
    if median_radius>0 or median_radius is not None:
        to_subtract=filter_median(image=to_subtract, radius=median_radius, elsize=elsize, in_plane=median_in_plane)
    im=im-(weight*to_subtract)
    im=im.clip(min=0)
    im=im.astype(org_dtype)
    return(im)

def rel_elsize(elsize):
    min_size=min(elsize)
    elsize_scaled= [round(x/min_size, 2) for x in elsize]
    return(elsize_scaled)

def draw_ellipsoid(shape=[], radius=1, elsize=[1,1,1], remove_border_zeros=True):
    from skimage.draw import ellipsoid
    from general_segmentation_functions.image_processing import rel_elsize, trim_zeros
    if shape:
        z,y,x = shape
    elif radius:
        z,y,x = [radius]*3

    elsize_scaled=rel_elsize(elsize)
    # print(elsize_scaled)
    z_temp, y_temp, x_temp = z,y,x
    if z==0:
        z_temp=1
    if y==0:
        y_temp=1
    if x==0:
        x_temp=1

    shape=ellipsoid(z_temp, y_temp, x_temp, spacing=elsize_scaled)

    if z==0:
        shape=shape[[2],:,:]
    if y==0:
        shape=shape[:,[2],:]
    if x==0:
        shape=shape[:,:,[2]]
    
    if remove_border_zeros:
        shape=trim_zeros(shape)
    return(shape)

def seg_replace_with_target(seg, labels, target):
    import numpy as np

    k = labels
    v = target

    mapping_ar = np.zeros(labels.max()+1,dtype=target.dtype) #k,v from approach #1
    mapping_ar[labels] = target
    out = mapping_ar[seg]
    return(out)
    #
    # # Extract out keys and values
    # k = np.array(list(dic.keys()))
    # v = np.array(list(dic.values()))
    #
    # # Get argsort indices
    # sidx = k.argsort()
    #
    # ks = k[sidx]
    # vs = v[sidx]
    # return vs[np.searchsorted(ks,seg)]

def filter_median(image, radius=None, shape_zyx=None, shape_type="ellipsoid", elsize=[1,1,1], in_plane=False):
    from skimage.filters import median
    import numpy as np
    from general_segmentation_functions.image_processing import rel_elsize, draw_ellipsoid

    img_dim = image.ndim
    assert img_dim==2 or img_dim==3, f"Image need to be 3D or 2D, got {img_dim} dimensions"
    elsize=rel_elsize(elsize)
    if img_dim==3:
        if in_plane:
            from skimage.morphology import disk
            k = disk(radius)
            data_smooth = np.zeros_like(image)
            for i, slc in enumerate(image):
                data_smooth[i, :, :] = median(slc, k)
        else:
            if shape_zyx is None and radius:
                shape_zyx=[radius]*3
            k = draw_ellipsoid(shape=shape_zyx)
            print(k.shape)
            data_smooth = median(image=image, footprint=k)
    else:
        from skimage.morphology import disk
        k = disk(radius)
        data_smooth = median(image=image, footprint=k)
    return(data_smooth)

def filter_gaussian(image, sigma, elsize=[1,1,1], in_plane=False):
    from skimage.filters import gaussian
    import numpy as np
    from general_segmentation_functions.image_processing import rel_elsize

    elsize=rel_elsize(elsize)

    if in_plane:
        data_smooth = np.zeros_like(image)
        if isinstance(sigma, int) or isinstance(sigma, float):
            sigma=[sigma/es for es in elsize[-2:]]
        for i, slc in enumerate(image):
            data_smooth[i, :, :] = gaussian(slc, sigma=sigma, preserve_range=True)
    else:
        if isinstance(sigma, int) or isinstance(sigma, float):
            if len(elsize)==image.ndim:
                sigma=[sigma/es for es in elsize]
            else:
                print("Provided elsize {} is not same length as image dimensions: {}".format(elsize, image.ndim))
                print("Using default non-differing elsizes")
        data_smooth = gaussian(image=image, sigma=sigma, preserve_range=True)

    return(data_smooth)

def filter_dog(image, sigma1, sigma2, elsize=[1,1,1], in_plane=False):
    from general_segmentation_functions.image_processing import filter_gaussian, rel_elsize

    elsize=rel_elsize(elsize)

    gaussian1=filter_gaussian(image, sigma=sigma1, elsize=elsize, in_plane=in_plane)
    gaussian2=filter_gaussian(image, sigma=sigma2, elsize=elsize, in_plane=in_plane)
    dog=gaussian1-gaussian2
    return(dog)

def erode_image(
    image,
    shape=None,
    shape_type=None,
    shape_zyx=[],
    radius=None,
    elsize=[1,1,1],
    in_plane=False,
    ):

    from general_segmentation_functions.image_processing import draw_ellipsoid
    from skimage.morphology import(
        erosion,
        binary_erosion
    )
    import numpy as np

    if shape is None:
        if shape_type=='ellipsoid' and (radius or shape_zyx):
            if radius and not shape_zyx:
                shape_zyx=[radius]*3
            shape=draw_ellipsoid(shape=shape_zyx, elsize=elsize)
        else:
            raise ValueError("Either define 'shape' or both 'shape_type' and either 'radius' or 'shape_xyz' that exists")

    if in_plane:
        if shape.ndim != 2:
            raise ValueError("Trying to apply a {}D shape while in_plane=True. Please provide either a 2D shape or 2D shape_type".format(str(shape.ndim)))
        eroded_im = np.zeros_like(image)
        for i, slc in enumerate(image):
            if image.dtype == "bool":
                eroded_im[i, :, :] = binary_erosion(image=slc, footprint=shape)
            else:
                eroded_im[i, :, :] = erosion(image=slc, footprint=shape)
    else:
        if shape.ndim != image.ndim:
            raise ValueError("Trying to apply a {0}D to a {1}D image. Please provide correct {1}D shape or shape_type".format(str(shape.ndim), str(image.ndim)))

        if image.dtype == "bool":
            eroded_im=binary_erosion(image=image, footprint=shape)
        else:
            eroded_im=erosion(image=image, footprint=shape)
    return(eroded_im)

def dilation_image(
    image,
    shape=None,
    shape_type=None,
    shape_zyx=[],
    radius=None,
    elsize=[1,1,1],
    in_plane=False,
    ):

    from general_segmentation_functions.image_processing import draw_ellipsoid
    from skimage.morphology import(
        dilation,
        binary_dilation
    )
    import numpy as np

    if shape is None:
        if shape_type=='ellipsoid' and (radius or shape_zyx):
            if radius and not shape_zyx:
                shape_zyx=[radius]*3
            shape=draw_ellipsoid(shape=shape_zyx, elsize=elsize)
        else:
            raise ValueError("Either define 'shape' or both 'shape_type' and either 'radius' or 'shape_xyz' that exists")

    if in_plane:
        if shape.ndim != 2:
            raise ValueError("Trying to apply a {}D shape while in_plane=True. Please provide either a 2D shape or 2D shape_type".format(str(shape.ndim)))
        dilated_im = np.zeros_like(image)
        for i, slc in enumerate(image):
            if image.dtype == "bool":
                dilated_im[i, :, :] = binary_dilation(image=slc, footprint=shape)
            else:
                dilated_im[i, :, :] = dilation(image=slc, footprint=shape)
    else:
        if shape.ndim != image.ndim:
            raise ValueError("Trying to apply a {0}D to a {1}D image. Please provide correct {1}D shape or shape_type".format(str(shape.ndim), str(image.ndim)))

        if image.dtype == "bool":
            dilated_im=binary_dilation(image=image, footprint=shape)
        else:
            dilated_im=dilation(image=image, footprint=shape)

    return(dilated_im)

def closing_image(
    image,
    shape=None,
    shape_type=None,
    shape_zyx=[],
    radius=None,
    elsize=[1,1,1],
    in_plane=False,
    ):

    from general_segmentation_functions.image_processing import draw_ellipsoid
    from skimage.morphology import(
        closing,
        binary_closing
    )
    import numpy as np

    if shape is None:
        if shape_type=='ellipsoid' and (radius or shape_zyx):
            if in_plane:
                from skimage.morphology import disk
                shape = disk(radius)
            else:
                if radius and not shape_zyx:
                    shape_zyx=[radius]*3
                shape=draw_ellipsoid(shape=shape_zyx, elsize=elsize)
        else:
            raise ValueError("Either define 'shape' or both 'shape_type' and either 'radius' or 'shape_xyz' that exists")

    if in_plane:
        if shape.ndim != 2:
            raise ValueError("Trying to apply a {}D shape while in_plane=True. Please provide either a 2D shape or 2D shape_type".format(str(shape.ndim)))
        closed_im = np.zeros_like(image)
        for i, slc in enumerate(image):
            if image.dtype == "bool":
                closed_im[i, :, :] = binary_closing(image=slc, footprint=shape)
            else:
                closed_im[i, :, :] = closing(image=slc, footprint=shape)
    else:
        if shape.ndim != image.ndim:
            raise ValueError("Trying to apply a {0}D to a {1}D image. Please provide correct {1}D shape or shape_type".format(str(shape.ndim), str(image.ndim)))

        if image.dtype == "bool":
            closed_im=binary_closing(image=image, footprint=shape)
        else:
            closed_im=closing(image=image, footprint=shape)

    return(closed_im)

def opening_image(
    image,
    shape=None,
    shape_type=None,
    shape_zyx=[],
    radius=None,
    elsize=[1,1,1],
    in_plane=False,
    # settings={},
    # save_step=False,
    img_origin="",
    outpath="",
    ):
    """
    Perform an opening operation on the image

    Can be defined by providing a 'settings' dictionary:
    e.g.
    settings={


        'shape' : np.array
        or
        'shape_type' : 'ellipsoid'
        +
        'axes' : [3,3,3]
        or
        'radius' : 3

        'elsize' : [1,1,1],
        'in_plane' : False,
        'img_origin' : substruct,
        'out_name' : "/dapi_opened"
    }

    img_origin and out_name only required if save_step==True
    otherwise, a settings dictionary is created from provided variables
    """

    from general_segmentation_functions.image_processing import draw_ellipsoid
    from skimage.morphology import(
        opening,
        binary_opening
    )
    import numpy as np
    # if not settings:
    #     settings={
    #         'radius' : radius,
    #         'shape_type' : shape_type,
    #         'axes' : shape_zyx or [radius]*3,
    #         'elsize' : elsize,
    #         'in_plane' : in_plane,
    #         'img_origin' : img_origin
    #     }


    # Create default shape of the ellipsoid
    if shape is None:
        if shape_type=='ellipsoid' and (radius or shape_zyx):
            if in_plane:
                from skimage.morphology import disk
                shape = disk(radius)
            else:
                if radius and not shape_zyx:
                    shape_zyx=[radius]*3
                shape=draw_ellipsoid(shape=shape_zyx, elsize=elsize)
        else:
            raise ValueError("Either define 'shape' or both 'shape_type' and either 'radius' or 'shape_xyz' that exists")
    print("Shape of opening shape: {}".format(shape.shape))
    # Opening the image
    if in_plane:
        if shape.ndim != 2:
            raise ValueError("Trying to apply a {}D shape while in_plane=True. Please provide either a 2D shape or 2D shape_type".format(str(shape.ndim)))
        opened_im = np.zeros_like(image)
        for i, slc in enumerate(image):
            if image.dtype == "bool":
                opened_im[i, :, :] = binary_opening(image=slc, footprint=shape)
            else:
                opened_im[i, :, :] = opening(image=slc, footprint=shape)
    else:
        if shape.ndim != image.ndim:
            raise ValueError("Trying to apply a {0}D to a {1}D image. Please provide correct {1}D shape or shape_type".format(str(shape.ndim), str(image.ndim)))

        if image.dtype == "bool":
            opened_im=binary_opening(image=image, footprint=shape)
        else:
            opened_im=opening(image=image, footprint=shape)

    # # Saving the image in the h5 if save_step==True
    # if save_step:
    #     if not outpath:
    #         print("'Save_step==True. Please specify outpath")
    #     else:
    #         h5=Image(h5, permission="a")
    #         h5.write(data=opened_im, outpath=outpath, metadata=settings)

    return(opened_im)

# def mask_image(image, method="sauvola", absmin=0, override_thr=None, window_size=15, k=0.2, r=None):
def mask_image(
    image,
    settings={}
    ):

    try:
        method=settings["method"]
    except:
        raise ValueError("Please define 'method' in settings")

    try:
        elsize = settings['elsize']
    except:
        elsize = [1,1,1]

    try:
        in_plane=settings['in_plane']
    except:
        in_plane=False

    ###############################
    if method=="global":
        try:
            absmin=settings['absmin']
        except:
            raise ValueError("Please specify 'absmin' in your settings for global thresholding")
        else:
            mask=image>=settings['absmin']

    elif method=="sauvola":

        from general_segmentation_functions.image_processing import sauvola_thresholding
        print(settings)
        try:
            absmin=settings['absmin']
        except:
            absmin=0

        try:
            k=settings['k']
        except:
            k=0.2

        try:
            r=settings['r']
        except:
            r=None

        try:
            window_size=settings['window_size']
        except:
            raise ValueError("Please specify 'window_size' in your settings for Sauvola thresholding (Uneven in or list of ints)")

        try:
            override_thr=settings['override_thr']
        except:
            override_thr=None
        print(window_size)
        mask=sauvola_thresholding(
            image,
            window_size=window_size,
            sd_weight=k, #k, sd=standard deviation
            max_sd=r, #r
            elsize=elsize,
            in_plane=in_plane,
            absmin=absmin,
            override_thr=override_thr
        )
    return(mask)

def sauvola_thresholding(
    image,
    window_size=61,
    sd_weight=0.2, #k, sd=standard deviation
    max_sd=None, #r
    elsize=[1,1,1],
    absmin=0,
    override_thr=None,
    in_plane=False
):
    """
    Perform sauvola thresholding.

    k: For low contrast images, make k as small as possible, otherwise high k will do

    https://hal.archives-ouvertes.fr/hal-02181880/document
    """

    from general_segmentation_functions.image_processing import rel_elsize
    import numpy as np
    from skimage.filters import threshold_sauvola

    mask=image>absmin

    if isinstance(window_size, int):
        window_size=[window_size]*3
        window_size_tmp=[x/y for x,y in zip(window_size, rel_elsize(elsize))]
        window_size=[]
        for el in window_size_tmp:
            rounded_el=int(round(el, 0))
            if rounded_el%2 != 1:
                if rounded_el==int(el):
                    rounded_el=int(el)+1
                else:
                    rounded_el=int(el)
            window_size.append(rounded_el)
        if in_plane:
            window_size=window_size[1:]

    if any([x%2 != 1 for x in list(window_size)]):
        raise ValueError("One of the window_size values is not odd. Sauvola requires odd window_size")

    if in_plane:
        if len(window_size) != 2:
            raise ValueError("window_size {} is not 2D for the defined in_plane=True".format(window_size))
        thr=np.zeros_like(image)
        for i, slc in enumerate(image):
            thr[i, :, :] = threshold_sauvola(slc, window_size=window_size, k=sd_weight, r=max_sd)
    else:
        thr = threshold_sauvola(image, window_size=window_size, k=sd_weight, r=max_sd)

    mask_sauvola = image > thr
    mask &= mask_sauvola

    if override_thr:
        override_mask = image > override_thr
        mask |= override_mask

    return(mask)

def fill_holes(
    image,
    in_plane=False
    ):

    from scipy.ndimage.morphology import binary_fill_holes
    import numpy as np

    if in_plane:
        filled = np.zeros_like(image)
        for i, slc in enumerate(image):
            filled[i, :, :] = binary_fill_holes(slc)
    else:
        filled = binary_fill_holes(image)

    return(filled)


def remove_overexposure(
    image=None,
    h5_path=None,
    max_intensity=None,
    output_ext="_overexp_rm",
    combined=True,
    input_group="/raw_channels",
    output_group="/filtered_channels",
    filtered_channels=[],
    combined_channels=[]
    ):
    """
    Remove overexpressed voxels (voxels > max_intensity) from an image or h5 structure (channels defined by 'filtered_channels')

    if h5_struct==True, the image is assumed to be h5 format and processing will be done within
    that h5 structure and settings below that setting will be used

    if combined==true all defined 'combined_channels' or default all channels are combined to only filter out voxels that are overexpressed in all channels
    """
    from general_segmentation_functions.image_handling import Image, get_image
    from pathlib import Path
    import numpy as np

    if image:
        if not max_intensity:
            max_intensity=np.iinfo(image.dtype).max-1
            print("No max intensity provided, only filtering out voxels with maximum value of {} image, max_intensity: {}".format(h5.dtype, max_intensity))
        ch_overexp=image>max_intensity
        im_overexp=image*~ch_overexp
        return(im_overexp)

    elif h5_path:
        h5=Image(h5_path, permission="a")
        h5.load()

        if combined:
            combined_mask=None
            # Generation of overexpression mask for a single (combined==False) or multiple (combined==True) channels
            for channel, image in h5.file[input_group].items():
                if combined_channels:
                    if channel not in combined_channels:
                        continue
                substruct=input_group+"/"+channel
                h5.load(substruct=substruct)
                image=h5.image
                if not max_intensity:
                    max_intensity=np.iinfo(h5.dtype).max-1
                    print("No max intensity provided, only filtering out voxels with maximum value of {} image, max_intensity: {}".format(h5.dtype, max_intensity))
                ch_overexp=image>max_intensity
                print("Channel {} has {} overexpressed voxels".format(channel, ch_overexp.sum()))
                if combined_mask is None:
                     combined_mask=ch_overexp
                else:
                    combined_mask *= ~ch_overexp
            print("Combined # of overexpressed voxels: {}".format(combined_mask.sum()))


        for channel in filtered_channels:
            print("Removing overexpression from {}".format(channel))
            substruct=input_group+"/"+channel
            print(substruct)
            outname=output_group+"/"+channel+"/"+channel+output_ext
            h5.load(substruct=substruct)
            image=h5.image
            if not combined:
                ch_overexp=image>max_intensity
                im_overexp=image*~ch_overexp
            else:
                im_overexp=image * combined

            settings={
                'filter' : 'combined_overexpression_removed',
                'threshold' : max_intensity,
                'combined_overexpression' : combined
            }
            print(h5_path, outname)
            h5.write(data=im_overexp, outpath=h5_path, substruct=outname, metadata=settings)
        h5.close()

    else:
        print("Please provide either 'image' or 'h5_path'")

def find_local_maxima(image, size=[3, 13, 13], shape_type="", elsize=[1,1,1], threshold=0.05, dilate=0):
    """Find peaks in image."""

    from general_segmentation_functions.image_processing import draw_ellipsoid
    from scipy.ndimage import maximum_filter
    import numpy as np

    if threshold == -float('Inf'):
        threshold = img.min()

    if shape_type=="ellipsoid":
        if isinstance(size, int):
            footprint = draw_ellipsoid(radius=size/2, elsize=elsize)
        else:
            footprint = draw_ellipsoid(shape=size, elsize=elsize)
    else:
        footprint = np.ones(size, dtype=bool)
    image_max = maximum_filter(image, footprint=footprint, mode='constant')

    mask = image == image_max
    mask &= image > threshold

    coordinates = np.column_stack(np.nonzero(mask))[::-1]

    peaks = np.zeros_like(image, dtype=np.bool)
    peaks[tuple(coordinates.T)] = True

    if dilate:
        peaks=dilation_image(peaks, shape_type="ellipsoid", radius=dilate)
    return(peaks)

def get_nuclear_overlap(segments, images, overlap="full", border_size=3, per_plane=False):
    """

    FOR THE BORDER, SKIMAGE.SEGMENTATION.EXPAND_LABELS SHOULD WORK BETTER (No flow to other segments),
    BUT DISTANCE DOES NOT TAKE ELSIZE INTO ACCOUNT

    Get overlap of specific markers for nuclear overlap (full/border). Takes either full nuclei or the area around nuclei
    """
    from general_segmentation_functions.image_handling import Image, get_image, save_image_to_h5
    from skimage.measure import(
        regionprops,
        regionprops_table
    )
    import pandas as pd
    import numpy as np

    if not isinstance(segments, np.ndarray):
        segments=get_image(segments)

    assert(segments is not None)

    loaded_images=[]
    if isinstance(images, np.ndarray):
        loaded_images=images
    elif isinstance(images, str):
        loaded_images=get_image(image)
    else:
        for image in images:
            if not isinstance(image, np.ndarray):
                image=get_image(image)

            loaded_images.append(image)
        loaded_images=np.stack(loaded_images, axis=-1)

    if overlap=="full":
        props=regionprops_table(label_image=segments, intensity_image=loaded_images, properties=['label', 'mean_intensity'])
    if overlap=="border":
        from general_segmentation_functions.image_processing import dilation_image
        from skimage.segmentation import expand_labels

        dilated_segments_yx=segments.copy()
        dilated_segments_zyx=segments.copy()

        """ Currently set to 0 as it seems to add more noise that real signal """
        # border_zyx_steps=int(round(border_size/3))
        border_zyx_steps=0
        border_yx_steps=border_size-border_zyx_steps

        for i, slc in enumerate(dilated_segments_yx):
            dilated_segments_yx[i, :, :] = expand_labels(slc, distance=border_yx_steps)
        if border_zyx_steps>0:
            dilated_segments_zyx=expand_labels(dilated_segments_zyx, distance=border_zyx_steps)

        dilated_segments=np.maximum(dilated_segments_yx, dilated_segments_zyx)
        border_segments = dilated_segments*(segments != dilated_segments)

        def border_planes_max_intensity(regionmask, intensity):
            max_mean=0
            for i, slc in enumerate(intensity):
                slc_mean=np.mean(slc[regionmask[i, :, :]])
                if slc_mean>max_mean:
                    max_mean=slc_mean
            return max_mean

        if per_plane:
            props=regionprops_table(label_image=border_segments, intensity_image=loaded_images, properties=['label', 'mean_intensity'], extra_properties=(border_planes_max_intensity,))
        else:
            props=regionprops_table(label_image=border_segments, intensity_image=loaded_images, properties=['label', 'mean_intensity'])

    data = pd.DataFrame(props)

    return(data)

def remove_border_segments(segments):
    import numpy as np
    border_segments = get_border_segments(segments)
    border_mask=~np.isin(segments, border_segments)
    segments = segments * border_mask
    return(segments)
        
def filter_nuclear_overlap(segments, image, overlap="full", threshold=0.5, border_size=3, per_plane=False, outpath=None):
    """

    FOR THE BORDER, SKIMAGE.SEGMENTATION.EXPAND_LABELS SHOULD WORK BETTER (No flow to other segments),
    BUT DISTANCE DOES NOT TAKE ELSIZE INTO ACCOUNT

    Filters nuclei that contain >threshold mean intensity

    overlap (full/border): Takes either full nuclei or the area around nuclei

    Weird result: When overlapping mean intensity with segments some high intensity segments don' t show up in napari???
    """
    from general_segmentation_functions.image_handling import Image, get_image, save_image_to_h5
    from skimage.measure import(
        regionprops,
        regionprops_table
    )
    import pandas as pd
    import numpy as np

    if not isinstance(segments, np.ndarray):
        h5=Image(segments, permission="r")
        h5.load()
        segments=h5.image
        h5.close()

    if not isinstance(image, np.ndarray):
        h5=Image(image, permission="r")
        h5.load()
        image=h5.image
        h5.close()

    if overlap=="full":
        props=regionprops_table(label_image=segments, intensity_image=image, properties=['label', 'mean_intensity'])
    if overlap=="border":
        from general_segmentation_functions.image_processing import dilation_image
        from skimage.segmentation import expand_labels

        dilated_segments_yx=segments.copy()
        dilated_segments_zyx=segments.copy()

        """ Currently set to 0 as it seems to add more noise that real signal """
        # border_zyx_steps=int(round(border_size/3))
        border_zyx_steps=0
        border_yx_steps=border_size-border_zyx_steps

        for i, slc in enumerate(dilated_segments_yx):
            dilated_segments_yx[i, :, :] = expand_labels(slc, distance=border_yx_steps)
        if border_zyx_steps>0:
            dilated_segments_zyx=expand_labels(dilated_segments_zyx, distance=border_zyx_steps)

        dilated_segments=np.maximum(dilated_segments_yx, dilated_segments_zyx)

        # for i in range(border_size):
        #     if (i+1)%3==0:
        #         # shape=np.array([[[0,0,0],
        #         #                  [0,1,0],
        #         #                  [0,0,0]],
        #         #                 [[0,1,0],
        #         #                  [1,1,1],
        #         #                  [0,1,0]],
        #         #                 [[0,0,0],
        #         #                  [0,1,0],
        #         #                  [0,0,0]]])
        #     else:
        #         for i, slc in enumerate(dilated_segments):
        #             dilated_segments[i, :, :] = expand_labels(slc)
        #         # shape=np.array([[[0,1,0],
        #         #                  [1,1,1],
        #         #                  [0,1,0]]])
        #     dilated_segments=dilation_image(dilated_segments, shape=shape)
        border_segments = dilated_segments*(segments != dilated_segments)

        def border_planes_max_intensity(regionmask, intensity):
            max_mean=0
            for i, slc in enumerate(intensity):
                slc_mean=np.mean(slc[regionmask[i, :, :]])
                if slc_mean>max_mean:
                    max_mean=slc_mean
            return max_mean

        if per_plane:
            props=regionprops_table(label_image=border_segments, intensity_image=image, properties=['label', 'mean_intensity'], extra_properties=(border_planes_max_intensity,))
        else:
            props=regionprops_table(label_image=border_segments, intensity_image=image, properties=['label', 'mean_intensity'])

    data = pd.DataFrame(props)

    # import matplotlib.pyplot as plt
    # props=regionprops_table(label_image=im_nucl, intensity_image=im_iba1, properties=['label', 'mean_intensity'])
    # data = pd.DataFrame(props)
    # plt.axis([0, 40000, 0, 30])
    # plt.hist(data["mean_intensity"], bins = 100)
    # plt.show()
    property="mean_intensity"
    if per_plane:
        property="border_planes_max_intensity"

    if outpath:
        from numpy import copy
        if overlap=="border":
            props_segments=copy(border_segments)
        else:
            props_segments=copy(segments)
        props_segments=props_segments.astype(data[property].dtype)
        for index, row in data.iterrows():
            props_segments[props_segments==row["label"]] = row[property]
        save_image_to_h5(props_segments, h5_path=outpath)


    select=data[data[property]>=threshold]['label'].tolist()
    thr_segments=segments*np.isin(segments, select)
    return(thr_segments)

def calculate_edt(mask, elsize=[1,1,1], threshold=None):
    from scipy.ndimage import distance_transform_edt

    edt = distance_transform_edt(
        mask,
        sampling=elsize
        )

    if threshold:
        edt *= edt >= threshold

    return(edt)

def get_border_segments(image, dist_from_border=1):
    import numpy as np
    edges_z1=image[0:dist_from_border,
        :,
        :].ravel()
    edges_z2=image[
        -dist_from_border:
        :,
        :].ravel()

    #edges_y - edges_z to skip lowest and highest plane in z
    edges_y1=image[
        dist_from_border:-dist_from_border,
        0:dist_from_border,
        :].ravel()

    edges_y2=image[
        dist_from_border:-dist_from_border,
        -dist_from_border:,
        :].ravel()

    #edges_x - edges_z - edges_y to skip lowest and highest plane in z and y
    edges_x1=image[
        dist_from_border:-dist_from_border,
        dist_from_border:-dist_from_border,
        0:dist_from_border].ravel()

    edges_x2=image[
        dist_from_border:-dist_from_border,
        dist_from_border:-dist_from_border,
        -dist_from_border:].ravel()

    edges=np.concatenate([edges_z1, edges_z2, edges_y1, edges_y2, edges_x1, edges_x2])
    unique_edges=np.unique(edges)
    return(unique_edges)

def fill_label_holes(lbl_img, **kwargs):
    """Fill small holes in label image."""
    from scipy.ndimage.morphology import binary_fill_holes
    from scipy.ndimage.measurements import find_objects
    import numpy as np
    # TODO: refactor 'fill_label_holes' and 'edt_prob' to share code
    def grow(sl,interior):
        return tuple(slice(s.start-int(w[0]),s.stop+int(w[1])) for s,w in zip(sl,interior))
    def shrink(interior):
        return tuple(slice(int(w[0]),(-1 if w[1] else None)) for w in interior)
    objects = find_objects(lbl_img)
    lbl_img_filled = np.zeros_like(lbl_img)
    for i,sl in enumerate(objects,1):
        if sl is None: continue
        interior = [(s.start>0,s.stop<sz) for s,sz in zip(sl,lbl_img.shape)]
        shrink_slice = shrink(interior)
        grown_mask = lbl_img[grow(sl,interior)]==i
        mask_filled = binary_fill_holes(grown_mask,**kwargs)[shrink_slice]
        lbl_img_filled[sl][mask_filled] = i
    return lbl_img_filled
