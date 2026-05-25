"""
PSSML File Format Handler
Handles saving and loading of .pssml (Piper SSML) project files.
"""

import json
import os
from datetime import datetime
from typing import Tuple, Optional
from core.ssml_processor import SSMLRules


class PSSMLHandler:
    """Handle .pssml file format for SSML projects"""
    
    VERSION = "1.0"
    
    @staticmethod
    def save_pssml(filepath: str, original_text: str, ssml_text: str, rules: SSMLRules) -> bool:
        """
        Save SSML project to .pssml file.
        
        Args:
            filepath: Path to save file (should end with .pssml)
            original_text: Original plain text
            ssml_text: Processed SSML text
            rules: SSMLRules configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure .pssml extension
            if not filepath.endswith('.pssml'):
                filepath += '.pssml'
            
            # Create data structure
            data = {
                "version": PSSMLHandler.VERSION,
                "created": datetime.now().isoformat(),
                "original_text": original_text,
                "ssml_text": ssml_text,
                "rules": rules.to_dict()
            }
            
            # Write to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving PSSML file: {e}")
            return False
    
    @staticmethod
    def load_pssml(filepath: str) -> Optional[Tuple[str, str, SSMLRules]]:
        """
        Load SSML project from .pssml file.
        
        Args:
            filepath: Path to .pssml file
            
        Returns:
            Tuple of (original_text, ssml_text, rules) or None if error
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate version (for future compatibility)
            version = data.get("version", "1.0")
            if version != PSSMLHandler.VERSION:
                print(f"Warning: File version {version} may not be fully compatible with current version {PSSMLHandler.VERSION}")
            
            # Extract data
            original_text = data.get("original_text", "")
            ssml_text = data.get("ssml_text", "")
            rules_dict = data.get("rules", {})
            
            # Reconstruct SSMLRules
            rules = SSMLRules.from_dict(rules_dict)
            
            return (original_text, ssml_text, rules)
            
        except Exception as e:
            print(f"Error loading PSSML file: {e}")
            return None
    
    @staticmethod
    def export_ssml_xml(filepath: str, ssml_text: str) -> bool:
        """
        Export pure SSML XML to file.
        
        Args:
            filepath: Path to save XML file (should end with .xml or .ssml)
            ssml_text: SSML text to export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure appropriate extension
            if not (filepath.endswith('.xml') or filepath.endswith('.ssml')):
                filepath += '.xml'
            
            # Write SSML text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(ssml_text)
            
            return True
            
        except Exception as e:
            print(f"Error exporting SSML XML: {e}")
            return False
    
    @staticmethod
    def is_pssml_file(filepath: str) -> bool:
        """Check if file is a valid .pssml file"""
        if not os.path.exists(filepath):
            return False
        
        if not filepath.endswith('.pssml'):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check for required fields
                return all(key in data for key in ["version", "original_text", "ssml_text", "rules"])
        except:
            return False
