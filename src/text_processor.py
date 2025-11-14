"""Text processing module for applying replacement rules."""
import re
from typing import List, Dict, Any, Optional


class TextProcessor:
    """Handles text replacement rules for message content."""
    
    def __init__(self, replacement_rules: List[Dict[str, Any]]):
        self.replacement_rules = replacement_rules
    
    def update_rules(self, replacement_rules: List[Dict[str, Any]]) -> None:
        """Update the replacement rules."""
        self.replacement_rules = replacement_rules
    
    def process_text(self, text: Optional[str]) -> Optional[str]:
        """
        Apply all replacement rules to the given text.
        
        Args:
            text: The text to process
            
        Returns:
            Processed text with all replacements applied
        """
        if not text:
            return text
        
        processed = text
        
        for rule in self.replacement_rules:
            find = rule.get("find", "")
            replace = rule.get("replace", "")
            case_sensitive = rule.get("case_sensitive", False)
            
            if not find:
                continue
            
            if case_sensitive:
                processed = processed.replace(find, replace)
            else:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(find), re.IGNORECASE)
                processed = pattern.sub(replace, processed)
        
        return processed
    
    def should_forward_message(self, text: Optional[str], filters: Dict[str, Any]) -> bool:
        """
        Check if a message should be forwarded based on filter settings.
        
        Args:
            text: The message text to check
            filters: Filter configuration
            
        Returns:
            True if message should be forwarded, False otherwise
        """
        if not filters.get("enabled", False):
            return True
        
        if not text:
            # If no text and filters are enabled, forward only if mode is blacklist
            return filters.get("mode", "whitelist") == "blacklist"
        
        keywords = filters.get("keywords", [])
        if not keywords:
            return True
        
        mode = filters.get("mode", "whitelist")
        text_lower = text.lower()
        
        has_keyword = any(keyword.lower() in text_lower for keyword in keywords)
        
        if mode == "whitelist":
            # In whitelist mode, forward only if message contains at least one keyword
            return has_keyword
        else:
            # In blacklist mode, forward only if message doesn't contain any keyword
            return not has_keyword
    
    def split_long_message(self, text: str, max_length: int = 4096) -> List[str]:
        """
        Split a long message into multiple parts if it exceeds max_length.
        
        Args:
            text: The text to split
            max_length: Maximum length per message part
            
        Returns:
            List of text parts
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Split by lines first to avoid breaking in the middle of a line
        lines = text.split('\n')
        
        for line in lines:
            # If a single line is longer than max_length, we need to split it
            if len(line) > max_length:
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                
                # Split long line by words
                words = line.split(' ')
                for word in words:
                    if len(current_part) + len(word) + 1 > max_length:
                        if current_part:
                            parts.append(current_part)
                        current_part = word
                    else:
                        if current_part:
                            current_part += ' ' + word
                        else:
                            current_part = word
            else:
                # Check if adding this line would exceed the limit
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line
                else:
                    if current_part:
                        current_part += '\n' + line
                    else:
                        current_part = line
        
        if current_part:
            parts.append(current_part)
        
        return parts

