#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D patternMask;
uniform vec3 color1;
uniform vec3 color2;
uniform vec2 viewportSize;

void main()
{
	vec2 tileIndex = floor(vTexCoord * 32.0);
	vec2 tileCenter = (tileIndex + 0.5) / 32.0;
	vec2 scaleCoords = tileCenter + (vTexCoord - tileCenter) * 1.3;
	vec4 textureMask = texture(patternMask, scaleCoords);
	
	vec3 outputColor = mix(color1, color2, textureMask.g);
	
	FragColor = vec4(outputColor, textureMask.a);
}

