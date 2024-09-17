# Virtual Multiplexing

## Overview

This repository continues the work done by Ana Ballesteros (https://github.com/imAIgene-Dream3D/ZeroCode-VirtualMultiplexing).

In this repository we present Virtual Multiplexing (“virtual dyeing”), a technique based on adversarial neural networks (cGANs) with which we are able to separate the biomarkers used in a sample into different channels (signal unmixing). This tool is easily accesible for everyone, even those without computartional expertise. For that, it is implemented in a [Docker](https://docs.docker.com/) image, using [Jupyter](https://jupyterlab.readthedocs.io/en/latest/) notebooks. 

## How to use Virtual Multiplexing

This tool is adapted in Docker. Docker is a platform for designing and distributing applications in the form of images. A Docker image contains all the programs, packages, files, and code necessary to run our application consistently in any environment, ensuring that the application runs consistently on any computer.

![Docker scheme](/images/docker_scheme.png "https://www.geeksforgeeks.org/what-is-docker-hub/")

### Installing Docker

Primero instalas [Docker Desktop](https://www.docker.com/products/docker-desktop/).

### Downloading Virtual Multiplexing image

Luego vas al buscador de docker y pones XXXXXXXXX

### Image to container

Vas al CLI de Docker y ejecutas el siguiente comando:

```docker run --gpus all -it -p 8888:8888 --name XXXXXXX -v [[Carpeta con tus datos]] vm:imp```

### Running container

Más o menos como en el rep de Ana

### User general workflow

![General workflow](/images/scheme.jpg "")

![General workflow](/images/steps.jpg "")



## 

## Acknowledgements
Work produced with the support of 

## References
