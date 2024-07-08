# Usa una imagen base de Python
FROM python:3.8-slim

# Instala git, openmpi, gcc y otras herramientas necesarias para importar repositorios de git
RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev && \ 
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Para instalar mpi4py en un contenedor Docker, primero debes instalar
# las herramientas de compilación necesarias, como GCC y una
# implementación de MPI (en este caso, libopenmpi-dev). 

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala Jupyter Notebook y los paquetes necesarios
RUN pip install --no-cache-dir \
    czifile \
    git+https://github.com/miguelhroca/STAPL3D.git \
    h5py==2.10.0 \
    ipython \
    ipywidgets \
    jupyter \
    matplotlib \
    mpi4py==3.0.3 \
    napari \
    nibabel \
    numpy==1.19.5 \
    opencv-python-headless \
    pillow \
    PyPDF2 \
    pyqt5==5.12.3 \
    pyqtwebengine==5.12.1 \
    pyvista \
    readlif \
    scikit-image \
    scipy \
    tensorboardX \
    tensorflow-gpu==2.2.0 \
    torch>=0.4.0 \
    torchvision \
    visdom \
    tensorflow-addons \
    elasticdeform \
    scikit-learn 


# --no-cache-dir en pip install evita que pip almacene en caché los archivos de instalación
# lo que puede reducir el espacio en disco utilizado por el contenedor Docker.

# pillow es reemplazo de PIL

# pyvista for visulization

# Clona los repositorios necesarios
RUN git clone https://github.com/akabago/ZeroCostDL4Mic-VirtualMultiplexing.git && \
    git clone https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix && \
    git clone https://github.com/heeycoen/VirtualMultiplexing3D

# Run training job: python train.py --dataset <your dataset name>

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

# Copia todos los archivos locales al contenedor en el directorio /app
COPY . .

# Expone el puerto 8888 para que Jupyter Notebook sea accesible y el 8097 para que visdom 
EXPOSE 8888
EXPOSE 8097


# Comando por defecto para ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["sh", "-c", "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root & python -m visdom.server -p 8097"]

# Comando para correr docker y que lea los archivoa en D:/Escritorio/data:
# docker run -it -p 8888:8888 --name vm -v D:/Escritorio/data:/app/data vm:vox2vox
# docker run -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:vox2vox
# docker run --gpus all -it -p 8888:8888 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:vox2vox
# docker run --gpus all -it -p 8888:8888 -p 8097:8097 --name vm -v C:/Users/malieva/Desktop/data:/app/data vm:vox2vox

# Comando para guardar los resultados en el escritorio
# docker cp vm:/app/pruebas D:/Escritorio
# docker cp vm:/app/ C:/Users/malieva/Desktop