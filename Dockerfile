FROM python:3.8-slim

RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev curl unzip maven cmake && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    numpy==1.19.5 \
    h5py==2.10.0 \
    ipython \
    ipywidgets \
    jupyter \
    matplotlib \
    mpi4py==3.0.3 \
    natsort \
    nibabel \
    pillow \
    PyPDF2 \
    pyyaml \
    scikit-image \
    scikit-learn \
    scipy \
    tensorboard \
    tifffile \
    visdom \
    wandb

RUN pip install --no-cache-dir \
    aicspylibczi \
    ashlar \
    czifile \
    elasticdeform \
    read_lif \
    readlif

RUN pip install --no-cache-dir \
    napari \
    pyqt5==5.12.3 \
    pyqtwebengine==5.12.1 \
    pyvista \
    opencv-python-headless

RUN pip install --no-cache-dir \
    tensorflow==2.10.1 \
    tensorflow-addons==0.18.0 \
    torch>=0.4.0 \
    torchvision

RUN pip install --no-cache-dir \
    numpy==1.22 \
    h5py==3.1.0 \
    flameplot \
    umap-learn \
    d3blocks \
    plotly

RUN git clone https://github.com/josecared/ZeroCode-VirtualMultiplexing

RUN git clone https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix && \
    cd pytorch-CycleGAN-and-pix2pix && \
    git checkout bd893b38d158d0b663321052c24dc1f4acccf552

RUN git clone https://github.com/heeycoen/VirtualMultiplexing3D && \
    git clone https://github.com/josecared/STAPL3D

RUN pip install --no-cache-dir -r pytorch-CycleGAN-and-pix2pix/requirements.txt 

RUN jupyter notebook --generate-config --allow-root

ENV PYTHONPATH /app/VirtualMultiplexing3D

COPY . .

EXPOSE 8888
EXPOSE 8097

CMD ["sh", "-c", "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root & python -m visdom.server -p 8097"]