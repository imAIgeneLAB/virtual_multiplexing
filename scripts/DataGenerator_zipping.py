"""
Modified on Thu april 18 2023

@author: Ana Ballesteros and Jose Carlos Redondo

Functions: 
Reads in an .czi or .lif file and generates datasets according to the parameter provided

"""

import numpy as np
import sys
sys.path.append('/app/STAPL3D')

from stapl3d.preprocessing import shading
import matplotlib.pyplot as plt
import argparse
from matplotlib import pyplot as plt
import matplotlib
import random
import os
import cv2
from PIL import Image, ImageEnhance
from skimage import io
from skimage import color
from skimage import exposure
from readlif.reader import LifFile
import tifffile
from natsort import natsorted
import shutil
from tifffile import TiffFile



#Function increases/decreases randomly the brightness of the passed imaged based on a distribution of values passed as a list
def BrightnessAugmentation(image,brightnesslist):
    image = np.array(image)
    brightness = random.sample(brightnesslist, 1)
    print(brightness)
    # print(brightness)
    pilOutput = Image.fromarray(image)
    enhancer = ImageEnhance.Brightness(pilOutput)
    output = enhancer.enhance(brightness[0])

    augmented_image = np.array(output)

    return(augmented_image)

#FOR TRAINING AND TESTING A MODEL
#Function extracts patch, normalizes it based on percentile value of each channel, and creates syntheic data, returning concatenated AB images representing the source and target image.
def get_patch_train(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,normalization,Brightness,filepath):
    
    #Generate brightness range list for data augmentation
    #Hard coded the range of brightness. a value of 1 the yields no change. Lower than 1, image gets darger. Higher than 1, image gets brighter.
    # Lower bound is 0.5 and upper bound is 3.
    brightnessRange = [0.5,3]

    if filepath.endswith('.lif'):
        l_br = int(brightnessRange[0] * 100)
        u_br = int(brightnessRange[1] * 100)
        brightnesslist = [round(x * 0.01, 2) for x in range(l_br, u_br, 1)]

    else:
        #generating a list containing values between 0.5 and 3 with steps of 0.01 representing brightness degrees that will be sampled for introducing brightness. 
        l = int(brightnessRange[0] * 100)
        u = int(brightnessRange[1]*100)
        brightnesslist = [round(x*0.01,2) for x in range(l,u,1)]
  
    #setting arguments to integers
    uby = int(uby)
    ubx = int(ubx)
    #alpha value for membrane channel
    if alpha:
        alpha2 = round(1-alpha,2)


    #----------****GETTING COORDINATES FOR PATCH EXTRACTION****----------
    #get random ij position point in the tile image. 
    #uby "upper bound y" and ubx "upper bound x" are limits of the y and x axis in the image in order to avoid slecting an area where a patch falls outside of the image range.
    i_idx = random.randint(0,uby)
    j_idx = random.randint(0,ubx)
    #Each list contains two indices selecting a range in the corresponding axis starting from the "i or j"th point up to the lenght of a patch size i.e 512
    yax = [i_idx, (i_idx+patchsize)]
    xax = [j_idx, (j_idx+patchsize)]

    #Generates a random number representing a random selection of a layer (all layers are considered here)
    rl = random.randint(0,l-1)

    
    #----------****EXTRACTING PATCHES****----------
    #List containing normalized patch from all three channels
    channel_normalized_patches_list = []

    if filepath.endswith('.lif'):
        
        for c in range(len(channels)):
        # Extracting the patch from channel "c" from the layer "rl" of the stack
            patch = channel_stacks[c][rl, yax[0]:yax[1], xax[0]:xax[1]]
    
            if normalization == "ac":
                # Normalizing the patch using the percentile of the current channel "c"
                normalized_patch = (patch / percentiles[c]) * 255
    
            if normalization == "od":
                # Normalizing the patch using the highest percentile (open detector channel percentile)
                normalized_patch = (patch / percentiles[2]) * 255
    
            # Clipping the values, anything higher than 255 is set to 255
            normalized_patch[normalized_patch > 255] = 255
            # Adding the normalized patch of current channel "c" to the list which collects all 3 channels
            channel_normalized_patches_list.append(normalized_patch)
        
    else:
    
        #For each channel, get the patch using the indices in the yax and xax lists
        for c in range(channels):
            #extracting the patch from channel "c" from the layer "rl" of the stack 
            patch = channel_stacks[c][rl, yax[0]:yax[1],xax[0]:xax[1]]
            
            if normalization == "ac":
                # Normalizing the patch using the percentile of the current channel "c"
                normalized_patch = (patch/percentiles[c])*255         
    
            if normalization == "od":
                # Normalizing the patch using the highest percentile (open detector channel percentile)
                normalized_patch = (patch/percentiles[2])*255     
    
            # Clipping the values, anything higher than 255 is set to 255
            normalized_patch[normalized_patch> 255] = 255
            #Adding the normalized patch of current channel "c" to the list which collects all 3 channels. 
            channel_normalized_patches_list.append(normalized_patch)
        
    
    #Empty 3 channel RGB array for source image
    source_image = np.zeros((patchsize, patchsize,3))
        
        
    if mode == "synthetic":
        #Creating the synthetic patch by taking the mean value of the nuclear and membrane channel 
        synthetic_patch = (channel_normalized_patches_list[0]+channel_normalized_patches_list[1])/2
        synthetic_patch = synthetic_patch.astype(np.uint8)

        #Introducing the Synthetic patch in each channel of the source image (RGB) # Dejar aqui solo el canal 3 
        source_image[:,:,0] = synthetic_patch.astype(np.uint8)
        source_image[:,:,1] = synthetic_patch.astype(np.uint8)
        source_image[:,:,2] = synthetic_patch.astype(np.uint8)

    elif mode == "weighted":
        #Creating the synthetic weighted blended patch by taking the mean value of the nuclear and membrane channel blended with alpha and 1-alpha
        synthetic_patch = cv2.addWeighted(channel_normalized_patches_list[0], alpha2, channel_normalized_patches_list[1],alpha, 0)
        synthetic_patch = synthetic_patch.astype(np.uint8)

        #Introducing the Synthetic patch in each channel of the source image (RGB) # dejar aqui el canal 3
        source_image[:,:,0] = synthetic_patch.astype(np.uint8)
        source_image[:,:,1] = synthetic_patch.astype(np.uint8)
        source_image[:,:,2] = synthetic_patch.astype(np.uint8)

    elif mode == "open_detector":
        #Introducing the Real patch in each channel of the source image (RGB) # dejar aqui solo el canal 3
        source_image[:,:,0] = channel_normalized_patches_list[2].astype(np.uint8)
        source_image[:,:,1] = channel_normalized_patches_list[2].astype(np.uint8)
        source_image[:,:,2] = channel_normalized_patches_list[2].astype(np.uint8)

    if Brightness:
            #Enhancing brightness of source image 
        if random.randint(0,100) < int(Brightness):
            source_image = BrightnessAugmentation(source_image.astype(np.uint8),brightnesslist)
        else:
            source_image = source_image.astype(np.uint8)

    #----------****CREATING TARGET IMAGE****----------   ESTO CREO QUE TENGO QUE QUITARLO PORQUE ES EL TARGET IMAGE Y NO SE CREARIA 
    #Empty 3 channel RGB array for target image
    target_image = np.zeros((patchsize, patchsize,3))

    #Introducing the nuclear channel in the Red channel and membrane in the Green channel
    target_image[:,:,0] = channel_normalized_patches_list[1].astype(np.uint8)
    target_image[:,:,1] = channel_normalized_patches_list[0].astype(np.uint8)

    #Concatenating the source and the target image to get the AB format for pix2pix
    image_AB = np.concatenate([source_image, target_image], 1)

    #Return the concatenated AB image
    return(image_AB)

#FOR MAKING PREDICTIONS
#Function extracts patch, normalizes it based on percentile value of each channel, and creates syntheic data, returning concatenated AB images representing the source and target image.

def get_patch_predict(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,normalization,Brightness,individual_image):
    individual_image = int(individual_image)
    #Generate brightness range list for data augmentation
    #Hard coded the range of brightness. a value of 1 the yields no change. Lower than 1, image gets darger. Higher than 1, image gets brighter.
    # Lower bound is 0.5 and upper bound is 3.
    brightnessRange = [0.5,3]
    #generating a list containing values between 0.5 and 3 with steps of 0.01 representing brightness degrees that will be sampled for introducing brightness. 
    l = int(brightnessRange[0] * 100)
    u = int(brightnessRange[1]*100)
    brightnesslist = [round(x*0.01,2) for x in range(l,u,1)]
  
    #setting arguments to integers
    uby = int(uby)
    ubx = int(ubx)
    #alpha value for membrane channel
    if alpha:
        alpha2 = round(1-alpha,2)

    
    #----------****GETTING COORDINATES FOR PATCH EXTRACTION****----------
    #get random ij position point in the tile image. 
    #uby "upper bound y" and ubx "upper bound x" are limits of the y and x axis in the image in order to avoid slecting an area where a patch falls outside of the image range.
    
    i_idx = 0
    j_idx = 0

    #Each list contains two indices selecting a range in the corresponding axis starting from the "i or j"th point up to the lenght of a patch size i.e 512
    yax = [i_idx, (i_idx+patchsize)]
    xax = [j_idx, (j_idx+patchsize)]

    #Generates a random number representing a random selection of a layer (all layers are considered here)
    #rl = random.randint(0,l-1)
    rl = individual_image
    
    #----------****EXTRACTING PATCHES****----------
    #List containing normalized patch from all three channels
    channel_normalized_patches_list = []

    #For each channel, get the patch using the indices in the yax and xax lists
    for c in range(channels):
        #extracting the patch from channel "c" from the layer "rl" of the stack 
        patch = channel_stacks[c][rl, yax[0]:yax[1],xax[0]:xax[1]]
        if normalization == "ac":
            # Normalizing the patch using the percentile of the current channel "c"
            normalized_patch = (patch/percentiles[c])*255            

        # Clipping the values, anything higher than 255 is set to 255
        normalized_patch[normalized_patch> 255] = 255
        #Adding the normalized patch of current channel "c" to the list which collects all 3 channels. 
        channel_normalized_patches_list.append(normalized_patch)
    
    
    #Empty 3 channel RGB array for source image
    source_image = np.zeros((patchsize, patchsize,3))
    if mode == "open_detector":
        #Introducing the Real patch in each channel of the source image (RGB) # dejar aqui solo el canal 3
        source_image[:,:,0] = channel_normalized_patches_list[0].astype(np.uint8)
        source_image[:,:,1] = channel_normalized_patches_list[0].astype(np.uint8)
        source_image[:,:,2] = channel_normalized_patches_list[0].astype(np.uint8)
    
    if Brightness:
            #Enhancing brightness of source image 
        if random.randint(0,100) < int(Brightness):
            source_image = BrightnessAugmentation(source_image.astype(np.uint8),brightnesslist)
        else:
            source_image = source_image.astype(np.uint8)

    image_AB = source_image
    #Return the AB image
    return(image_AB)


# ----------------------------------------------------------------------------------
# ------------------------------ .LIF FILE MANAGEMENT ------------------------------
# ----------------------------------------------------------------------------------

# Dir creation (if doesnt exist)
def create_directories(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    for subdir in ["train", "test", "val"]:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)

# Percentiles per channel
def calculate_percentiles(filepaths, l_layer, u_layer, percentile):
    channel_stacks = []
    percentiles = []
    
    for filepath in filepaths:
        tmp_channel_stacked_planes = []
        for layer in range(l_layer, u_layer):
            data = tifffile.imread(filepath)[layer, :, :]
            tmp_channel_stacked_planes.append(data)
        
        planes_stacked = np.stack(tmp_channel_stacked_planes, axis=0)
        channel_stacks.append(planes_stacked)
        flat_stacked_planes = planes_stacked.flatten()
        p_val = np.percentile(flat_stacked_planes, percentile)
        percentiles.append(p_val)
    
    return channel_stacks, percentiles

# Extract and save train, test and validation patches
def extract_and_save_patches(datafoldername, t_train, t_test, t_val, patchsize, channels, channel_stacks, percentiles, mode, alpha, Norm, Brightness, filepath):
    dimensions = channel_stacks[0].shape
    l = dimensions[0]
    y = dimensions[1]
    x = dimensions[2]
    ubx = x - patchsize
    uby = y - patchsize

    for phase, count in zip(['train', 'test', 'val'], [t_train, t_test, t_val]):
        for t in range(count):
            image_AB = get_patch_train(l, uby, ubx, patchsize, channels, channel_stacks, percentiles, mode, alpha, Norm, Brightness, filepath)
            filename = f"{datafoldername}/{phase}/{t}.png"
            matplotlib.image.imsave(filename, image_AB.astype(np.uint8))

# Ext
def process_channel_to_tiff(series, channel_idx, num_frames, ruta_base, sample_name):
    """
    Process a channel from a series and saves the images in a multipage TIFF file.

    Args:
        series (LifSeries): Series to process.
        channel_idx (int): Index of the channel to process.
        num_frames (int): Number of frames to process.
        ruta_base (str): Base path to save the files.
        sample_name (str): Name of the channel.

    Returns:
        str: Path to the created multipage TIFF file.
    """
    ruta_carpeta = os.path.join(ruta_base, sample_name)

    if not os.path.exists(ruta_carpeta):
        os.makedirs(ruta_carpeta)

    # Guardar cada capa como un archivo TIFF separado
    for i in range(num_frames):
        chosen = series.get_frame(c=channel_idx, z=i)
        tifffile.imwrite(f'{ruta_carpeta}/{sample_name}_{i}.tiff', chosen)

    # Obtener una lista de todos los archivos TIFF en la carpeta
    tiff_files = [f for f in os.listdir(ruta_carpeta) if f.endswith('.tiff') or f.endswith('.tif')]

    # Ordenar la lista de archivos si es necesario
    tiff_files = natsorted(tiff_files)

    # Leer y almacenar todos los frames de los archivos TIFF
    frames = []
    for tiff_file in tiff_files:
        with tifffile.TiffFile(os.path.join(ruta_carpeta, tiff_file)) as tif:
            for page in tif.pages:
                frames.append(page.asarray())

    # Guardar todos los frames en un solo archivo TIFF multipágina
    tifffile.imwrite(f'{ruta_carpeta}/{sample_name}.tiff', frames)

    # Devuelve la ruta al archivo TIFF multipágina creado
    return os.path.join(ruta_carpeta, f'{sample_name}.tiff')

def choose_and_process_lif_channel(lif_path, series_idx, channel_idx, num_frames, ruta_base, sample_name):
    """
    Chooses a series and a channel from the LIF file and converts them into a multipage TIFF file.

    Args:
        lif_path (str): Path to the LIF file.
        series_idx (int): Index of the series to process.
        channel_idx (int): Index of the channel to process.
        num_frames (int): Number of frames to process.
        ruta_base (str): Base path to save the files.
        sample_name (str): Name of the channel.

    Returns:
        str: Path to the created multipage TIFF file.
    """
    reader = LifFile(lif_path)
    series = reader.get_image(series_idx)
    return process_channel_to_tiff(series, channel_idx, num_frames, ruta_base, sample_name)

def process_multiple_channels(lif_path, series_list, channel_list, num_frames, ruta_base):
    """
    Processes multiple series and channels and saves the images into multipage TIFF files.

    Args:
        lif_path (str): Path to the LIF file.
        series_list (list): List of series indices to process.
        channel_list (list): List of channel indices to process.
        num_frames (int): Number of frames to process.
        ruta_base (str): Base path to save the files.

    Returns:
        list: List of paths to the created multipage TIFF files.
    """
    tiff_paths = []
    for series_idx, channel_idx in zip(series_list, channel_list):
        sample_name = f'channel_{series_idx + 1}_{channel_idx + 1}'
        ruta_tiff = choose_and_process_lif_channel(lif_path, series_idx, channel_idx, num_frames, ruta_base, sample_name)
        tiff_paths.append(ruta_tiff)
    
    return tiff_paths

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

#MAIN function automating the patch extraction process
def main_DataGenerator(filepath, role, percentile,patchsize,channels,ch1,ch2,ch3,l_layer,u_layer,biosample,datasize,mode,alpha,Norm,Brightness):
    l_layer = int(l_layer)
    u_layer = int(u_layer)
    percentile = float(percentile)
    patchsize = int(patchsize)
    #Number of channels from the stack as integers 
    channels = int(channels)
    if role == "train_test": 
        ch1 = int(ch1)
        ch2 = int(ch2)
        datasize = int(datasize)
    ch3 = int(ch3)
    if alpha:
        alpha = float(alpha)
    
    #Collects all planes from all 3 channels
    channel_stacks = []
    #List containing the calculated percentile value from each channel from the stack 
    percentiles = []


    if role == "train_test":
        
        if filepath.endswith('.lif'):

            series_list = [0, 0, 1]  # Lista de índices de las series a procesar
            channel_list = [1, 0, 0]  # Lista de índices de los canales a procesar

            num_frames = u_layer - l_layer
            ruta_base = '../channels'
            
            # Procesar las series y canales especificados
            filepaths = process_multiple_channels(filepath, series_list, channel_list, num_frames, ruta_base)
            
            l_layer, u_layer = 10, 20  # Define tus límites de capas
            
            channel_stacks, percentiles = calculate_percentiles(filepaths, l_layer, u_layer, percentile)

            t_train = int(datasize)
            t_test = int(t_train * 0.2)
            t_val = int(t_train * 0.2)
            
            if alpha:
                wb = str(alpha)+"_"+str(round(1-alpha,2))
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_"+wb+"_patches"
    
            elif Brightness:
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_br"+Brightness+"%"+"_patches"
            else:
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_patches"
            
            create_directories(datafoldername)
            
            extract_and_save_patches(datafoldername, t_train, t_test, t_val, patchsize, filepaths, channel_stacks, percentiles, mode, alpha, Norm, Brightness, filepath)
            shutil.rmtree(ruta_base)

            
        else:
            
            #LOADING THE CHANNEL DATA FROM THE 3D STACK AND CALCULATING PERCENTILE FOR EACH CHANNEL
            selected_channels = [ch1,ch2,ch3]
            #For each channel in the 3Dstack
            for i in selected_channels:
                #Temporary list holding the collected stacked planes from channel "i" each iteration
                tmp_channel_stacked_planes = []
                #For each layer in the range of lower and uper layer limits
                for j in range(l_layer,u_layer):
                    #Extracting layer (or plane) using the reading function from stapl3D. The plane consist of 49 tiles. 
                    data = shading.read_tiled_plane(filepath,i,j)
                    #Stacking the 49 tiles on top of each other. 
                    dstacked = np.stack(data, axis=0)
                    #Add stacked tiles from the single plane to temp list collecting each plane
                    tmp_channel_stacked_planes.append(dstacked)
    
                #Stacking all collected planes from a single channel as the following dimensions l,y,x   
                planes_stacked = np.vstack(tmp_channel_stacked_planes)
                #Append stacked planes of a single channel to list which collects all channel planes. 
                channel_stacks.append(planes_stacked)
                #Making a 1D vector for percentile calculation
                flat_stacked_planes = planes_stacked.flatten()
                #Calculating percentile value for the channel "i"
                p_val = np.percentile(planes_stacked, percentile)
    
                #Append percentile values to list
                percentiles.append(p_val)
            
            #AUTOMATING PATCH EXTRACTION
            #Get dimensions that will be used to extract patches
            dimensions = channel_stacks[0].shape 
    
    
            #Getting dimension of 3D stack l=layers, y and x tile size
            l = dimensions[0]
            y = dimensions[1]
            x = dimensions[2]
    
            #Upperbound for x and y (avoid taking patch beyond frame size)
            ubx = x-patchsize
            uby = y-patchsize
    
            #Defining proportions of the dataset
            t_train = int(datasize)
            t_test  = int(t_train*0.2)
            t_val   = int(t_train*0.2)
    
        
            #----------****CREATING FOLDERS****----------
            if alpha:
                wb = str(alpha)+"_"+str(round(1-alpha,2))
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_"+wb+"_patches"
    
            elif Brightness:
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_br"+Brightness+"%"+"_patches"
            else:
                datafoldername = biosample+"_"+str(datasize)+"_"+Norm+"_"+mode+"_patches"
    
    
            os.mkdir(datafoldername)
            if os.path.exists(datafoldername+"/train")==False:
                os.mkdir(datafoldername+"/train")
            if os.path.exists(datafoldername+"/test")==False:
                os.mkdir(datafoldername+"/test")
            if os.path.exists(datafoldername+"/val")==False:
                os.mkdir(datafoldername+"/val")    
    
    
            #----------********----------
            #Extracting patches for training testing and validation
    
            #Generating training set
            for t in range(t_train):    
    
                #Random patch is extracted and a synthetic source image and a ground truth target image is returned concatenated in AB png format
                image_AB = get_patch_train(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,Norm,Brightness,filepath)
                #Saving the AB patch
                matplotlib.image.imsave(datafoldername+"/train/"+str(t)+'.png', image_AB.astype(np.uint8))
    
            for t in range(t_test):  
                #Random patch is extracted and a synthetic source image and a ground truth target image is returned concatenated in AB png format
                image_AB = get_patch_train(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,Norm,Brightness,filepath)
                #Saving the AB patch
                matplotlib.image.imsave(datafoldername+"/test/"+str(t)+'.png', image_AB.astype(np.uint8))
    
            for t in range(t_val):  
                #Random patch is extracted and a synthetic source image and a ground truth target image is returned concatenated in AB png format
                image_AB = get_patch_train(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,Norm,Brightness,filepath)
                #Saving the AB patch
                matplotlib.image.imsave(datafoldername+"/val/"+str(t)+'.png', image_AB.astype(np.uint8))
    
    elif role == "predict": 
        #LOADING THE CHANNEL DATA FROM THE 3D STACK AND CALCULATING PERCENTILE FOR EACH CHANNEL
        selected_channels = [ch3]
        #For each channel in the 3Dstack
        for i in selected_channels:
            #Temporary list holding the collected stacked planes from channel "i" each iteration
            tmp_channel_stacked_planes = []
            #For each layer in the range of lower and uper layer limits
            for j in range(l_layer,u_layer):
                
                #Extracting layer (or plane) using the reading function from stapl3D. The plane consist of 49 tiles. 
                #data = shading.read_tiled_plane(filepath,i,j)
                
                dstack = []
                
                # Si el archivo es .lif...
                if filepath.endswith('.lif'):

                    # Definimos una lista que guarda los datos
                    m_idx = 3

                    # Leemos el archivo .lif
                    lif = LifFile(filepath)

                    # Tomamos la primera imagen del archivo .lif 
                    lim = lif.get_image(1)
                    #frame = lim.get_frame(z=j, c=i, t=0, m=m_idx)

                    # Obtenemos la cantidad de tiles en la dimensión m (m_idx)
                    n_tiles = lim.dims[m_idx]

                    # Iteramos tile por tile
                    for m in range(n_tiles):

                        # Obtenemos el frame para nuestros canales i, plano j (l y u_layer), tiempo 0 y tile m
                        data = lim.get_frame(z=j, c=i, t=0, m=m)

                        # Agregamos el frame a la lista dstack
                        dstack.append(data)
                
                elif filepath.endswith('.tiff'):
                    with TiffFile(filepath) as tif:
                        print(f'Iteracion {j} de {u_layer}')
                        data = tif.pages[j].asarray()
                        dstack.append(data)
                
                # Si no es .lif ejecuta read_tiled_plane tal cual desde STAPL-3D
                else:
                    dstack = shading.read_tiled_plane(filepath,i,j)




                #Stacking the 49 tiles on top of each other. 
                dstacked = np.stack(dstack, axis=0)
                #Add stacked tiles from the single plane to temp list collecting each plane
                tmp_channel_stacked_planes.append(dstacked)

            #Stacking all collected planes from a single channel as the following dimensions l,y,x   
            planes_stacked = np.vstack(tmp_channel_stacked_planes)
            #Append stacked planes of a single channel to list which collects all channel planes. 
            channel_stacks.append(planes_stacked)
            #Making a 1D vector for percentile calculation
            flat_stacked_planes = planes_stacked.flatten()
            #Calculating percentile value for the channel "i"
            p_val = np.percentile(planes_stacked, percentile)

            #Append percentile values to list
            percentiles.append(p_val)

        #AUTOMATING PATCH EXTRACTION
        #Get dimensions that will be used to extract patches
        dimensions = channel_stacks[0].shape 


        #Getting dimension of 3D stack l=layers, y and x tile size
        l = dimensions[0]
        y = dimensions[1]
        x = dimensions[2]

        #Upperbound for x and y (avoid taking patch beyond frame size)
        ubx = x-patchsize
        uby = y-patchsize
        
        #----------****CREATING FOLDERS****----------
        if alpha:
            wb = str(alpha)+"_"+str(round(1-alpha,2))
            datafoldername = biosample+"_"+Norm+"_"+mode+"_"+wb+"_patches"

        elif Brightness:
            datafoldername = biosample+"_"+Norm+"_"+mode+"_br"+Brightness+"%"+"_patches"
        else:
            datafoldername = biosample+"_"+Norm+"_"+mode+"_patches"


        os.mkdir(datafoldername)
        if os.path.exists(datafoldername+"/images")==False:
            os.mkdir(datafoldername+"/images")

        #----------********----------
        #Extracting patches for training testing and validation

        #Generating the images set
        for i in range(l):    
            #Random patch is extracted and a synthetic source image and a ground truth target image is returned concatenated in AB png format
            image_AB = get_patch_predict(l,uby,ubx,patchsize,channels,channel_stacks,percentiles,mode,alpha,Norm,Brightness,i)
            #Saving the AB patch
            matplotlib.image.imsave(datafoldername+"/images/"+str(i)+'.png', image_AB.astype(np.uint8))

if __name__ == '__main__':
    #Commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--Filepath", help = "Enter file path for .czi file")
    parser.add_argument("--Role", help = "Enter what you want to do with Data Generator: train_test | predict")
    parser.add_argument("--Percentile", help = "Enter percentile to normalize e.g 95")
    parser.add_argument("--PatchSize", help = "Enter size of patch as single integer e.g 512")
    parser.add_argument("--Channels", help = "Enter number of channels from 3D stack")
    parser.add_argument("--Channel1", help = "Number of channel where there is the data of one marker, starting by 0")
    parser.add_argument("--Channel2", help = "Number of channel where there is data of one marker, starting by 0")
    parser.add_argument("--Channel3", help = "Number of channel where there is the data of mixed signal, starting by 0")
    parser.add_argument("--BottomLayer", help = "Enter bottom layer number")
    parser.add_argument("--TopLayer", help = "Enter top layer number")
    parser.add_argument("--Biosample", help = "Enter biological sample name")
    parser.add_argument("--DatasetSize", help = "Enter size of training data to generate")
    parser.add_argument("--DataMode", help = "Enter data type: synthethic | open_detector | weighted | For weighted blending alpha must be set")
    parser.add_argument("--Alpha", help = "Enter ch1 alpha value for blending | ch2 alpha is automaticall calculated 1-alpha")
    parser.add_argument("--Normalization", help = "Enter normalization option for percentile value| od = Open detector percentile, ac = All channels percentiles")
    parser.add_argument("--Brightness", help = "Enter percentage of brighness augmented images in the dataset| enter as integer e.g. 50 -> means 50%")


    args = parser.parse_args()

                      
    main_DataGenerator(args.Filepath,args.Role,args.Percentile,args.PatchSize,args.Channels,args.Channel1,args.Channel2,args.Channel3,args.BottomLayer,args.TopLayer,args.Biosample,args.DatasetSize,args.DataMode,args.Alpha,args.Normalization,args.Brightness)
