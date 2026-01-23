from PIL import Image
import numpy as np

# Load the original texture
img = Image.open('source_coa_files/coa_mask_texture.png')
arr = np.array(img)

print(f'Original image shape: {arr.shape}')

# Create three separate images, each showing only one channel
# Red channel only
red_only = np.zeros_like(arr)
red_only[:,:,0] = arr[:,:,0]  # Copy red channel
red_only[:,:,3] = 255  # Keep alpha fully opaque
red_img = Image.fromarray(red_only, 'RGBA')
red_img.save('source_coa_files/coa_mask_RED_only.png')
print('Saved: coa_mask_RED_only.png')

# Green channel only
green_only = np.zeros_like(arr)
green_only[:,:,1] = arr[:,:,1]  # Copy green channel
green_only[:,:,3] = 255  # Keep alpha fully opaque
green_img = Image.fromarray(green_only, 'RGBA')
green_img.save('source_coa_files/coa_mask_GREEN_only.png')
print('Saved: coa_mask_GREEN_only.png')

# Blue channel only
blue_only = np.zeros_like(arr)
blue_only[:,:,2] = arr[:,:,2]  # Copy blue channel
blue_only[:,:,3] = 255  # Keep alpha fully opaque
blue_img = Image.fromarray(blue_only, 'RGBA')
blue_img.save('source_coa_files/coa_mask_BLUE_only.png')
print('Saved: coa_mask_BLUE_only.png')

print('\nCreated 3 separate channel images:')
print('  - Red channel: source_coa_files/coa_mask_RED_only.png')
print('  - Green channel: source_coa_files/coa_mask_GREEN_only.png')
print('  - Blue channel: source_coa_files/coa_mask_BLUE_only.png (the "Jackson Pollock" texture)')
