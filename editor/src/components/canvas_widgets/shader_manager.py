"""
CK3 Coat of Arms Editor - Shader Manager

This module provides shader compilation and management utilities for OpenGL rendering.
"""

import os
from PyQt5.QtGui import QOpenGLShaderProgram, QOpenGLShader
from utils.path_resolver import get_shader_dir


class ShaderManager:
    """Manages OpenGL shader compilation and program creation"""
    
    def __init__(self, shader_dir=None):
        """Initialize shader manager
        
        Args:
            shader_dir: Path to directory containing shader files.
                       If None, uses path_resolver to find shaders.
        """
        if shader_dir is None:
            self.shader_dir = str(get_shader_dir())
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
        return self.create_program(parent, 'basic.vert', 'pattern.frag', 'Base')
    
    def create_design_shader(self, parent):
        """Create design/emblem layer shader program
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for emblem layer rendering
        """
        return self.create_program(parent, 'basic.vert', 'emblem.frag', 'Design')
    
    def create_basic_shader(self, parent):
        """Create basic shader program for frame rendering
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for frame rendering
        """
        return self.create_program(parent, 'basic.vert', 'basic.frag', 'Basic')
    
    def create_composite_shader(self, parent):
        """Create composite shader program for RTT texture display
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for composite rendering
        """
        return self.create_program(parent, 'basic.vert', 'composite.frag', 'Composite')
    
    def create_picker_shader(self, parent):
        """Create picker shader program for layer selection RTT
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for picker rendering
        """
        return self.create_program(parent, 'basic.vert', 'emblem_picker.frag', 'Picker')
    
    def create_main_composite_shader(self, parent):
        """Create main composite shader program for frame-aware CoA rendering
        
        Args:
            parent: Parent QObject
            
        Returns:
            QOpenGLShaderProgram for main composite rendering
        """
        return self.create_program(parent, 'basic.vert', 'main_composite.frag', 'MainComposite')
