#version 330 core

/**
 * Main Composite Shader DEBUG - Fragment Stage
 * 
 * Debug version with bounds visualization.
 */

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D coaTextureSampler;
uniform vec2 coaTopLeft;
uniform vec2 coaBottomRight;

void main() {
	vec2 fragPos = gl_FragCoord.xy;
	
	float minX = min(coaTopLeft.x, coaBottomRight.x);
	float maxX = max(coaTopLeft.x, coaBottomRight.x);
	float minY = min(coaTopLeft.y, coaBottomRight.y);
	float maxY = max(coaTopLeft.y, coaBottomRight.y);
	
	bool insideBounds = (fragPos.x >= minX && fragPos.x <= maxX && 
	                     fragPos.y >= minY && fragPos.y <= maxY);
	
	if (insideBounds) {
		// Calculate UV coordinates from fragment position
		vec2 coaUV = (fragPos - vec2(minX, minY)) / (vec2(maxX, maxY) - vec2(minX, minY));
		
		// Flip Y for OpenGL texture coords
		coaUV.y = 1.0 - coaUV.y;
		
		// Sample CoA texture
		vec4 coaColor = texture(coaTextureSampler, coaUV);
		
		// Show CoA content with border highlight
		bool onBorder = (fragPos.x < minX + 3.0 || fragPos.x > maxX - 3.0 ||
		                 fragPos.y < minY + 3.0 || fragPos.y > maxY - 3.0);
		
		if (onBorder) {
			FragColor = vec4(1.0, 1.0, 0.0, 1.0);  // Yellow border
		} else {
			FragColor = coaColor;
		}
		FragColor=vec4(1.,1.,0.,1.);	
	} else {
		// Red outside CoA bounds
		FragColor = vec4(1.0, 0.0, 0.0, 1.0);
	}
}
