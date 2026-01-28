#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D patternMaskSampler;  // 8192×8192 atlas with 256 tiles (16×16 grid, 512×512 per tile)
uniform sampler2D texturedMaskSampler;  // Material/dirt texture (coa_mask_texture.png)
uniform sampler2D noiseMaskSampler;     // Noise texture (noise.png)
uniform vec3 color1;
uniform vec3 color2;
uniform vec3 color3;
uniform vec2 viewportSize;

void main()
{
	// vTexCoord already contains the correct UV coordinates for the selected tile
	vec4 textureMask = texture(patternMaskSampler, vTexCoord);
	
	vec3 outputColor = vec3(0.0);
	outputColor = mix(color1, color2, textureMask.g);
	outputColor = mix(outputColor, color3, textureMask.b);
	
	// Screen-space coordinates for material and noise (512×512 RTT)
	vec2 coaUV = gl_FragCoord.xy / vec2(512.0, 512.0);
	coaUV.y = 1.0 - coaUV.y;  // Flip Y
	
	// Apply material mask (dirt/texture)
	vec4 materialSample = texture(texturedMaskSampler, coaUV);
	outputColor = mix(outputColor, outputColor * materialSample.b, 0.5);
	
	// Apply noise grain
	float noise = texture(noiseMaskSampler, coaUV).r;
	outputColor = mix(outputColor, outputColor * noise, 0.2);
	
	FragColor = vec4(outputColor, textureMask.a);
}

