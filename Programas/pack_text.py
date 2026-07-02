#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Layton's Text Packer
Packs translated text files back into binary .lbin format

Based on analysis of Professor Layton and the Lost Future text format.
'''

import re
import struct
import os
import glob
import sys
import shutil

__title__ = "Layton's Text Packer"
__version__ = "1.0"

# Special tag mappings (Spanish/Portuguese to Unicode)
TAG_MAP = {
    "{'a}": u'\xe1',  # á
    "{'e}": u'\xe9',  # é
    "{'i}": u'\xed',  # í
    "{'o}": u'\xf3',  # ó
    "{'u}": u'\xfa',  # ú
    "{''}": u'\u201d', # "
    "{^?}": u'\xbf',  # ¿
    "{^!}": u'\xa1',  # ¡
}

# Reverse mapping for unpacking (if needed later)
REVERSE_TAG_MAP = {v: k for k, v in TAG_MAP.items()}

def convert_tags_to_unicode(text):
    """Convert special tags to Unicode characters"""
    for tag, char in TAG_MAP.items():
        text = text.replace(tag, char)
    return text

def convert_unicode_to_tags(text):
    """Convert Unicode characters back to special tags"""
    for char, tag in REVERSE_TAG_MAP.items():
        text = text.replace(char, tag)
    return text

def parse_header(header_line):
    """Parse a header line like [7017010000000000:0002000000]"""
    header_line = header_line.strip()
    if header_line.startswith('[') and header_line.endswith(']'):
        content = header_line[1:-1]
        if ':' in content:
            parts = content.split(':', 1)
            id_part = parts[0]
            data_part = parts[1]
            return id_part, data_part
    return None, None

def header_to_bytes(id_part, data_part):
    """Convert hex header parts to bytes"""
    try:
        id_bytes = bytes.fromhex(id_part)
        data_bytes = bytes.fromhex(data_part)
        return id_bytes + data_bytes
    except ValueError:
        return None

def bytes_to_header(data_bytes):
    """Convert bytes back to hex header string"""
    hex_str = data_bytes.hex()
    # Try to split at a reasonable point (8 chars for ID, rest for data)
    if len(hex_str) >= 24:
        id_part = hex_str[:16]
        data_part = hex_str[16:]
        return "[%s:%s]" % (id_part, data_part)
    return "[%s]" % hex_str

def parse_text_file(filepath):
    """Parse a .lbin.txt file and return structured data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    current_header = None
    current_char = None
    current_text = []
    in_text = False
    
    for line in lines:
        line = line.rstrip('\n').rstrip('\r')
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if it's a header line
        if line.startswith('[') and line.endswith(']'):
            # Save previous entry if exists
            if current_header and current_text:
                entries.append({
                    'header': current_header,
                    'char': current_char,
                    'text': '\n'.join(current_text)
                })
            
            current_header = line
            current_char = None
            current_text = []
            in_text = False
            continue
        
        # Check if it's a separator
        if re.match(r'^!\D{30}!$', line):
            if in_text:
                # End of text block
                in_text = False
            continue
        
        # Check if it's a character name (short line without tags, between separators)
        if not in_text and current_header and not current_char:
            # This might be a character name
            if not line.startswith('<') and not line.startswith('{'):
                current_char = line
                continue
        
        # Otherwise it's text content
        if current_header:
            in_text = True
            current_text.append(line)
    
    # Don't forget the last entry
    if current_header and current_text:
        entries.append({
            'header': current_header,
            'char': current_char,
            'text': '\n'.join(current_text)
        })
    
    return entries

def parse_puzzle_text_file(filepath):
    """Parse a puzzle .lbin.txt file (rc/nazo format)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    current_header = None
    current_section = None
    current_text = []
    in_text = False
    
    for line in lines:
        line = line.rstrip('\n').rstrip('\r')
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if it's a header line
        if line.startswith('[') and line.endswith(']'):
            # Save previous entry if exists
            if current_header and current_text:
                entries.append({
                    'header': current_header,
                    'section': current_section,
                    'text': '\n'.join(current_text)
                })
            
            current_header = line
            current_section = None
            current_text = []
            in_text = False
            continue
        
        # Check if it's a separator
        if re.match(r'^!\D{30}!$', line):
            if in_text:
                in_text = False
            continue
        
        # Check if it's a section identifier (short line like n009, n009a, etc.)
        if not in_text and current_header and not current_section:
            if not line.startswith('<') and not line.startswith('{') and not line.startswith('['):
                current_section = line
                continue
        
        # Otherwise it's text content
        if current_header:
            in_text = True
            current_text.append(line)
    
    # Don't forget the last entry
    if current_header and current_text:
        entries.append({
            'header': current_header,
            'section': current_section,
            'text': '\n'.join(current_text)
        })
    
    return entries

def pack_text_file(entries, output_path):
    """Pack text entries into a binary file"""
    with open(output_path, 'wb') as f:
        for entry in entries:
            # Parse header
            id_part, data_part = parse_header(entry['header'])
            if id_part is None:
                print("Warning: Invalid header: %s" % entry['header'])
                continue
            
            # Convert header to bytes
            header_bytes = header_to_bytes(id_part, data_part)
            if header_bytes is None:
                print("Warning: Could not convert header to bytes: %s" % entry['header'])
                continue
            
            # Write header
            f.write(header_bytes)
            
            # Convert text to Unicode and then to UTF-8
            text = entry.get('text', '')
            text = convert_tags_to_unicode(text)
            text_bytes = text.encode('utf-8')
            
            # Write text length (4 bytes, little-endian)
            f.write(struct.pack('<I', len(text_bytes)))
            
            # Write text
            f.write(text_bytes)
            
            # Write null terminator
            f.write(b'\x00')

def pack_puzzle_text_file(entries, output_path):
    """Pack puzzle text entries into a binary file"""
    with open(output_path, 'wb') as f:
        for entry in entries:
            # Parse header
            id_part, data_part = parse_header(entry['header'])
            if id_part is None:
                print("Warning: Invalid header: %s" % entry['header'])
                continue
            
            # Convert header to bytes
            header_bytes = header_to_bytes(id_part, data_part)
            if header_bytes is None:
                print("Warning: Could not convert header to bytes: %s" % entry['header'])
                continue
            
            # Write header
            f.write(header_bytes)
            
            # Write section name if present
            if entry.get('section'):
                section_bytes = entry['section'].encode('utf-8')
                f.write(struct.pack('<I', len(section_bytes)))
                f.write(section_bytes)
                f.write(b'\x00')
            else:
                f.write(struct.pack('<I', 0))
            
            # Convert text to Unicode and then to UTF-8
            text = entry.get('text', '')
            text = convert_tags_to_unicode(text)
            text_bytes = text.encode('utf-8')
            
            # Write text length (4 bytes, little-endian)
            f.write(struct.pack('<I', len(text_bytes)))
            
            # Write text
            f.write(text_bytes)
            
            # Write null terminator
            f.write(b'\x00')

def process_directory(src_dir, dst_dir, is_puzzle=False):
    """Process all text files in a directory"""
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    
    # Find all .lbin.txt files
    pattern = os.path.join(src_dir, '**/*.lbin.txt')
    files = glob.glob(pattern, recursive=True)
    
    for txt_file in files:
        # Determine output path
        rel_path = os.path.relpath(txt_file, src_dir)
        bin_file = os.path.join(dst_dir, rel_path.replace('.lbin.txt', '.lbin'))
        
        # Create output directory if needed
        out_dir = os.path.dirname(bin_file)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        print("Packing: %s -> %s" % (txt_file, bin_file))
        
        # Parse and pack
        if is_puzzle:
            entries = parse_puzzle_text_file(txt_file)
            pack_puzzle_text_file(entries, bin_file)
        else:
            entries = parse_text_file(txt_file)
            pack_text_file(entries, bin_file)

def main():
    if len(sys.argv) < 4:
        print("Usage: pack_text.py <mode> <src_dir> <dst_dir>")
        print("  mode: txt or rc")
        print("  src_dir: Source directory with .lbin.txt files")
        print("  dst_dir: Destination directory for .lbin files")
        sys.exit(1)
    
    mode = sys.argv[1]
    src_dir = sys.argv[2]
    dst_dir = sys.argv[3]
    
    if mode == 'txt':
        process_directory(src_dir, dst_dir, is_puzzle=False)
    elif mode == 'rc':
        process_directory(src_dir, dst_dir, is_puzzle=True)
    else:
        print("Unknown mode: %s" % mode)
        sys.exit(1)
    
    print("Done!")

if __name__ == '__main__':
    main()
