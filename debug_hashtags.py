#!/usr/bin/env python3
import re

def extract_hashtags_debug(text: str):
    """Extract hashtags from text with debug output"""
    hashtags = []
    i = 0
    
    print(f"Processing text: '{text}'")
    
    while i < len(text):
        print(f"Position {i}: '{text[i] if i < len(text) else 'END'}'")
        
        if i < len(text) and text[i] == '#':
            print(f"  Found # at position {i}")
            
            # Check if this is a valid hashtag position
            if i == 0:
                valid_start = True
                print(f"    Valid: start of string")
            elif text[i - 1] == '#':
                valid_start = False
                print(f"    Invalid: preceded by #")
            elif text[i - 1].isspace():
                valid_start = True
                print(f"    Valid: preceded by whitespace")
            else:
                valid_start = not text[i - 1].isalnum()
                print(f"    Valid check: prev char '{text[i - 1]}' isalnum={text[i - 1].isalnum()}, valid={valid_start}")
            
            if valid_start:
                # Extract hashtag content
                start = i + 1
                end = start
                while end < len(text) and text[end] not in ' #':
                    end += 1
                
                if end > start:  # Non-empty hashtag
                    hashtag_content = text[start:end]
                    hashtags.append(hashtag_content)
                    print(f"    Extracted hashtag: '{hashtag_content}' (positions {start}-{end})")
                    i = end  # Move to end of hashtag
                    print(f"    Moving to position {i}")
                    continue
            
            print(f"    Skipping, moving to {i+1}")
            i += 1
        else:
            i += 1
            
    print(f"Final result: {hashtags}")
    return hashtags

# Test the problematic case
extract_hashtags_debug('#hashtag#another')