# Virtual Multiplexing

This is **ZeroCostDL4mic-Virtual-Multiplexing**, a tool designed to perform multiplexing (“virtual staining“) predictions on cell samples, enabling efficient analysis and interpretation of complex data without requiring advanced knowledge in bioinformatics. It supports various input formats and provides customizable settings for advanced processing.

This repository continues the work done by Ana Ballesteros (https://github.com/imAIgene-Dream3D/ZeroCode-VirtualMultiplexing).

## Overview

Virtual Multiplexing is a technique with which we are able to separate the biomarkers used in a sample into different channels (signal unmixing). Our approach is based on adversarial neural networks (cGANs) and is easily accesible for everyone, even those without computational expertise. To achieve this, it is implemented in a [Docker](https://docs.docker.com/) image, using [Jupyter](https://jupyterlab.readthedocs.io/en/latest/) notebooks. 

## How to use Virtual Multiplexing

This tool is adapted in Docker. Docker is a platform for designing and distributing applications in the form of images. A Docker image contains all the programs, packages, files, and code necessary to run our application consistently in any environment, ensuring that the application runs consistently on any computer.

![Docker scheme](/images/docker_scheme.png "https://www.geeksforgeeks.org/what-is-docker-hub/")

With our Docker image for virtual multiplexing, you'll just have to install Docker Desktop, download our image and run it to create the container. This container holds everything you need to do the analysis, without extra installation.

## What type of data does Virtual Multiplexing work with?

This tool is prepared to work with:
- Video-microscopy files (.czi, .lif. .tif, .tiff) to make predictions and train models
- pix2pix pre-trained models to use in image predictions.

Important: note that, during the process, the output result will surely miss loss the metadata of the original image.

## Video-tutorial

link

## Getting started

![Getting started](/images/scheme_docker_installation.jpg "")

### Installing Docker Desktop

First, if you don't have a Docker account, you need to [sign up](https://app.docker.com/signup). Once you've have a Docker account, you need to [install Docker Desktop](https://www.docker.com/products/docker-desktop/) in your computer.

### Downloading Virtual Multiplexing image

Once installed, you open it, you sign in and search in the searchbar:

```jcredonava/virtual_multiplexing```

Then, you select the latest version in the 'tag' pop-up menu. Finally, click pull and wait for the image to download.

![Getting started](/images/docker_pull.png "")

### Image to container

Once the image is downloaded, you have to open your terminal and write the following command:

```docker run --gpus all -it -p 8888:8888 --name virtual_multiplexing -v [[DATA_FOLDER]] virtual_multiplexing:v1```

This command launches a Docker container with GPU support for running our image:

- ```docker run```: Start a new Docker container from the downloaded image.
- ```--gpus all```: Use all available GPUs within the container to perform GPU-accelerated Virtual Multiplexing.
- ```-it```: Run the container in interactive mode, keeping the container open for input.
- ```-p 8888:8888```: Map port 8888 from inside the containe, allowing you to access the notebook in your browser via ```localhost:8888```.

- ```--name virtual_multiplexing```: Assign a name (virtual_multiplexing in this case) to the container. This name can be used later to reference or manage the container (e.g., stopping or restarting it).

- ```-v [[DATA_FOLDER]]```: The -v flag mounts a volume (a folder from the host machine) into the container. [[DATA_FOLDER]] should be replaced by the path to your data on the host machine.

- ```virtual_multiplexing:v1```: This specifies the Docker image to use for creating the container. ```virtual_multiplexing``` is the image name, and ```v1``` is the tag (version 1).

Once entered, you'll see something similar to this:

![CLI](/images/cli.png "")

Now, you just have to click on the ```localhost link```. And thats all! Jupyter lab will open up, ready for you to use!

## Notebook general workflow

![General workflow](/images/steps.jpg "")

### Importing dependencies

If the Docker image has been successfully installed, you don’t need to install anything else; everything required to use this notebook has already been set up for you. Now, simply run the dependencies cell to import all the necessary packages and get started!

### Spliting 

To ensure compatibility with the tiling process and the prediction algorithm, it's crucial to understand the characteristics of our images:

- Size: Knowing the exact dimensions of the image (height and width) is essential, especially since the images must be square for correct processing.
- Number of channels: Whether the image is in grayscale or another format influences how the data is handled and processed.

Knowing the exact dimensions of the original image is essential for determining an appropriate block size for tiling, ensuring that all tiles are perfectly square. For instance, if the image is 4000x4000 pixels, valid block sizes could be:

- 2000x2000, producing 4 tiles (2x2)
- 1000x1000, producing 16 tiles (4x4)
- 500x500, producing 64 tiles (8x8)

However, if the original image has dimensions like 3276x3276 pixels, valid block sizes could be:

- 1638x1638, producing 4 tiles (2x2)
- 819x819, producing 16 tiles (4x4)

In contrast, a block size of 600x600 pixels would be invalid since it would generate rectangular tiles, which are not processed correctly by the pipeline.

### Read and generate data

In this section, you can load your microscopy image files (.czi, .lif, .tif, and .tiff) for two different purposes, depending on the selected option:

- Data for Train/Test: This option processes your data to generate paired images suitable for training and testing a virtual multiplexing model. It prepares the images so that the model can learn to identify patterns and relationships within the data.
- Data for Predictions: This option processes data containing mixed signals and generates images that are ready to be used for predictions by the virtual multiplexing model. The model will use these images to unmix the signals and make predictions based on the data.

The preprocessing step ensures that the images are in the correct format and ready for use with the virtual multiplexing pipeline, whether for training, testing, or making predictions.

### Model training

Once you have generated the necessary data, this section allows you to proceed with the following options, depending on the selected window:

- Train from Scratch: In this option, you will configure and train a virtual multiplexing model from the beginning. You can set up the model architecture, hyperparameters, and other training configurations to start learning from your data.
- Continue Training: This option allows you to continue training an already pretrained model. You can load the model and resume training with additional data or fine-tune it based on new parameters.
- Test a Model: This option enables you to evaluate the performance of a trained model. You can test how well the model performs on unseen data and analyze its accuracy, predictions, and overall behavior.

These options provide flexibility to train and test a virtual multiplexing model tailored to your specific dataset and needs.

If you don’t need to train a model from scratch, you can find pretrained models in [this repository](https://github.com/imAIgene-Dream3D/ZeroCode-VirtualMultiplexing):

- Open Detector model: This model was trained from mixed-signal images, capturing real-world variations in the signals.
- Synthetic model (recommended): This model was trained using synthetic mixed-signal images, obtanied by combining source images in a controlled manner, we simulate realistic mixed signals.
- Weighted model: Similar to the synthetic method, this dataset also utilizes computational techniques. However, it incorporates weighted blending of the source images, allowing for the adjustment of signal intensity.

These models can be used directly for your virtual multiplexing tasks, saving you time on training and allowing you to focus on testing or making predictions with your data.

### Virtual Multiplexing

After properly generating the data and obtaining the model, you can now unmix the signals. By utilizing a pretrained model, you can efficiently handle the complexities of signal unmixing, enhancing your ability to interpret and analyze the data. This step is crucial for obtaining accurate results and insights from your microscopy images.

### Stitching

After tiling your data at the beginning of the process, it's now time to stitch the predicted data back together into a complete image. This step is crucial for reconstructing the original image from the smaller tiles that were processed individually.

## Acknowledgements
Work produced with the support of 

## References

