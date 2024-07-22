File.openSequence("/app/data/gray");
run("Make Composite");
run("Image Sequence... ", "../data/composite/ format=TIFF name=composite");
selectImage("gray");
close();
run("Define dataset ...", "define_dataset=[Automatic Loader (Bioformats based)] project_filename=dataset.xml path=../ exclude=10 pattern_0=Tiles pattern_1=Channels move_tiles_to_grid_(per_angle)?=[Move Tiles to Grid (interactive)] how_to_load_images=[Re-save as multiresolution HDF5] load_raw_data_virtually dataset_save_path=../data/composite check_stack_sizes subsampling_factors=[{ {1,1,1}, {2,2,1}, {4,4,1} }] hdf5_chunk_sizes=[{ {64,64,1}, {64,64,1}, {64,64,1} }] timepoints_per_partition=1 setups_per_partition=0 use_deflate_compression");
run("BigStitcher", "select=../data/composite/dataset.xml");
saveAs("Tiff", "C:/Users/malieva/Desktop/Fused Non-rigid.tif");
