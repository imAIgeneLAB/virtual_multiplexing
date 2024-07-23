# Usa una imagen base de Python
FROM python:3.8-slim

# Instala git, openmpi, gcc, java, maven y otras herramientas necesarias para importar repositorios de git
RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev curl unzip default-jre maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala Jupyter Notebook y los paquetes necesarios
RUN pip install --no-cache-dir \
    aicspylibczi \
    czifile \
    elasticdeform \
    git+https://github.com/josecared/STAPL3D.git \
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
 
# Descargar Fiji desde el enlace proporcionado usando curl
RUN mkdir -p /app/fiji_linux && \
    curl -L -o /tmp/fiji_linux.zip https://downloads.imagej.net/fiji/latest/fiji-linux64.zip && \
    unzip -q /tmp/fiji_linux.zip -d /app/fiji_linux && \
    rm /tmp/fiji_linux.zip

# Clona los repositorios necesarios
RUN git clone https://github.com/josecared/ZeroCode-VirtualMultiplexing && \
    git clone https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix && \
    git clone https://github.com/heeycoen/VirtualMultiplexing3D && \
    git clone https://github.com/josecared/STAPL3D && \
    git clone https://github.com/NicolasCristini/ImageJ-Processing-Assistant-Notebook

# Instala los requisitos para pytorch-CycleGAN-and-pix2pix
RUN pip install --no-cache-dir -r pytorch-CycleGAN-and-pix2pix/requirements.txt 
# Genera la configuración de Jupyter Notebook
RUN jupyter notebook --generate-config --allow-root

# Creamos carpetas 
RUN mkdir -p \
    /app/Pruebas \
    /app/Pruebas/models \
    /app/Pruebas/traintest \
    /app/Pruebas/preds \
    /app/Pruebas/unmix

# Toma la ruta /app/VirtualMultiplexing3D para ejecutar módulos personalizados
ENV PYTHONPATH /app/VirtualMultiplexing3D
ENV FIJI_PATH /fiji/ImageJ-linux64
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64
ENV PATH $JAVA_HOME/bin:$PATH

# Copia todos los archivos locales al contenedor en el directorio /app
COPY . .

# Expone el puerto 8888 para Jupyter Notebook y el 8097 para visdom 
EXPOSE 8888
EXPOSE 8097

# Comando por defecto para ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["sh", "-c", "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root & python -m visdom.server -p 8097"]

# Comando para correr docker y que lea los archivoa en D:/Escritorio/data:
# docker run -it -p 8888:8888 --name vm -v D:/Escritorio/data:/app/data vm:bigstitcher
# docker run -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:bigstitcher
# docker run --gpus all -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:bigstitcher
# docker run --gpus all -it -p 8888:8888 -p 8097:8097 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:bigstitcher

# Comando para guardar los resultados en el escritorio
# docker cp vm:/app/pruebas D:/Escritorio
# docker cp vm:/app/ C:/Users/malieva/Desktop