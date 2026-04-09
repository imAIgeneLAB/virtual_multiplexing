# Zero Code Virtual-Multiplexing

Welcome to the **Zero Code Virtual-Multiplexing tool**, designed to perform multiplexing (“virtual staining”) predictions on cell samples. It enables efficient analysis and interpretation of complex data without requiring advanced bioinformatics knowledge. 

- **Easy-to-use**
- **Supports multiple input formats**
- **Customizable settings for advanced processing**

## Overview

**Virtual Multiplexing** is a technique used to separate biomarkers in a sample into different channels (signal unmixing). Our approach is based on **adversarial neural networks (cGANs)**, making it easily accessible for users, even those without computational expertise. 

Key features:
- Integrated with [**Docker**](https://docs.docker.com/)
- Available through [**Jupyter notebooks**](https://jupyterlab.readthedocs.io/en/latest/)
- Perfect for signal unmixing in microscopy files

## How to use Virtual Multiplexing

This tool is integrated into **Docker**, a platform for designing and distributing applications in the form of images. A Docker image contains all the programs, packages, files, and code necessary to run our application consistently in any environment.

> **Note:** With **Docker** you can ensure that the application runs smoothly on any computer, regardless of its configuration.

![Docker scheme](/images/docker_scheme.png "https://www.geeksforgeeks.org/what-is-docker-hub/")

### Steps:

1. **Install Docker Desktop**.
2. **Download** our image.
3. **Run the container** to start the analysis with no additional installation.

The container holds everything you need to perform the analysis seamlessly.

## What type of data does Virtual Multiplexing work with?

This tool is designed to work with:

- **Video-microscopy files** (`.czi`, `.lif`, `.tif`, `.tiff`) for predictions and model training.
- **pix2pix pre-trained models** for image predictions.

> **Important** The output will likely lose the metadata from the original image.

## Data and Models for Evaluation

To facilitate the evaluation of this work by the thesis committee, a set of
pre-trained models, example input images and test data are available at the
following link:

**Google Drive repository**:  
https://drive.google.com/drive/folders/19SEpX16FtHxiKYLkqz9TJ-Z__RvP5tCd?usp=sharing

The folder includes:
- Example microscopy images (`.czi`, `.lif`, `.tif`)
- Pre-trained pix2pix models (`.pth`)

## Getting started

![Getting started](/images/scheme_docker_installation.jpg "")

### Installing Docker Desktop

If you don't have a Docker account yet, you need to [**sign up**](https://app.docker.com/signup). After that, follow the instructions to [**install Docker Desktop**](https://www.docker.com/products/docker-desktop) on your computer.

### Downloading the Virtual Multiplexing image

Once Docker is installed, follow these steps:

1. **Open Docker**, sign in, and use the search bar to find:

    ```bash
    jcredonava/virtual_multiplexing
    ```

2. Select the **latest version** in the 'tag' pop-up menu.
3. Click **pull** and wait for the image to download.

![Getting started](/images/docker_pull.png "")

### Image to container

Once the image is downloaded, you have to open your terminal and write the following command:

```bash
docker run -it -p 8888:8888 --name virtual_multiplexing -v [[PARENT_FOLDER]] jcredonava/virtual_multiplexing:v1
```

This command launches a Docker container with GPU support for running our image:

- ```docker run```: Start a new Docker container from the downloaded image.
- ```--gpus all```: OPTIONAL: Use all available GPUs within the container to perform GPU-accelerated Virtual Multiplexing.
- ```-it```: Run the container in interactive mode, keeping the container open for input.
- ```-p 8888:8888```: Map port 8888 from inside the container, allowing you to access the notebook in your browser via ```localhost:8888```.

- ```--name virtual_multiplexing```: Assign a name (virtual_multiplexing in this case) to the container. This name can be used later to reference or manage the container (e.g., stopping or restarting it).

- ```-v [[PARENT_FOLDER]]```: The -v flag mounts a volume (a folder from the host machine) into the container. ```[[PARENT_FOLDER]]``` should be replaced by the path to your data on your PC.

- ```jcredonava/virtual_multiplexing:v1```: This specifies the Docker image to use for creating the container. ```jcredonava/virtual_multiplexing``` is the image name, and ```v1``` is the tag (version 1).

Once entered, you'll see something similar to this:

![CLI](/images/cli.png "")

Now, you just have to click on the ```localhost link```. And that's all! Jupyter lab will open up, ready for you to use!

## Notebook General Workflow

Virtual Multiplexing is divided into two main modules:

- **Model Generation**: Starting from video-microscopy files (`.czi`, `.lif`, `.tif`, or `.tiff`), Virtual Multiplexing can train models and use them for signal unmixing.
- **Signal Unmixing**: Using a pre-trained model (either from the model generation step or another source), Virtual Multiplexing can unmix signals from a mixed-channel image, differentiating subcellular structures with different colors (e.g., red nuclei, green cytoplasm, and membrane).

> **Important**: The output may miss the metadata of the original image during processing.

![General workflow](/images/steps.jpg "")

### Importing Dependencies

If the Docker image has been successfully installed, no further installations are needed. Everything required to use this notebook is already set up. Simply run all the cell blocks, and you’ll be ready to go! Let’s explore each module step-by-step.

> **Note**: Each block has a help button that explains the parameters needed to run each step.

### Splitting

To ensure compatibility with the tiling process and prediction algorithm, it’s crucial to understand the characteristics of your images:

- **Size**: Knowing the exact dimensions (height and width) is essential, as the images must be square for correct processing.
- **Number of Channels**: The image format (grayscale, etc.) affects how data is handled.


> **Example**: if the image is **4000x4000 pixels**, valid block sizes could be:
> 
> - **2000x2000**: Producing 4 tiles (2x2)
> - **1000x1000**: Producing 16 tiles (4x4)
> - **500x500**: Producing 64 tiles (8x8)
> 
> However, for an image with dimensions like **3276x3276 pixels**, valid block sizes could be:
> 
> - **1638x1638**: Producing 4 tiles (2x2)
> - **819x819**: Producing 16 tiles (4x4)
> 
> **Important**: In this example, a block size of **600x600 pixels** would be invalid, as it would create rectangular tiles, which cannot be processed correctly by the pipeline.

### Read and generate data

In this section, you can load your microscopy image files (`.czi`, `.lif`, `.tif`, `.tiff`) for two different purposes:

- **Data for Train/Test**: Prepares paired images suitable for training and testing a virtual multiplexing model.
- **Data for Predictions**: Processes mixed signals and generates images ready for predictions by the virtual multiplexing model.

The preprocessing step ensures the images are in the correct format for the virtual multiplexing pipeline, whether for training, testing, or making predictions.

### Model training

Once you have the necessary data, you can proceed with the following options:

- **Train from Scratch**: Configure and train a virtual multiplexing model from the beginning, setting up the architecture, hyperparameters, and other training configurations.
- **Continue Training**: Resume training an already pre-trained model with additional data or new parameters.
- **Test a Model**: Evaluate the performance of a trained model on unseen data, analyzing its accuracy and predictions.

These options provide flexibility for training and testing your virtual multiplexing model tailored to your dataset.

For those who don’t need to train a model from scratch, you can find pre-trained models in [**this repository**](https://github.com/imAIgene-Dream3D/ZeroCode-VirtualMultiplexing?tab=readme-ov-file#models):

- **Open Detector model**: Trained from mixed-signal images, capturing real-world variations.
- **Synthetic model (recommended)**: Trained using synthetic mixed-signal images, simulating realistic mixed signals.
- **Weighted model**: Utilizes weighted blending of source images for signal intensity adjustment.

These models can be directly applied to your virtual multiplexing tasks, saving time on training.

### Signal unmixing

After generating your data and obtaining the model, you can **effectively unmix the signals**. Utilizing a **pre-trained model** helps you navigate the complexities of signal unmixing, enhancing your data analysis.

- **Use your own pre-trained model** or download one suitable for unmixing signals.
- After predictions, you can **preview the results**.
- You also have the option to **separate RGB channels** into individual files for further analysis.

### Stitching

If you used tiled data, it's time to **stitch the predicted data back** into a complete image. This step is vital for reconstructing the original image from the smaller tiles processed individually.

To do this, you need to know:

- **Tile size**: The dimensions in pixels of each individual tile.
- **Number of tiles**: The arrangement of tiles (e.g., 2x2, 4x4, etc.).

## Acknowledgements

This repository builds upon the work done by Ana Ballesteros: [**ZeroCode-VirtualMultiplexing**](https://github.com/imAIgene-Dream3D/ZeroCode-VirtualMultiplexing).

Also, our tool uses work published on the following repositories by **Coen** ([**VirtualMultiplexing3D**](https://github.com/heeycoen/VirtualMultiplexing3D)), **Sam de Blank** ([**Zipping**](https://github.com/Dream3DLab/Zipping)) and **Rios Group** ([**STAPL3D**](https://github.com/RiosGroup/STAPL3D)).


## References

- Isola, P. et al. (2016). Image-to-Image Translation with Conditional Adversarial Networks. arXiv (Cornell University). [https://doi.org/10.48550/arxiv.1611.07004](https://doi.org/10.48550/arxiv.1611.07004)

- Von Chamier, L. et al. (2021). Democratizing deep learning for microscopy with ZeroCostDL4Mic. Nature Communications, 12(1). [https://doi.org/10.1038/s41467-021-22518-0](https://doi.org/10.1038/s41467-021-22518-0)