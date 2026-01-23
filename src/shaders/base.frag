#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D textureSampler;
uniform sampler2D coaMaskSampler;

uniform vec3 primaryColor;
uniform vec3 secondaryColor;
uniform vec3 tertiaryColor;
uniform vec2 viewportSize;

void main()
{
	vec2 tileIndex = floor(vTexCoord * 32.0);  // Which tile in the 32x32 atlas
	vec2 tileCenter = (tileIndex + 0.5) / 32.0;  // Center of that tile in atlas coords
	vec2 scaleCoords = tileCenter + (vTexCoord - tileCenter) * 1.3;  // Scale around tile center
	vec4 textureMask=texture(textureSampler,scaleCoords);
	vec3 outputColour=vec3(0.);
	outputColour=mix(primaryColor,secondaryColor,textureMask.g);
	outputColour=mix(outputColour,tertiaryColor,textureMask.b);
	
	// Use screen-space coordinates for mask (0-1 range, centered)
	vec2 maskCoord=1.-(gl_FragCoord.xy/viewportSize);
	maskCoord -= 0.5; // Center the coordinates
	maskCoord *= 1.6; // Scale to cover more area
	maskCoord += 0.5; // Re-center the coordinates

	vec4 maskSample = texture(coaMaskSampler,maskCoord);
	// Use max of RGB channels or alpha, whichever has data
	float coaMaskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));
	
	FragColor=vec4(outputColour,textureMask.a*coaMaskValue);
}
