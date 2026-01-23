from PIL import Image
import numpy as np

files = ['standard.png', 'no_colorspace.png', 'format_rgba.png', 'accurate.png']
print('Blue channel analysis for ce_vair_single conversions:\n')

for f in files:
    img = Image.open(f)
    arr = np.array(img)
    w, h = img.size
    center = arr[h//2, w//2]
    blue = arr[:,:,2]
    print(f'{f}:')
    print(f'  Center pixel: R={center[0]}, G={center[1]}, B={center[2]}, A={center[3]}')
    print(f'  Blue range: {blue.min()}-{blue.max()}, mean={blue.mean():.1f}, median={np.median(blue):.1f}')
    print()
