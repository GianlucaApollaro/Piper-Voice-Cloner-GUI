"""
SSML Processor for Piper TTS (Text-Only Mode)
Updates: Adjusted to produce clean text for Piper C++ Binary which does not support SSML tags.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

@dataclass
class SSMLRules:
    """Configuration for Text Enhancement rules"""
    
    # Punctuation-based pauses (Simulated via text)
    punctuation_pauses: Dict[str, any] = field(default_factory=lambda: {
        "enabled": True,
        "period": 800,      # Ignored in Text Mode (Standard Pause)
        "comma": 300,       # Ignored
        "exclamation": 1000,# Ignored
        "question": 1000,   # Ignored
        "ellipsis": 1500,   # Ignored
        "semicolon": 500,   # Ignored
        "colon": 400        # Ignored
    })
    
    # Number formatting rules
    number_formatting: Dict[str, bool] = field(default_factory=lambda: {
        "enabled": True,
        "cardinal": True,  # Leave as digits (Espeak handles it)
        "ordinal": True    # Leave as 1° (Espeak handles it)
    })
    
    # Spelling rules
    spelling: Dict[str, bool] = field(default_factory=lambda: {
        "enabled": True,
        "brackets": True,      # [ABC] -> A B C
        "uppercase": True      # WORD -> W O R D
    })
    
    # Paragraph structure
    paragraph_structure: Dict[str, bool] = field(default_factory=lambda: {
        "enabled": True,
        "double_newline": True  # \n\n -> \n
    })
    
    # Custom pronunciation dictionary (word -> Phonemes/Text)
    custom_dictionary: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class SSMLProcessor:
    """Process text to enhance pronunciation for Piper (Text Only)"""
    
    @staticmethod
    def apply_rules(text: str, rules: SSMLRules) -> str:
        """
        Apply enabled rules to enhance text.
        RETURNS PLAIN TEXT, NOT XML/SSML.
        """
        if not text.strip():
            return ""
        
        # Start with original text
        processed = text
        
        # 1. Custom Pronunciations (Simple Text Replacement)
        if rules.custom_dictionary:
            processed = SSMLProcessor._apply_custom_pronunciations(processed, rules)
        
        # 2. Spelling Rules (Crucial for Acronyms)
        if rules.spelling.get("enabled", False):
            processed = SSMLProcessor._apply_spelling(processed, rules)
        
        # 3. Numbers (Let Espeak handle proper formatting, just ensure spacing)
        # We skip manual conversion as Espeak logic is better than simple regex.
        
        # 4. Paragraph Structure (Normalize newlines)
        if rules.paragraph_structure.get("enabled", False):
            processed = SSMLProcessor._apply_paragraph_structure(processed, rules)
        
        # 5. Clean up any accidental tags
        processed = SSMLProcessor.strip_ssml_tags(processed)
        
        return processed
    
    @staticmethod
    def _apply_spelling(text: str, rules: SSMLRules) -> str:
        """Apply character-by-character spelling by adding spaces"""
        spelling = rules.spelling
        
        # Text in [brackets] -> [A B C]
        if spelling.get("brackets", False):
            def _spell_out(match):
                content = match.group(1)
                return " ".join(list(content))
            
            text = re.sub(r'\[([A-Za-z0-9]+)\]', _spell_out, text)
        
        # ALL CAPS words -> W O R D
        if spelling.get("uppercase", False):
            def _spell_caps(match):
                content = match.group(1)
                # Only spell out if it looks like an acronym (no vowels?) or configurable
                # For now, spell out everything that is strictly upper case > 2 chars
                return " ".join(list(content))

            text = re.sub(r'\b([A-Z]{2,})\b', _spell_caps, text)
        
        return text
    
    @staticmethod
    def _apply_paragraph_structure(text: str, rules: SSMLRules) -> str:
        """Normalize structure"""
        structure = rules.paragraph_structure
        
        if structure.get("double_newline", False):
            # Replace double newlines with single for cleaner consumption, or keep?
            # Piper splits sentences on newlines sometimes.
            # Let's ensure max 1 newline.
            text = re.sub(r'\n\s*\n', '\n', text)
            
        return text
    
    @staticmethod
    def _apply_custom_pronunciations(text: str, rules: SSMLRules) -> str:
        """Apply custom text replacements"""
        if not rules.custom_dictionary:
            return text
        
        sorted_words = sorted(rules.custom_dictionary.keys(), key=len, reverse=True)
        for word in sorted_words:
            replacement = rules.custom_dictionary[word]
            pattern = r'\b' + re.escape(word) + r'\b'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def strip_ssml_tags(text: str) -> str:
        """Remove all XML tags from text"""
        return re.sub(r'<[^>]+>', '', text).strip()
