"""
CK3 Coat of Arms Editor - Shader Manager

This module provides shader compilation and management utilities for OpenGL rendering.
"""

import os
from PyQt5.QtGui import QOpenGLShaderProgram, QOpenGLShader


class ShaderManager:
    """Manages OpenGL shader compilation and program creation"""
    
    def __init__(self, shader_dir=None):
        """Initialize shader manager
        
        Args:
            shader_dir: Path to directory containing shader files.
                       If None, uses default 'shaders' directory.
        """
        if shader_dir is None:
            # Default to shaders directory relative to src/
            # Current file is in src/components/canvas_widgets/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up 3 levels: canvas_widgets -> components -> src
            src_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            self.shader_dir = os.path.join(src_dir, 'src', 'shaders')
        else:
            self.shader_dir = shader_dir
    
    def create_program(self, parent, vertex_file, fragment_file, program_name="Shader"):
        """Create and link a shader program from vertex and fragment shader files
        
        Args:
            parent: Parent QObject (typically the OpenGL widget)
            vertex_file: Filename of vertex shader (e.g., 'basic.vert')
            fragment_file: Filename of fragment shader (e.g., 'base.frag')
            program_name: Name for error messages (e.g., 'Base', 'Design')
            
        Returns:
            QOpenGLShaderProgram if successful, None if compilation/linking failed
        """
        program = QOpenGLShaderProgram(parent)
        
        vert_path = os.path.join(self.shader_dir, vertex_file)
        frag_path = os.path.join(self.shader_dir, fragment_file)
        
        # Add vertex shader
        if not program.addShaderFromSourceFile(QOpenGLShader.Vertex, vert_path):
            print(f"{program_name} vertex shader error: {program.log()}")
            return None
        
        # Add fragment shader
        if not program.addShaderFromSourceFile(QOpenGLShader.Fragment, frag_path):
            print(f"{program_name} fragment shader error: {program.log()}")
            return None
        
        # Link program
        if not program.link():
            print(f"{program_name} shader link error: {program.log()}")
            return None
        
        return program
    
    def create_base_shader(self, parent):
        """Create base layer shader program
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for base layer rendering
        """
        return self.create_program(parent, 'basic.vert', 'base.frag', 'Base')
    
    def create_design_shader(self, parent):
        """Create design/emblem layer shader program
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for emblem layer rendering
        """
        return self.create_program(parent, 'basic.vert', 'design.frag', 'Design')
    
    def create_basic_shader(self, parent):
        """Create basic shader program for frame rendering
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for frame rendering
        """
        return self.create_program(parent, 'basic.vert', 'basic.frag', 'Basic')
