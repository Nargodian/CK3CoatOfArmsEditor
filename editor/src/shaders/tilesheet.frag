#version 330 core

in vec2 fragUV;
out vec4 fragColor;

uniform sampler2D textureSampler;
uniform int tileCols;      // Number of columns in tilesheet
uniform int tileRows;      // Number of rows in tilesheet
uniform int tileIndex;     // Which tile to display (0-based)

void main()
{
    // Calculate tile position in grid
    int col = tileIndex % tileCols;
    int row = tileIndex / tileCols;
    
    // Calculate UV offset and scale for this tile
    float tileWidth = 1.0 / float(tileCols);
    float tileHeight = 1.0 / float(tileRows);
    
    vec2 tileUV = vec2(
        float(col) * tileWidth + fragUV.x * tileWidth,
        float(row) * tileHeight + fragUV.y * tileHeight
    );
    
    fragColor = texture(textureSampler, tileUV);
}
