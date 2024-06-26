# Usa una imagen base de Python
FROM python:3.8-slim

# Instala git, openmpi, gcc y otras herramientas necesarias
RUN apt-get update && \
    apt-get install -y git build-essential libopenmpi-dev && \ 
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Para instalar mpi4py en tu contenedor Docker, primero debes asegurarte
# de que se instalen las herramientas de compilación necesarias, como GCC y
#una implementación de MPI (por ejemplo, libopenmpi-dev). 

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala Jupyter Notebook y los paquetes necesarios
RUN pip install jupyter \
    git+https://github.com/miguelhroca/STAPL3D.git \
    pyqt5==5.12.3 \
    pyqtwebengine==5.12.1 \
    napari \
    mpi4py==3.0.3 \ 
    PyPDF2 \
    czifile \
    readlif \
    h5py \
    matplotlib

# Genera la configuración de Jupyter Notebook
RUN jupyter notebook --generate-config --allow-root

# Copia todos los archivos locales al contenedor en el directorio /app
COPY . .

# Expone el puerto 8888 para que Jupyter Notebook sea accesible
EXPOSE 8888

# Comando por defecto para ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
