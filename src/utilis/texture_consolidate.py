import numpy as np
import math
from PIL import Image


def consolidate_textures(texture_list):
	"""Consolidate multiple textures into a single texture atlas.
	
	Args:
		texture_list (list of np.ndarray): List of 2D texture arrays (H x W x C).
		
	Returns:
		np.ndarray: Consolidated texture atlas.
		list of tuple: List of (x_offset, y_offset, width, height) for each original texture in the atlas.
	"""
	if not texture_list:
		return None, []
	
	# Determine atlas size
	max_width = max(tex.shape[1] for tex in texture_list)
	total_height = sum(tex.shape[0] for tex in texture_list)
	
	# Create empty atlas
	atlas = np.zeros((total_height, max_width, texture_list[0].shape[2]), dtype=texture_list[0].dtype)
	
	offsets = []
	current_y = 0
	
	for tex in texture_list:
		h, w, _ = tex.shape
		atlas[current_y:current_y + h, 0:w, :] = tex
		offsets.append((0, current_y, w, h))
		current_y += h
	
	return atlas, offsets

        
#builds texture atlas from list of file paths
#max of 1024 tiles of 256x256
def build_texture_atlas(texture_paths):
    
	# load textures into a list
	textureArray = np.zeros((1024, 256, 256, 4), dtype=np.uint8)
	for i, path in enumerate(texture_paths):
		with open(path, 'rb') as f:
			img_data = f.read()
		img = Image.open(io.BytesIO(img_data)).convert('RGBA')
		img = img.resize((256, 256), Image.ANTIALIAS)
		textureArray[i] = np.array(img)
	atlasTotal = math.floor(len(texture_paths)/1024)+1
	atlasTextures = np.zeros((atlasTotal, 8192, 8192, 4), dtype=np.uint8)
	for i in range(atlasTotal):
		start_idx = i * 1024
		end_idx = min((i + 1) * 1024, len(texture_paths))
		atlasTexture = consolidate_textures(textureArray[start_idx:end_idx])
	return atlasTextures