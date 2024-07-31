# Installation
```
mamba create -n zipping python=3.10
pip install <Zipping_folder>/
```

For linux:

```
pip install tensorflow[and-cuda] (for linux)
```


For Windows:
```
mamba install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0
pip install "tensorflow<2.11" (for Windows)
```

Download RDCnet from: [https://github.com/fmi-basel/RDCNet](https://github.com/fmi-basel/RDCNet)

Install RDCnet
```
pip install <rdcnet_fodler>/
```


# Running

Run the OrganoidSegmentation.ipynb notebook
(RDCnet only works with GPU at the moment)

Testdata can be found on the Isilon:

/data/groups/pmc_rios/6.archive/left_colleagues/internships/CK1_CoenKenter/CK1_SegmentationModel/1.data/

Input:
- Image (.tiff) of organoids with all channels summed (With some models, only EFluor is used)
- RDCnet model
- Parameters on parallelization (# processes, blocksizes)