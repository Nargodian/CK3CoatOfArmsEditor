from PIL import Image
import numpy as np

img = Image.open('source_coa_files/coa_mask_texture.png')
arr = np.array(img)

print(f'Image Shape: {arr.shape}')
print(f'Data Type: {arr.dtype}')
print(f'Number of Channels: {arr.shape[2] if len(arr.shape) > 2 else 1}')

print(f'\nChannel Statistics:')
if len(arr.shape) > 2:
    channel_names = ['Red', 'Green', 'Blue', 'Alpha'][:arr.shape[2]]
    for i, name in enumerate(channel_names):
        channel = arr[:,:,i]
        print(f'\n{name} Channel:')
        print(f'  Min: {channel.min()}')
        print(f'  Max: {channel.max()}')
        print(f'  Mean: {channel.mean():.2f}')
        print(f'  Std: {channel.std():.2f}')
        print(f'  Median: {np.median(channel):.2f}')
        
        # Check distribution
        unique_vals = len(np.unique(channel))
        print(f'  Unique values: {unique_vals}')
        
        # Histogram
        hist, bins = np.histogram(channel, bins=10, range=(0, 255))
        print(f'  Histogram (0-255 in 10 bins): {hist}')
