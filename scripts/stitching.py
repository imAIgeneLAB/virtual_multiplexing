import os
import re
import numpy as np
from PIL import Image

class Stitching:
    def __init__(self, directory, overlap_x, overlap_y):
        """
        Initializes the TileStitcher object with the directory of images and the overlap values.

        :param directory: Directory containing the subfolders with PNG files.
        :param overlap_x: Overlap size on the X-axis.
        :param overlap_y: Overlap size on the Y-axis.
        """
        self.directory = directory
        self.overlap_x = overlap_x
        self.overlap_y = overlap_y
        self.tile_dict = {}

    @staticmethod
    def load_png(file_path):
        """Loads a PNG file as a numpy array."""
        with Image.open(file_path) as img:
            return np.array(img)

    @staticmethod
    def parse_filename(filename):
        """Extracts the Z coordinate from the filename."""
        pattern = r'(\d+)_fake\.png$'
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1))
        else:
            raise ValueError(f"Filename {filename} does not match the expected pattern.")

    @staticmethod
    def extract_coordinates_from_folder(folder_name):
        """Extracts the X, Y coordinates from the subfolder name."""
        pattern = r'_block(\d+)x(\d+)x(\d+)$'
        match = re.search(pattern, folder_name)
        if match:
            x = int(match.group(2))
            y = int(match.group(3))
            return x, y
        else:
            raise ValueError(f"Folder name {folder_name} does not match the expected pattern.")

    def stitch_tiles(self, tiles):
        """Stitches the tiles considering the overlap."""
        n_tiles_y = len(tiles)
        n_tiles_x = len(tiles[0])

        max_tile_y = max(max(tile.shape[0] for tile in row) for row in tiles)
        max_tile_x = max(max(tile.shape[1] for tile in row) for row in tiles)
        min_tile_y = min(min(tile.shape[0] for tile in row) for row in tiles)
        min_tile_x = min(min(tile.shape[1] for tile in row) for row in tiles)
        
        stitched_y = max_tile_y * (n_tiles_y - 2) + min_tile_y * 2 - 2 * self.overlap_y * (n_tiles_y - 1)
        stitched_x = max_tile_x * (n_tiles_x - 2) + min_tile_x * 2 - 2 * self.overlap_x * (n_tiles_x - 1)

        stitched_image = np.zeros((stitched_y, stitched_x, tiles[0][0].shape[2]), dtype=np.float32)
        weight_map = np.zeros_like(stitched_image)

        # Loop through each tile to place it in its corresponding position in the final image
        for i in range(n_tiles_y):
            for j in range(n_tiles_x):
                tile = tiles[i][j]
                tile_y, tile_x, tile_channels = tile.shape

                left_overlap = self.overlap_x if j > 0 else 0
                right_overlap = self.overlap_x if j < n_tiles_x - 1 else 0
                top_overlap = self.overlap_y if i > 0 else 0
                bottom_overlap = self.overlap_y if i < n_tiles_y - 1 else 0

                if n_tiles_y == 2:
                    start_y = i * (max_tile_y - top_overlap * 2)
                    start_x = j * (max_tile_x - left_overlap * 2)
                else:
                    if i == 1:
                        start_y = i * (max_tile_y - top_overlap * 3)
                    else:
                        start_y = i * (max_tile_y - top_overlap * 2) - top_overlap

                    if j == 1:
                        start_x = j * (max_tile_x - left_overlap * 3)
                    else:
                        start_x = j * (max_tile_x - left_overlap * 2) - left_overlap

                end_y = start_y + tile_y
                end_x = start_x + tile_x

                end_y = min(end_y, stitched_y)
                end_x = min(end_x, stitched_x)
                start_y = max(start_y, 0)
                start_x = max(start_x, 0)

                tile_end_y = min(tile_y, end_y - start_y)
                tile_end_x = min(tile_x, end_x - start_x)

                tile_cut = tile[:tile_end_y, :tile_end_x, :]

                stitched_image[start_y:end_y, start_x:end_x, :] += tile_cut
                weight_map[start_y:end_y, start_x:end_x, :] += 1

        stitched_image /= np.maximum(weight_map, 1)

        final_image = stitched_image.astype(np.uint8)
        return final_image

    def process_directory(self):
        """Reads all PNG files in the directory and performs the stitching."""
        for subdir in os.listdir(self.directory):
            subdir_path = os.path.join(self.directory, subdir)
            if os.path.isdir(subdir_path):
                try:
                    x, y = self.extract_coordinates_from_folder(subdir)
                except ValueError:
                    print(f"Subfolder {subdir} does not follow the expected format 'data1channel-001_block0xXxY'. Ignoring...")
                    continue

                for filename in os.listdir(subdir_path):
                    if filename.endswith(".png"):
                        z = self.parse_filename(filename)
                        file_path = os.path.join(subdir_path, filename)
                        tile = self.load_png(file_path)

                        if z not in self.tile_dict:
                            self.tile_dict[z] = []
                        self.tile_dict[z].append((x, y, tile))

        for z in self.tile_dict:
            self.tile_dict[z] = sorted(self.tile_dict[z], key=lambda item: (item[0], item[1]))

        z_levels = sorted(self.tile_dict.keys())
        stitched_tiles = []
        for z in z_levels:
            max_x = max(x for x, _, _ in self.tile_dict[z]) + 1
            max_y = max(y for _, y, _ in self.tile_dict[z]) + 1
            tile_matrix = [[None] * max_y for _ in range(max_x)]

            for x, y, tile in self.tile_dict[z]:
                tile_matrix[x][y] = tile

            stitched_tiles.append(self.stitch_tiles(tile_matrix))

        return stitched_tiles

    def save_stitched_images(self, stitched_images, output_dir):
        """Saves the stitched images for each Z level as PNG files."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for i, stitched_image in enumerate(stitched_images):
            output_path = os.path.join(output_dir, f'stitched_image_z{self.overlap_x}_{i+1}.png')
            Image.fromarray(stitched_image).save(output_path)
            print(f'File saved at {output_path}')