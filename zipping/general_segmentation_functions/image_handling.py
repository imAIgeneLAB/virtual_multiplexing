import sys
import os
from pathlib import Path
import numpy as np
class Image(object):
    def __init__(self, path, permission='r'):
        import pathlib
        from pathlib import Path
        import os
        import sys
        path=str(path)
        self.known_image_types=[".nii.gz", ".tiff", ".tif", ".h5", ".ims"]
        self.path = os.path.realpath(path).replace("\\", "/")
        self.format = self.get_format() or ""
        self.permission = permission
        self.file=None
        self.ds=None
        self.image=None       # TODO Loads it into memory (normal self.ds does not. FInd way to work around???)
        self.dims=None
        self.axlab=["z", "y", "x"]
        self.elsize=[1,1,1]
        self.rel_elsize=[1,1,1]
        self.metadata={}
        self.pathparts=self.split_path()
        self.h5path=self.pathparts
        
        self.ds=None
        self.image=None
        
        if not os.path.exists(self.pathparts['file']) and self.permission=="r":
            print("WARNING: Path to image file does not exist\n{}".format(self.pathparts['file']))
            sys.exit()


    '''
    General functions for opening/writing/viewing/closing files
    '''

    def load(self, substruct='', channel=''):
        import os
        self.ds=None
        self.image=None

        image_loaders={
        '.h5' : self.h5_load,
        '.ims' : self.ims_load,
        '.tiff' : self.tif_load,
        '.tif' : self.tif_load,
        '.nii.gz' : self.nii_load,
        '.nii' : self.nii_load,
        '.czi' : self.czi_load
        }

        try:
            loader=image_loaders[self.format]
        except:
            print("No loader for {} exists yet".format(self.format))
        else:
            loader(substruct=substruct, channel=channel)

        self.axlab=self.get_axlab()
        return(self.image)

    def write(self, data=None, outpath="", substruct="", ext="", metadata={}, overwrite=False, elsize=[1,1,1], **kwargs):
        import re
        image_writers={
        '.h5' : self.h5_write,
        '.tif' : self.tif_write,
        '.tiff' : self.tif_write,
        '.nii.gz' : self.nii_write
        }

        if not outpath:
            try:
                # TODO THIS DOES NOT MAKE FULL SENSE
                outpath=self.pathparts["file_no_ext"]+self.format
            except:
                print("Please specify an outpath or ext(e.g. '.h5')")

        try:
            writer=image_writers[self.format]
        except:
            print("No writer for {} exists yet".format(self.format))
        else:
            writer(data=data, outpath=outpath, substruct=substruct, elsize=elsize, metadata=metadata, **kwargs)

        # match=False
        # outpath=str(outpath)
        # for ext, writer in image_writers.items():
        #     if re.match(".+\\{}\/*.*$".format(ext), outpath):
        #         match=True
        #         writer(data=data, outpath=outpath, substruct=substruct, overwrite=False, metadata=metadata)
        # if not match:
        #     print("No writer for {} exists yet".format(outpath))

    def save(self, data=None, outpath="", substruct="", ext="", metadata={}, overwrite=False):
        self.write(self, data=data, outpath=outpath, substruct=substruct, ext=ext, metadata=metadata, overwrite=overwrite, elsize=elsize)

    def close(self):
        """Close a file."""
        import h5py
        try:
            if isinstance(self.file, h5py.File):
                self.file.close()
        except:
            print("Can't close file")

    def view(self, images=[], labels=[], elsize=[]):
        import napari
        import numpy as np
        
        images = images or self.image
        if images is None:
            images = self.pathparts['substruct']
        print(images)
        viewer=napari.Viewer()

        if images==[] and self.ds==None:
            print("Images is not defined and the image object is not an image. Please load in an image (im.load(substruct)) in the h5 structure")
        # elif images!=[]:
        #     if not elsize:
        #         elsize=self.rel_elsize
        #     print("ASDASDASDAS")
        #     print(self.ds)
        #     viewer = viewer.add_image(self.ds, name=self.pathparts['substruct'], scale=elsize)
        elif isinstance(images, str):
            if not elsize:
                elsize=self.rel_elsize
            viewer = viewer.add_image(self.file[images], name=images, scale=elsize)
        elif isinstance(images, list) or isinstance(images, tuple):
            for idx, substruct in enumerate(images):
                if labels is None or labels==[]:
                    label = None
                else:
                    label=labels[idx]
                if elsize is None or elsize==[]:
                    elsize=self.file[substruct].attrs['element_size_um']
                if 'image_type' in self.file[substruct].attrs.keys():
                    if self.file[substruct].attrs['image_type']=='labels' or self.file[substruct].attrs['image_type']=='segments':
                        viewer.add_labels(self.file[substruct], name=substruct, scale=elsize)
                    else:
                        viewer.add_image(self.file[substruct], name=substruct, scale=elsize)
                elif label=="label":
                    viewer.add_labels(self.file[substruct], name=substruct, scale=elsize)
                else:
                    viewer.add_image(self.file[substruct], name=substruct, scale=elsize)
            for lay in viewer.layers: lay.visible = False
        elif isinstance(images, dict):
            for substruct, type in images.items():
                print("opening:", substruct)
                elsize=self.file[substruct].attrs['element_size_um']
                if type=='labels':
                    viewer.add_labels(self.file[substruct], name=substruct, scale=elsize)
                elif type=='image':
                    viewer.add_image(self.file[substruct], name=substruct, scale=elsize)
            for lay in viewer.layers: lay.visible = False
                
        elif isinstance(images, np.ndarray):
            if labels=='label':
                viewer.add_labels(images, scale=elsize)
            else:
                viewer.add_image(images, scale=elsize)
        napari.run()

    '''
    General functions for all images
    '''

    def get_format(self):
        import re

        image_type=None
        for ext in self.known_image_types:
            if re.match(".+"+ext+"/*.*$", self.path):
                image_type=ext
                break

        if not image_type:
            # FIXME Gives wrong output if . in folder structure
            print(".{} is not a known image type".format(".".join(self.path.split(".")[1:])))
            print("Known image types are:", self.known_image_types)
        else:
            return(image_type)

    def get_axlab(self):
        """Get the axis labels."""

        if ((self.axlab is not None) and (len(self.axlab) > 0)):
            axlab = ''.join(self.axlab)
#             print("""WARNING:
#                   axlab already specified as {}""".format(self.axlab))
            return axlab

        formats = {
            '.h5': self.h5_get_axlab,
            '.ims': self.ims_get_axlab,
        }
        axlab = formats[self.format]()

        if axlab is None:
            axlab = 'zyxct'[:self.get_ndim()]
#             raise Exception("""WARNING: axlab is None;
#                                replaced by {}""".format(axlab))

        return axlab

    def get_rel_elsize(self, elsize):
        min_size=min(elsize)
        elsize_scaled= [round(x/min_size, 2) for x in elsize]
        return(elsize_scaled)

    def split_path(self):
        file_comps={}
        file_comps['ext']=self.format
        try:
            before_ext, after_ext = self.path.split(self.format)
        except:
            before_ext = self.path
            after_ext=""
        file_comps['file'] = before_ext + file_comps['ext']
        file_comps['file_no_ext'] = before_ext
        if file_comps['ext']=="":
            file_comps['folder']=before_ext
            file_comps['filename']=""
            file_comps['filename_no_ext']=""
        else:
            file_comps['folder'], file_comps['filename'] = file_comps['file'].rsplit("/", 1)
            file_comps['filename_no_ext']=file_comps['filename'].split(file_comps['ext'])[0]
        file_comps['folder']=file_comps['folder']+"/"
        file_comps['substruct']=None
        if after_ext!='' and after_ext!='/':
            file_comps['substruct']=after_ext
            file_comps['group'], file_comps['dataset'] = after_ext.rsplit("/", 1)
        return(file_comps)

    def attr2datatype(self, attrs,datatype=str):
        fixed_attrs=[]
        try:
            for t in attrs:
                try:
                    t=t.decode('utf-8')
                except:
                    pass
                finally:
                    fixed_attrs.append(t)

            fixed_attrs=datatype(''.join(fixed_attrs))
        except:
            fixed_attrs=attrs
        return(fixed_attrs)

    def attr2str(self, attrs):
        fixed_attrs=[]
        try:
            for t in attrs:
                try:
                    t=t.decode('utf-8')
                except:
                    pass
                finally:
                    fixed_attrs.append(t)
            fixed_attrs=''.join(fixed_attrs)
        except:
            fixed_attrs=attrs
        return(fixed_attrs)

    def attrs2dict(self, attrs):
        dict={}
        for k,v in attrs.items():
            dict[k]=self.attr2str(v)
        return(dict)

    '''
    Everything for .ims files
    '''

    def ims_load(self, substruct='', channel='', remove_zeropadding=True):
        import h5py
        import numpy as np
        channel=str(channel)
        if self.file is None:
            self.file = h5py.File(name=self.pathparts['file'], mode=self.permission)

        substruct = substruct or self.pathparts['substruct']
        if substruct:
            self.pathparts['substruct']=substruct
            self.pathparts['group'], self.pathparts['dataset'] = self.pathparts['substruct'].rsplit("/", 1)
            try:
                self.ds = self.file[substruct]
            except:
                print("{} is not a valid channel substructure for the .ims image".format(substruct))
            else:
                self.metadata.update(self.attrs2dict(self.file[self.pathparts['group']].attrs))
                self.image=self.ds[:]
                self.dims = self.ims_get_dims()
                self.elsize=self.ims_get_elsize()
                self.rel_elsize=self.get_rel_elsize(self.elsize)
                self.dtype = self.ds.dtype
                self.chunks = self.ds.chunks
                if self.image.shape != self.dims[-(self.image.ndim):]:
                    print("Imaris image is  zeropadded: org({}), unzeropadded({})".format(self.image.shape, self.dims[:3]))
        elif channel:
            default_channels_path='/DataSet/ResolutionLevel 0/'
            
            try:
                nr_timepoints = len([x for x in self.file[default_channels_path]])
                if nr_timepoints>1:
                    images = []
                    for frame in range(nr_timepoints):
                        self.pathparts['substruct']="{}/TimePoint {}/Channel {}/Data".format(default_channels_path, frame, channel)
                        self.pathparts['group'], self.pathparts['dataset'] = self.pathparts['substruct'].rsplit("/", 1)
                        print("Loading TimePoint {}".format(frame))
                        self.ds=self.file[ self.pathparts['substruct']]
                        images.append(self.file[ self.pathparts['substruct']][:])
                    self.image = np.stack(images, axis=0)
                else:
                    channel_path = default_channels_path+"TimePoint 0/"
                    self.pathparts['substruct']="{}/Channel {}/Data".format(channel_path, channel)
                    self.pathparts['group'], self.pathparts['dataset'] = self.pathparts['substruct'].rsplit("/", 1)
                    self.ds = self.file[self.pathparts['substruct']]
                    self.image=self.ds[:]
            except Exception as error:
                print('An exception occurred: {}'.format(error))
                print("{} is not a valid channel within the .ims image".format(channel))
            else:
                self.metadata.update(self.attrs2dict(self.file[self.pathparts['group']].attrs))
                
                self.dims = self.ims_get_dims()
                self.elsize=self.ims_get_elsize()
                self.rel_elsize=self.get_rel_elsize(self.elsize)
                self.dtype = self.ds.dtype
                self.chunks = self.ds.chunks
                if self.image.shape != self.dims[-(self.image.ndim):]:
                    print("Imaris image is zeropadded: org({}), unzeropadded({})".format(self.image.shape, self.dims[-(self.image.ndim):]))
        else:
            print("Base .ims file loaded as no substructure is specified")

        if remove_zeropadding:
            self.ims_remove_zeropadding()
        return(self.image)

    def ims_get_dims(self):

        if (self.ds is not None and self.metadata):
            #ATTRSTOSTR???
            #dimX=int("".join([str(x.decode()) for x in list(self.metadata["ImageSizeX"])]))
            dimX=self.attr2datatype(self.metadata["ImageSizeX"], int)
            dimY=self.attr2datatype(self.metadata["ImageSizeY"], int)
            dimZ=self.attr2datatype(self.metadata["ImageSizeZ"], int)

        else:
            dimX=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['X'], int)
            dimY=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['Y'], int)
            dimZ=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['Z'], int)
        dimC = len(self.file['/DataSet/ResolutionLevel 0/TimePoint 0/'])
        dimT = len(self.file['/DataSet/ResolutionLevel 0/'])

        dims=[dimT, dimZ, dimY, dimX]
        return(dims)

    def ims_get_axlab(self):
        return('zyxct')

    def ims_list_channels(self):
        default_channels_path='/DataSet/ResolutionLevel 0/TimePoint 0/'
        default_info_path='/DataSetInfo'
        print(self.file[default_channels_path])
        channel_names={}
        for channel in self.file[default_channels_path]:
            try:
                channel_name=self.attr2str(self.file[default_info_path][channel].attrs["Name"])
                channel_names[channel.split(" ")[1]]=channel_name
                print("{} - {}".format(channel, channel_name))
            except:
                print(channel)
        return(channel_names)

    def ims_remove_zeropadding(self, in_place=False):
        unzeropadded_X=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['X'], int)
        unzeropadded_Y=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['Y'], int)
        unzeropadded_Z=self.attr2datatype(self.file['/DataSetInfo/Image'].attrs['Z'], int)
        try:
            self.image[:]
        except:
            print("No dataset has been loaded yet")
        else:
            if in_place:
                resize_list = tuple(None) * (self.image[:].ndim-3) + (unzeropadded_Z, unzeropadded_Y,unzeropadded_X)
                self.ds.resize(resize_list)
                self.image=self.ds[:]
                self.dims=self.ds.shape
            else:
                resize_list=(slice(None),) * (self.image[:].ndim-3) + (slice(0,unzeropadded_Z), slice(0,unzeropadded_Y), slice(0,unzeropadded_X))
                self.image=self.image[resize_list]

    def ims_get_elsize(self):
        im_info = self.file['/DataSetInfo/Image']

        extmin0 = float(self.attr2str(im_info.attrs['ExtMin0']))
        extmin1 = float(self.attr2str(im_info.attrs['ExtMin1']))
        extmin2 = float(self.attr2str(im_info.attrs['ExtMin2']))
        extmax0 = float(self.attr2str(im_info.attrs['ExtMax0']))
        extmax1 = float(self.attr2str(im_info.attrs['ExtMax1']))
        extmax2 = float(self.attr2str(im_info.attrs['ExtMax2']))

        extX = extmax0 - extmin0
        extY = extmax1 - extmin1
        extZ = extmax2 - extmin2

        dims = self.dims or self.ims_get_dims()
        # elsizeX = round(extX / dims[2], 3)
        # elsizeY = round(extY / dims[1], 3)
        # elsizeZ = round(extZ / dims[0], 3)

        elsizeX = extX / dims[2]
        elsizeY = extY / dims[1]
        elsizeZ = extZ / dims[0]

        elsize=[elsizeZ, elsizeY, elsizeX]
        self.elsize=elsize
        return(elsize)

    '''
    Everything for .h5 files
    '''

    def get_all_datasets(self, substruct="/"):
        import h5py
        keys = []
        self.file[substruct].visit(lambda key : keys.append(substruct+"/"+key) if isinstance(self.file[substruct+"/"+key], h5py.Dataset) else None)
        return keys

    def h5_load(self, substruct='', **kwargs):
        import h5py
        if self.file is None:
            self.file = h5py.File(name=self.pathparts['file'], mode=self.permission)
        self.pathparts['substruct'] = substruct or self.pathparts['substruct']
        if self.pathparts['substruct']:
            try:
                self.ds = self.file[self.pathparts['substruct']]
            except:
                if self.permission=="r":
                    print("Substruct {} does not exist, loading base .h5 file".format(substruct))
            else:
                self.image=self.ds[:]
                self.dims = self.ds.shape
                self.dtype = self.ds.dtype
                self.chunks = self.ds.chunks
                self.metadata = self.attrs2dict(self.ds.attrs)

                try:
                    self.elsize=list(self.metadata['element_size_um'])
                    self.rel_elsize=self.get_rel_elsize(self.elsize)
                except:
                    pass
        else:
            print("Base .h5 file loaded as no substructure is specified")

        return(self.image)

    def h5_write(self, outpath, data=None, substruct="", metadata={}, chunks=None, overwrite=False, **kwargs):
        import h5py
        "Chunks can be True (automatically) or tuple"
        
        try:
            compression=kwargs["compression"]
        except:
            compression=None
        try:
            compression_level=kwargs["compression_level"]
        except:
            compression_level=None
            
        if self.file is None:
            self.load(self.pathparts['file'], "a")

        if data is None:
            data = self.image
        before_ext, after_ext=str(outpath).split(".h5")
        h5_base=before_ext+".h5"

        if len(after_ext)<=1:
            after_ext=None

        substruct=after_ext or substruct
        if not substruct:
            print("No substructure specified in outpath or substruct")
            return()

        output_h5=h5py.File(h5_base,"a")
        substruct_split = substruct.split("/")
        substruct_split=[grp for grp in substruct_split if grp]
        groups = substruct_split[:-1]
        dataset_name = substruct_split[-1]

        grp=output_h5
        for grp_name in groups:
            try:
                grp[grp_name]
            except KeyError:
                grp.create_group(grp_name)
            finally:
                grp=grp[grp_name]

        if dataset_name in grp.keys():
            del grp[dataset_name]
        grp.create_dataset(name=dataset_name, data=data, chunks=chunks, compression=compression, compression_opts=compression_level)

        grp[dataset_name].attrs.update(self.metadata)

        for k,v in metadata.items():
            if v is None:
                v="None"
            if k in grp[dataset_name].attrs.keys():
                grp[dataset_name].attrs.modify(name=str(k), value=v)
            else:
                grp[dataset_name].attrs.create(name=str(k), data=v)
        if 'element_size_um' not in grp[dataset_name].attrs.keys():
            grp[dataset_name].attrs.create(name='element_size_um', data=self.elsize)
        if 'DIMENSION_LABELS' not in grp[dataset_name].attrs.keys():
            grp[dataset_name].attrs.create(name='DIMENSION_LABELS', data=self.axlab)
        if 'creation_date' not in grp[dataset_name].attrs.keys():
            from datetime import datetime
            grp[dataset_name].attrs.create(name='creation_date', data=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        output_h5.close()

    def h5_get_axlab(self):
        """Get the dimension labels from a dataset."""

        if 'DIMENSION_LABELS' in self.metadata.keys():
            try:
                axlab = b''.join(self.metadata['DIMENSION_LABELS']).decode("utf-8")
            except TypeError:
                axlab = ''.join(self.metadata['DIMENSION_LABELS'])
        else:
            axlab = None

        return axlab

    def list_groups(self, substruct=None):
        """List groups of h5 file"""

        if self.file:
            if substruct:
                groups=list(self.file[substruct].keys())
            else:
                groups=list(self.file.keys())
            return(groups)
        else:
            print("File not loaded yet, use: file.load()")

    def remove_group(self, substruct):
        if not substruct in self.file:
            print("{} does not exist in file. Please provide correct group".format(substruct))
        else:
            del self.file[substruct]

    def move_group(self, in_group, out_group):
        """List groups of h5 file"""

        if self.file:
            try:
                self.file.move(in_group, out_group)
            except:
                import h5py
                keys = []
                self.file[in_group].visit(lambda key : keys.append(key))
                [ self.file.move(in_group+"/"+key, out_group+"/"+key) for key in keys ]
                self.remove_group(in_group)
            #         pass
        else:
            print("File not loaded yet, use: file.load()")


    def tif_load(self, **kwargs):
        from skimage import io
        import numpy as np
        from pathlib import Path
        if isinstance(self.path, str):
            tif_path=Path(self.path)
            if tif_path.is_dir():
                images=list(tif_path.iterdir())
                images.sort()
                # for img_path in images:
                #     print(img_path)
                images = [io.imread(fname=img_path) for img_path in images]
                self.ds = np.stack(images, axis=0)
                self.image = self.ds
                self.dims = self.ds.shape
                self.dtype = self.ds.dtype
            elif tif_path.is_file():
                self.ds=io.imread(
                    fname=tif_path
                    )
                self.image=self.ds
                self.dims = self.ds.shape
                self.dtype = self.ds.dtype
        elif isinstance(self.path, list):
            images = []
            for tif_path in self.path:
                print(f"Loading: {tif_path}")
                images.append(io.imread(fname=tif_path))
            self.ds=np.stack(images, axis=0)
            self.image=self.ds
            self.dims = self.ds.shape
            self.dtype = self.ds.dtype
        return(self.image)

    def tif_write(self, outpath, data=None, stacked=True, **kwargs):
        from skimage import io
        if data is None:
            data=self.image
                
        if stacked:
            io.imsave(
                    fname=outpath,
                    arr=data,
                    check_contrast=False
                    )
        else:
            if os.path.isdir(outpath):
                for idx, plane in enumerate(data):
                    file_outpath = Path(outpath, f"{idx:03d}.tif")
                    io.imsave(
                        fname=file_outpath,
                        arr=plane,
                        check_contrast=False
                        )
            else:
                print("If defined to have a tif per slice in stack, please provide a directory instead of file")

    def nii_load(self, **kwargs):
        import nibabel as nib
        self.ds=nib.load(self.path)
        self.image=self.ds.dataobj[:]
        self.dims = self.image.shape
        self.dtype = self.image.dtype
        return(self.image)

    def nii_write(self, outpath, data=None, substruct="", metadata={}, overwrite=False, elsize=None, dtype=None, **kwargs):
        import nibabel as nib
        if data is not None:
            nii_img=nib.Nifti1Image(data, affine=self.get_transmat(elsize), dtype=dtype)
            nib.save(
                nii_img,
                outpath
            )
        else:
            nii_img=nib.Nifti1Image(self.image, affine=self.get_transmat(self.elsize), dtype=dtype)
            nib.save(
                nii_img,
                outpath
            )
            
    def czi_load(self, **kwargs):
        import czifile
        self.ds=np.squeeze(czifile.imread(self.path))
        self.image=self.ds[:]
        self.dims = self.image.shape
        self.dtype = self.image.dtype
        return(self.image)
        
    def get_transmat(self, elsize=None):
        """Return a transformation matrix with scaling of elsize."""
        import numpy as np
        mat = np.eye(4)
        if elsize is not None:
            mat[0][0] = elsize[0]
            mat[1][1] = elsize[1]
            mat[2][2] = elsize[2]
        else:
            mat[0][0] = self.elsize[0]
            mat[1][1] = self.elsize[1]
            mat[2][2] = self.elsize[2]

        return mat




# folder ="/Users/samdeblank/OneDrive - Prinses Maxima Centrum/1.brain_segmentation/"
# file = "20201007_mbr26_1_b6_25x_shading_stitching_400x400x100CROP.ims"
# substruct=""
# # image_path = '/Users/samdeblank/OneDrive - Prinses Maxima Centrum/1.brain_segmentation/h5filetest.h5/memb/mean'
# # substruct ='/DataSet/ResolutionLevel 0/TimePoint 0/Channel 0'
# image_path = folder + file + substruct
# image = Image(path=image_path, permission='r+')
# image.load()
# image.list_ims_channels()
#
# image.ims_load(channel='1')
# print(image.ds)
# image.ims_remove_zeropadding()
# # WITH R+ the ims remove zeropadding is within the file!!!!!!
# image.dims
# image.ds
# image.view()
# image.close()

def save_h5_to_h5(inpath, outpath, in_substruct="", out_substruct="", remove_original=False):
    if inpath==outpath:
        permission="a"
    else:
        permission="r"
    if in_substruct:
        in_h5 = Image('{}/{}'.format(inpath, in_substruct), permission=permission)
    else:
        in_h5 = Image(inpath, permission="r")
    in_h5.load()

    # if out_substruct:
    #     out_h5 = Image('{}/{}'.format(outpath, out_substruct), permission='a')
    # else:
    #     out_h5 = Image(outpath, permission="a")
    in_h5.write(outpath=outpath, substruct=out_substruct, overwrite=True)

    if remove_original:
        in_h5.remove_group(in_substruct)

    in_h5.close()


def get_image(filepath, substruct="", channel=""):
    # print(substruct)
    channel=str(channel)
    if substruct:
        im = Image('{}/{}'.format(filepath, substruct), permission='r')
    else:
        im = Image(filepath, permission="r")
    # print(im.path)
    im.load(channel=channel)
    if im.image is None:
        sys.exit("Image was not loaded correctly. Exiting...")
    if im.format==".ims":
        im.ims_remove_zeropadding(in_place=False)
    data = im.image
    im.close()
    return data

def save_image(image, path, substruct="", metadata={}, elsize=[1,1,1], compression="gzip", **kwargs):
    path=str(path)
    im = Image(path, permission='a')
    im.write(data=image, outpath=path, substruct=substruct, metadata=metadata, elsize=elsize, overwrite=True, compression=compression, **kwargs)
    im.close()

def save_image_to_h5(image, h5_path, substruct=None, metadata={}, **kwargs):
    im = Image(h5_path, permission='a')
    im.write(data=image, outpath=h5_path, substruct=substruct, metadata=metadata, overwrite=True, **kwargs)
    im.close()

def slice_image(image, outfile=None, slices=None, xmin=None, xmax=None, ymin=None, ymax=None, zmin=None, zmax=None):
    import h5py
    import numpy as np
    if isinstance(image, np.ndarray):
        if slices:
            if len(slices)==image.ndim:
                cutout=image[slices]
            else:
                print("Dimension of slices ({}) unequal to dimensions of image ({})".format(str(len(slices)),str(image.ndim)))
                return
        elif image.ndim == 3:
            if not zmin or zmax:
                if image.shape[0]==1:
                    cutout=image[:, ymin:ymax, xmin:xmax]
                else:
                    print("Image is 3D but no zmin and/or zmax provided, taking full range")
                    cutout=image[:, ymin:ymax, xmin:xmax]
            else:
                cutout=image[zmin:zmax, ymin:ymax,xmin:xmax]
        elif image.ndim == 2:
            cutout=image[xmin:xmax, ymin:ymax]
        return(cutout)

    elif isinstance(image, str):
        if outfile is None:
            basename = image.split(".h5")[0]
            outfile = f"{basename}_cropped.h5"
        img_file=Image(image, "a")
        out_im=Image(outfile, "a")
        img = img_file.load()
        if img is None and img_file.pathparts["ext"]==".h5":
            def get_dataset_keys(f):
                keys = []
                f.visit(lambda key : keys.append(key) if isinstance(f[key], h5py.Dataset) else None)
                return keys

            channels=get_dataset_keys(img_file.file)

            for substruct in channels:
                print(f"Slicing {substruct}")
                img = img_file.load(substruct=substruct)

                if slices:
                    if len(slices)==img.ndim:
                        cutout=img[slices]
                    else:
                        print("Dimension of slices ({}) unequal to dimensions of image ({})".format(str(len(slices)),str(img.ndim)))
                        return
                elif img.ndim == 3:
                    if not zmin or zmax:
                        if img.shape[0]==1:
                            cutout=img[:, ymin:ymax, xmin:xmax]
                        else:
                            print("Image is 3D but no zmin and/or zmax provided, taking full range")
                            cutout=img[:, ymin:ymax, xmin:xmax]
                    else:
                        cutout=img[zmin:zmax, ymin:ymax,xmin:xmax]
                elif img.ndim == 2:
                    cutout=img[xmin:xmax, ymin:ymax]
                out_im.write(cutout, substruct=substruct)
        img_file.close()
        out_im.close()
    else:
        print("image is not an array or filepath. Please provide correct input")

def ims_channels_to_h5(
    ims_path,
    out_name=None,
    channels=[],
    channel_names=[],
    h5_group_names=[]
    ):

    from general_segmentation_functions.image_handling import Image, get_image
    import os
    from pathlib import Path
    ims_path=Path(ims_path)
    if os.path.exists(ims_path):
        image=Image(ims_path, 'r')
        image.load()
        ims_channels=image.ims_list_channels()

        if not h5_group_names:
            h5_group_names=["raw_channels"] * len(ims_channels)
        elif isinstance(h5_group_names, str):
            h5_group_names=[h5_group_names] * len(ims_channels)
        elif isinstance(h5_group_names, list):
            pass
        else:
            print("h5_group_names of unknown type: {}".format(type(h5_group_names)))

        print(ims_channels)
        if not channels and not channel_names:
            extract_zip=zip(ims_channels.keys(), ims_channels.values(), h5_group_names)
        elif channels and channel_names:
            extract_zip=zip(channels, channel_names, h5_group_names)
        elif channels:
            channel_names=[]
            for ch_nr in channels:
                channel_names.append(ims_channels[str(ch_nr)])
            extract_zip=zip(channels, channel_names, h5_group_names)
        elif channel_names:
            channels=[]
            for ch_name in channel_names:
                for nr, name in ims_channels.items():
                    if name==ch_name:
                        channels.append(nr)
            extract_zip=zip(channels, channel_names, h5_group_names)

        if not out_name:
            out_name=ims_path.with_suffix(".h5")

        out_image=Image(out_name, "w")
        for channel in extract_zip:
            idx=channel[0]
            name=channel[1]
            group_name=channel[2]
            print("Saving channel {}".format(str(idx)))
            ims_image = get_image(ims_path, channel=str(idx))
            group=group_name
            substruct="{}/{}".format(group, name)
            # print(out_name, substruct)
            out_image.write(data=ims_image, outpath=out_name, substruct=substruct)

        out_image.close()
        image.close()
    else:
        print(f"provided path does not exist:\n{ims_path}")

def view_napari(images=[], labels=[], names=[]):
    import napari
    import numpy as np
    viewer=napari.Viewer()
    if len(names)!=len(images) and names and images:
        print("Number of names is not equal to number of images. Using default naming")
        names=[]

    if isinstance(images, str):
        h5=Image(images, permission="a")
        h5.load()
        image=h5.image
        h5.close()
        viewer = viewer.add_image(image, name=image, scale=h5.elsize)
    elif isinstance(images, list) or isinstance(images, tuple):
        for idx, im_path in enumerate(images):
            if labels==[]:
                label = None
            else:
                label=labels[idx]
                 
            if isinstance(im_path, np.ndarray):              
                if label=="label":
                    viewer.add_labels(im_path)
                else:
                    viewer.add_image(im_path)
            else:
                print("opening:", im_path)
                h5=Image(im_path, permission="a")
                h5.load()
                # image=h5.image

                if names==[]:
                    name=im_path
                else:
                    name=names[idx]
                
                if 'image_type' in h5.ds.attrs.keys():
                    if h5.ds.attrs['image_type']=='labels':
                        viewer.add_labels(h5.image, name=name, scale=h5.elsize)
                    else:
                        viewer.add_image(h5.image, name=name, scale=h5.elsize)
                elif label=="label":
                    viewer.add_labels(h5.image, name=name, scale=h5.elsize)
                else:
                    viewer.add_image(h5.image, name=name, scale=h5.elsize)
                for lay in viewer.layers: lay.visible = False
                h5.close()
    elif isinstance(images, dict):
        for im_path, img_type in images.items():
            h5=Image(im_path, permission="a")
            h5.load()
            print("opening:", im_path)
            # if not names:
            name=im_path
            if img_type=='labels':
                viewer.add_labels(h5.image, name=name, scale=h5.elsize)
            elif img_type=='image':
                viewer.add_image(h5.image, name=name, scale=h5.elsize)
    elif isinstance(images, np.ndarray):
        if labels=="label":
            viewer.add_labels(images, name="image", scale=[1,1,1])
        else:
            viewer.add_image(images, name="image", scale=[1,1,1])
    napari.run()

def split_h5_path(path, ext=".h5"):
    file_comps={}
    file_comps['ext']=ext
    before_ext, after_ext = path.split(ext)
    file_comps['file'] = before_ext + file_comps['ext']
    file_comps['file_no_ext']= before_ext
    file_comps['folder'], file_comps['filename'] = file_comps['file'].rsplit("/", 1)
    file_comps['filename_no_ext']=file_comps['filename'].split(ext)[0]
    file_comps['folder']=file_comps['folder']+"/"
    file_comps['substruct']=None
    if after_ext!='' and after_ext!='/':
        file_comps['substruct']=after_ext
        file_comps['group'], file_comps['dataset'] = after_ext.rsplit("/", 1)
    return(file_comps)
# def channel_array_to_h5 (array):

def ims_4D_to_h5(
    ims_path,
    out_name=None,
    channel=0,
    susbtruct="/data"
    ):

    from general_segmentation_functions.image_handling import Image, get_image
    import os
    from pathlib import Path
    import numpy as np

    ims_path=Path(ims_path)

    if not out_name:
        out_name = ims_path.with_suffix(".h5")
        print(out_name)
    if os.path.exists(ims_path):
        image=Image(ims_path, 'r')
        image.load()
        full_image=None
        default_channels_path='/DataSet/ResolutionLevel 0/'
        images = []
        for timepoint in range(len(image.file[default_channels_path])):
            print(f"TimePoint {timepoint}")
            image.ims_load(substruct=f"{default_channels_path}/TimePoint {timepoint}/Channel {channel}/Data")
            image.ims_remove_zeropadding(in_place=False)
            images.append(image.image)
            # img=np.expand_dims(img, 0)
            # if full_image is None:
            #     full_image=img
            # else:
            #     full_image=np.concatenate((full_image, img))
        images=np.stack(images, axis=0)
        image.write(outpath=out_name, substruct=substruct)
        image.close()

def combine_tifs(tif_folder, prefix=""):
    from skimage import io
    import numpy as np
    from pathlib import Path
    
    tif_folder=Path(tif_folder)
    images=list(tif_folder.iterdir())
    images=[image for image in images if prefix in image.name]
    images = [io.imread(fname=img_path) for img_path in images]
    stacked_image=np.stack(images, axis=0)
        
    return stacked_image