from PIL import Image
from tqdm import tqdm
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import OG_TEAM_LOGOS_PATH

def resize_images(
    input_folder: str,
    output_folder: str,
    max_width: int = 100,
    max_height: int = 100,
    resample_method=Image.LANCZOS
):
    """
    Resize all images in input_folder and save to output_folder.

    Args:
        input_folder (str): Folder containing original images.
        output_folder (str): Folder to save resized images.
        max_width (int): Maximum width in pixels.
        max_height (int): Maximum height in pixels.
        resample_method: PIL resampling method (Image.NEAREST, Image.BILINEAR, etc.)

    Returns:
        None
    """
    os.makedirs(output_folder, exist_ok=True)
    
    for filename in tqdm(os.listdir(input_folder)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            img_path = os.path.join(input_folder, filename)
            with Image.open(img_path) as img:
                img.thumbnail((max_width, max_height), resample=resample_method)
                output_path = os.path.join(output_folder, filename)
                img.save(output_path)

if __name__ == "__main__":
    size = 150
    resize_images(
        input_folder=OG_TEAM_LOGOS_PATH,
        output_folder=f'{OG_TEAM_LOGOS_PATH}_{size}',
        max_width=size,
        max_height=size,
        resample_method=Image.LANCZOS
    )
