# Python base image
FROM python:3.8-slim

# Git, openmpi, gcc, java, maven & more tools
RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev curl unzip maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Jupyter Notebook & packages
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

# Morphometric analysis
RUN pip install --no-cache-dir \
    numpy==1.22 \
    h5py==3.1.0 \
    flameplot \
    umap-learn \
    d3blocks \
    plotly

# Git cloning
RUN git clone https://github.com/josecared/ZeroCode-VirtualMultiplexing && \
    git clone https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix && \
    git clone https://github.com/heeycoen/VirtualMultiplexing3D && \
    git clone https://github.com/josecared/STAPL3D

# pytorch-CycleGAN-and-pix2pix requirements
RUN pip install --no-cache-dir -r pytorch-CycleGAN-and-pix2pix/requirements.txt 

# Jupyter Notebook config
RUN jupyter notebook --generate-config --allow-root

# Toma la ruta /app/VirtualMultiplexing3D para ejecutar módulos personalizados
ENV PYTHONPATH /app/VirtualMultiplexing3D

# Copy local files to /app
COPY . .

# Open 8888 port for Jupyter Notebook and 8097 for visdom 
EXPOSE 8888
EXPOSE 8097

# Execute Jupyter Notebook
CMD ["sh", "-c", "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root & python -m visdom.server -p 8097"]

# Comando para correr docker y que lea los archivoa en D:/Escritorio/data:
# docker run -it -p 8888:8888 --name vm -v D:/Escritorio/data:/app/data vm:morph
# docker run -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:morph
# docker run --gpus all -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:morph
# docker run --gpus all -it -p 8888:8888 -p 8097:8097 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:morph

# Comando para guardar los resultados en el escritorio
# docker cp vm:/app/ D:/Escritorio
# docker cp vm:/app/ C:/Users/malieva/Desktop