#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D patternMaskSampler;  // 8192×8192 atlas with 256 tiles (16×16 grid, 512×512 per tile)
uniform vec3 color1;
uniform vec3 color2;
uniform vec3 color3;

void main()
{
	// vTexCoord already contains the correct UV coordinates for the selected tile
	vec4 textureMask = texture(patternMaskSampler, vTexCoord);
	
	vec3 outputColor = vec3(0.0);
	outputColor = mix(color1, color2, textureMask.g);
	outputColor = mix(outputColor, color3, textureMask.b);
	
	FragColor = vec4(outputColor, textureMask.a);
}

