from general_segmentation_functions.image_handling import Image, get_image, view_napari
from pathlib import Path
import argparse
import h5py

parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(description='Input parameters for automatic data transfer.')
parser.add_argument('-f', '--file', type=str, help='input file', required=True)
parser.add_argument('-s', '--substruct', type=str, nargs="*", help='h5 substructs to load')
parser.add_argument('-g', '--group', type=str, default="/", help='group in which to display everything')
parser.add_argument('-a', '--all', action='store_true', help='view all files in file', required=False)
parser.add_argument('--as_segments', action='store_true', help='view all files in file', required=False)

args = parser.parse_args()


h5_base=Path(args.file)
# h5_base="/Users/samdeblank/Documents/1.projects/LSD_LandscapeStimulatedDynamics/Ilastik_and_TrackMate/00.tif"
h5=Image(h5_base, permission="r")
h5.load()

if h5.format==".h5":
    if args.all:
        channels = h5.get_all_datasets()
        labels=["label" if "label" in x or "segment" in x else "image" for x in channels]
        print(labels)
        h5.view(images=channels, labels=labels, elsize=[1.2,0.3,0.3])
    elif h5.ds != None:
        print("ADASD")
        h5.view()
    elif args.substruct:
        h5.view(images=channels, substruct=args.substruct, elsize=[1.2,0.3,0.3])
    else:
        grp=args.group
        channels=[grp+"/"+dataset for dataset in list(h5.file[grp].keys()) if isinstance(h5.file[grp+"/"+dataset], h5py.Dataset)]
        print(channels)
        labels=["label" if "label" in x or "segment" in x else "image" for x in channels]
        print(labels)
        h5.view(images=channels, labels=labels, elsize=[1.2,0.3,0.3])
    h5.close()
else:
    if args.as_segments:
        h5.view(labels="label", elsize=[1.2,0.3,0.3])
    else:
        h5.view(elsize=[1.2,0.3,0.3])
    
# h5_base="/Users/samdeblank/Documents/1.projects/brain_segmentation/coregistration/coregistered_h5/20210416_MBR26_B16_zstack_pair5.h5"
# h5=Image(h5_base, permission="r")
# h5.load()
# grp='/dapi'
# channels=[grp+"/"+dataset for dataset in list(h5.file[grp].keys())]
# h5.view(images=channels)
