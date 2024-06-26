# Usa una imagen base de Python
FROM python:3.8-slim

# Instala git y otras herramientas necesarias
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala Jupyter Notebook
RUN pip install jupyter \
    git+https://github.com/miguelhroca/STAPL3D.git \
    pyqt5==5.12.3 \
    pyqtwebengine==5.12.1 \
    napari \
    mpi4py-mpich \
    PyPDF2 \
    czifile \
    readlif

# Genera la configuración de Jupyter Notebook
RUN jupyter notebook --generate-config --allow-root

# Copia todos los archivos locales al contenedor en el directorio /app
COPY . .

# Expone el puerto 8888 para que Jupyter Notebook sea accesible
EXPOSE 8888

# Comando por defecto para ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["jupyter", "notebook", "--ip='*'", "--port=8888", "--no-browser", "--allow-root"]
