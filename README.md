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

This tool is prepared to work with  (.czi, .lif. .tif, .tiff)
- modelos
- 

Important: note that, during the process, the output result won't have the metadata of the original image.

## Video-tutorial


## Getting started

![Getting started](/images/scheme_docker_installation.jpg "")

### Installing Docker Desktop

First, if you don't have a Docker account, you need to [sign up](https://app.docker.com/signup). Once you've have a Docker account, you need to [install Docker Desktop](https://www.docker.com/products/docker-desktop/) in your computer.



## Downloading Virtual Multiplexing image

Once installed, you open it, you sign in and search in the searchbar:

```jcredonava/virtual_multiplexing```

Then, you select the latest version in the 'tag' pop-up menu. Finally, click pull and wait for the image to download.

![Getting started](/images/docker_pull.png "")

## Image to container

Once the image is downloaded, you have to open your terminal and write the following command:

```docker run --gpus all -it -p 8888:8888 --name virtual_multiplexing -v [[DATA_FOLDER]] virtual_multiplexing:v1```

In ```[[DATA_FOLDER]]``` you must input the path of the directory containing all the images, models, etc . you want to work with.

Once entered, you'll see something similar to this:

![CLI](/images/cli.png "")

Now, you just have to clic on the loclahost link. And thats all! Jupyter notebook will open up, ready for you to use.

## Notebook general workflow



![General workflow](/images/steps.jpg "")


Pasos

Stitching 

Tenemos que conocer el tamano exacto de las imagens. Al hacer el tiling, es necesario que la imagen original sea cuadrada y que los tiles sean tambien cuadrados, pues el algoritmo de prediccion solamente produce como output imagenes cuasdradas ,de forma que si le damos algo diferente se recortara la imagen. Entonces, es importante conocer las dimnensiones originales de la imagen para determinar el blocksize de los tiles paraasegurar que todos son perfedctamente cuadrados. Por ejemplo, si tenemos una imagen de 4000x4000 pixeles, podemos determinar blocksizes de 2000x2000 (generando 4 tiles (2x2)), 1000x1000 (generando 16 tiles (4x4)), 500x500 (generando 64 tiles (8x8))... Si tenemos una imagen original de 3276x3276 pixeles, podemos determinar blocksizes de 1638x1638 (generando 4 tiles (2x2)), 819x819 (generando 16 tiles (4x4)), pero, por ejemplo, NO podriamos tener un blocksize de 600x600, ya que esto nos generar'ia tiles rectangulares que se procesan incorrectamente en el pipeline. Es por esta razon tambien que tampoco podemos procesar imagenes originales que no son perfectamenrte cuadradas. Por ejemplo, si nuestra imagen es de 4000x4100 p'ixlees, es conveniente recortar la imagen previamente de forma que tengamops una de 4000x4000.

El codigo funciona de la siguiente forma blablabla explicar cada parte del codigo y del widget.





## 

## Acknowledgements
Work produced with the support of 

## References
