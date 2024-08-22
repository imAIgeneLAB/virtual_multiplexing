# Use a base image with Python
FROM python:3.8-slim

# Install git, openmpi, gcc, java, maven, and other necessary tools for importing git repositories
RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev curl unzip maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Install Jupyter Notebook and the required packages
RUN pip install --no-cache-dir \
    aicspylibczi \
    ashlar \
    czifile \
    elasticdeform \
    h5py==2.10.0 \
    ipython \
    ipywidgets \
    jupyter \
    matplotlib \
    mpi4py==3.0.3 \
    napari \
    natsort \
    nibabel \
    numpy==1.19.5 \
    opencv-python-headless \
    pillow \
    pyimagej \
    PyPDF2 \
    pyqt5==5.12.3 \
    pyqtwebengine==5.12.1 \
    pyvista \
    pyyaml \
    read_lif \
    readlif \
    scikit-image \
    scikit-learn \
    scipy \
    tensorboard \
    tensorflow-addons \
    tensorflow \
    tifffile \
    torch>=0.4.0 \
    torchvision \
    visdom \
    wandb

# Clone necessary repositories
RUN git clone https://github.com/josecared/ZeroCode-VirtualMultiplexing && \
    git clone https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix && \
    git clone https://github.com/heeycoen/VirtualMultiplexing3D && \
    git clone https://github.com/josecared/STAPL3D

# Install requirements for pytorch-CycleGAN-and-pix2pix
RUN pip install --no-cache-dir -r pytorch-CycleGAN-and-pix2pix/requirements.txt 

# Generate Jupyter Notebook configuration
RUN jupyter notebook --generate-config --allow-root

# Create directories
RUN mkdir -p \
    /app/Testing \
    /app/Testing/models \
    /app/Testing/traintest \
    /app/Testing/preds \
    /app/Testing/unmix 

# Set the PYTHONPATH environment variable to include the VirtualMultiplexing3D directory
ENV PYTHONPATH /app/VirtualMultiplexing3D

# Copy all local files to the /app directory in the container
COPY . .

# Expose port 8888 for Jupyter Notebook and port 8097 for visdom
EXPOSE 8888
EXPOSE 8097

# Default command to run Jupyter Notebook and visdom server when the container starts
CMD ["sh", "-c", "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root & python -m visdom.server -p 8097"]

# Commands to run the Docker container and mount local directories:
# docker run -it -p 8888:8888 --name vm -v D:/Desktop/data:/app/data vm:imp
# docker run -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:imp
# docker run --gpus all -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:imp
# docker run --gpus all -it -p 8888:8888 -p 8097:8097 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:imp

# Commands to copy results from the container to the desktop:
# docker cp vm:/app/ D:/Desktop
# docker cp vm:/app/ C:/Users/malieva/Desktop