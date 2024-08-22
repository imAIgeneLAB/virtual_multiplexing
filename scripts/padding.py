import os
import numpy as np
import tifffile
import re

class Padding:
    def __init__(self, directory):
        """
        Initialize the Padding class.

        Parameters:
        directory (str): The directory where the TIFF files are located and where the padded tiles will be saved.
        """
        self.directory = directory
        self.tile_dict = {}
        self.max_tile_y = 0
        self.max_tile_x = 0
        self.padded_directory = os.path.join(directory, "padded_tiles")
        os.makedirs(self.padded_directory, exist_ok=True)

    def load_tiff(self, file_path):
        """
        Load a TIFF file as a numpy array.

        Parameters:
        file_path (str): The path to the TIFF file.

        Returns:
        numpy.ndarray: The image data loaded from the TIFF file.
        """
        with tifffile.TiffFile(file_path) as tif:
            return tif.asarray()

    def parse_filename(self, filename):
        """
        Extract the Z, X, Y coordinates from the filename.

        Parameters:
        filename (str): The name of the TIFF file.

        Returns:
        tuple: A tuple containing the Z, X, Y coordinates extracted from the filename.

        Raises:
        ValueError: If the filename does not match the expected pattern.
        """
        pattern = r'_block(\d+)x(\d+)x(\d+)\.tif$'
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        else:
            raise ValueError(f"Filename {filename} does not match the expected pattern.")

    def add_padding(self, tile, max_y, max_x, position):
        """
        Add padding to a tile based on its position.

        Parameters:
        tile (numpy.ndarray): The tile to which padding will be added.
        max_y (int): The maximum height of the final padded tile.
        max_x (int): The maximum width of the final padded tile.
        position (list): The position of the tile ('top', 'bottom', 'left', 'right', 'center').

        Returns:
        numpy.ndarray: The padded tile.
        """
        tile_z, tile_y, tile_x = tile.shape

        # Calculate the padding needed for each side
        pad_top = pad_bottom = pad_left = pad_right = 0
        if 'top' in position:
            pad_top = max_y - tile_y
        elif 'bottom' in position:
            pad_bottom = max_y - tile_y
        else:  # center
            pad_bottom = (max_y - tile_y) // 2
            pad_top = max_y - tile_y - pad_bottom

        if 'left' in position:
            pad_left = max_x - tile_x
        elif 'right' in position:
            pad_right = max_x - tile_x
        else:  # center
            pad_right = (max_x - tile_x) // 2
            pad_left = max_x - tile_x - pad_right

        # Apply padding
        padded_tile = np.pad(tile, ((0, 0), (pad_top, pad_bottom), (pad_left, pad_right)), mode='constant')
        
        return padded_tile

    def determine_position(self, x, y, max_x, max_y):
        """
        Determine the position of the tile in the complete image (e.g., edge, border, center).

        Parameters:
        x (int): The x-coordinate of the tile.
        y (int): The y-coordinate of the tile.
        max_x (int): The width of the full image.
        max_y (int): The height of the full image.

        Returns:
        list: A list indicating the tile's position (e.g., ['top', 'left']).
        """
        position = []
        if x == 0:
            position.append('top')
        elif x == max_y - 1:
            position.append('bottom')

        if y == 0:
            position.append('left')
        elif y == max_x - 1:
            position.append('right')

        return position

    def process_tiles_with_padding(self):
        """
        Load all tiles, add padding according to their position, and save the results.

        This method:
        - Loads all TIFF tiles from the directory.
        - Determines the maximum dimensions of the tiles.
        - Adds padding to each tile based on its position in the overall image.
        - Saves the padded tiles in a new directory.
        """
        # Load tiles into a dictionary, categorized by Z coordinate
        for filename in os.listdir(self.directory):
            if filename.endswith(".tif"):
                z, x, y = self.parse_filename(filename)
                file_path = os.path.join(self.directory, filename)
                tile = self.load_tiff(file_path)

                if z not in self.tile_dict:
                    self.tile_dict[z] = []
                self.tile_dict[z].append((x, y, tile))

        # Determine the maximum dimensions of tiles
        self.max_tile_y = max(tile.shape[1] for tiles in self.tile_dict.values() for _, _, tile in tiles)
        self.max_tile_x = max(tile.shape[2] for tiles in self.tile_dict.values() for _, _, tile in tiles)

        print(f"Maximum dimensions - Height (Y): {self.max_tile_y}, Width (X): {self.max_tile_x}")

        # Process and save padded tiles
        for z, tiles in self.tile_dict.items():
            max_x = max(x for x, _, _ in tiles) + 1
            max_y = max(y for _, y, _ in tiles) + 1

            for x, y, tile in tiles:
                position = self.determine_position(x, y, max_x, max_y)
                padded_tile = self.add_padding(tile, self.max_tile_y, self.max_tile_x, position)

                # Save the padded tile
                padded_filename = f'_block{z}x{x}x{y}_padded.tif'
                padded_path = os.path.join(self.padded_directory, padded_filename)
                tifffile.imwrite(padded_path, padded_tile)