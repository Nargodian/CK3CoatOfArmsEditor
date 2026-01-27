#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D patternTexture;
uniform sampler2D maskTexture;
uniform vec3 color1;
uniform vec3 color2;
uniform vec2 viewportSize;

void main()
{
	vec2 tileIndex = floor(vTexCoord * 32.0);
	vec2 tileCenter = (tileIndex + 0.5) / 32.0;
	vec2 scaleCoords = tileCenter + (vTexCoord - tileCenter) * 1.3;
	vec4 textureMask = texture(patternTexture, scaleCoords);
	
	vec3 outputColor = mix(color1, color2, textureMask.g);
	
	// Mask coordinate calculation using viewport size
	vec2 maskCoord = gl_FragCoord.xy / viewportSize;
	maskCoord.y = 1.0 - maskCoord.y;
	
	vec4 maskSample = texture(maskTexture, maskCoord);
	float maskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));
	
	FragColor = vec4(outputColor, textureMask.a * maskValue);
}

