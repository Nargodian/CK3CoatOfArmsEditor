"""
Render-to-Texture (RTT) Framebuffer Manager

Manages OpenGL framebuffer objects for offscreen rendering of Coat of Arms.
This eliminates coordinate space conversion issues by rendering at canonical
resolution (512×512) then compositing to viewport.

Architecture:
1. Create FBO with RGBA texture attachment
2. Render pattern + emblems to FBO in canonical 0.0-1.0 UV space
3. Composite FBO texture to viewport quad with proper scaling
4. Apply frame overlay on top

Benefits:
- No more arbitrary scaling factors (1.62, 0.6, 1.1)
- Consistent mask coordinate space (always 0.0-1.0)
- Clean separation between CoA rendering and viewport display
- High-quality rendering independent of viewport size
"""

from OpenGL.GL import *


class FramebufferRTT:
	"""
	Manages an offscreen framebuffer for render-to-texture operations.
	
	The framebuffer contains a single RGBA texture at canonical CoA resolution
	(512×512 pixels = 2× mask resolution for quality).
	"""
	
	# Canonical CoA resolution (2× mask texture resolution for quality)
	COA_RTT_WIDTH = 512
	COA_RTT_HEIGHT = 512
	
	def __init__(self):
		"""Initialize framebuffer (lazy - actual creation on first use)."""
		self.fbo = None
		self.texture = None
		self.initialized = False
	
	def initialize(self):
		"""Create framebuffer and texture attachment."""
		if self.initialized:
			return
		
		# Create framebuffer object
		self.fbo = glGenFramebuffers(1)
		glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
		
		# Create texture for color attachment
		self.texture = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, self.texture)
		
		# Allocate texture storage (RGBA8, 512×512)
		glTexImage2D(
			GL_TEXTURE_2D, 0, GL_RGBA8,
			self.COA_RTT_WIDTH, self.COA_RTT_HEIGHT, 0,
			GL_RGBA, GL_UNSIGNED_BYTE, None
		)
		
		# Texture parameters (no mipmaps, linear filtering for quality)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		
		# Attach texture to framebuffer
		glFramebufferTexture2D(
			GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
			GL_TEXTURE_2D, self.texture, 0
		)
		
		# Check framebuffer completeness
		status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
		if status != GL_FRAMEBUFFER_COMPLETE:
			error_msg = {
				GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT: "Incomplete attachment",
				GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT: "Missing attachment",
				GL_FRAMEBUFFER_UNSUPPORTED: "Unsupported format",
			}.get(status, f"Unknown error ({status})")
			raise RuntimeError(f"Framebuffer incomplete: {error_msg}")
		
		# Unbind framebuffer (return to default)
		glBindFramebuffer(GL_FRAMEBUFFER, 0)
		
		self.initialized = True
	
	def bind(self):
		"""
		Bind framebuffer for rendering.
		
		After this call, all rendering goes to the offscreen texture until
		unbind() is called.
		"""
		if not self.initialized:
			self.initialize()
		
		glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
		glViewport(0, 0, self.COA_RTT_WIDTH, self.COA_RTT_HEIGHT)
	
	def unbind(self):
		"""
		Unbind framebuffer (return to default framebuffer).
		
		Caller must restore viewport to window dimensions.
		"""
		glBindFramebuffer(GL_FRAMEBUFFER, 0)
	
	def get_texture(self):
		"""
		Get the rendered texture ID.
		
		Returns:
			int: OpenGL texture ID containing the rendered CoA
		
		This texture can be used in subsequent rendering passes to composite
		the CoA onto the viewport with frame overlays.
		"""
		if not self.initialized:
			return 0
		return self.texture
	
	def clear(self, r=0.0, g=0.0, b=0.0, a=0.0):
		"""
		Clear the framebuffer to a color.
		
		Args:
			r, g, b, a: Clear color components (0.0-1.0)
		
		This should be called after bind() and before rendering CoA content.
		Use transparent black (0,0,0,0) to allow compositing over backgrounds.
		"""
		glClearColor(r, g, b, a)
		glClear(GL_COLOR_BUFFER_BIT)
	
	def cleanup(self):
		"""Release OpenGL resources."""
		if self.texture:
			glDeleteTextures([self.texture])
			self.texture = None
		
		if self.fbo:
			glDeleteFramebuffers(1, [self.fbo])
			self.fbo = None
		
		self.initialized = False
	
	def __del__(self):
		"""Ensure cleanup on garbage collection."""
		# Note: This may not work if OpenGL context is already destroyed
		# Prefer explicit cleanup() call
		try:
			self.cleanup()
		except:
			pass  # Silently fail if GL context is gone
