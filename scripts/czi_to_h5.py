import czifile
import h5py
import numpy as np

def czi_to_h5(input_czi_file, output_h5_file):
    # Abrir el archivo CZI
    czi = czifile.imread(input_czi_file)
    
    # Crear un archivo HDF5
    with h5py.File(output_h5_file, 'w') as h5:
        # Guardar cada canal como un dataset en el archivo HDF5
        for idx, channel_data in enumerate(czi):
            h5.create_dataset(f'channel_{idx}', data=channel_data, compression='gzip')
            
if __name__ == "__main__":
    input_czi_file = 'archivo.czi'  # Reemplaza con el nombre de tu archivo CZI
    output_h5_file = 'archivo.h5'   # Nombre de archivo HDF5 de salida
    
    czi_to_h5(input_czi_file, output_h5_file)