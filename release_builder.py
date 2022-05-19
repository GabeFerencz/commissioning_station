import os
import sys
from glob import glob

def parse_version_tag(version_tag):
    version_tag_tuple = version_tag.split('-')
    # Use long version for anything dirty (or tagged using '-')
    if len(version_tag_tuple) != 3:
        return version_tag
    # Use long version when not on a tagged commit
    if version_tag_tuple[1] != '0':
        return version_tag
    # Use the tag name on a clean tagged commit
    return version_tag_tuple[0]

def test_parse_version_tag():
    # Test things that should use the long version name
    use_long_name = ['Release-1.2-0-1234567', 'Release_1.2-5-1234567', 
                    'Release_1.2-5-1234567-dirty']
    for version_tag in use_long_name:
        exp = version_tag
        got = parse_version_tag(version_tag)
        assert got == exp, 'ERROR: got %s, expected %s'%(got, exp)

    # Test things that should use the short version name
    use_short_name = [('Release_1.2-0-1234567', 'Release_1.2'), 
                    ('Release_1.0-0-abcdef0', 'Release_1.0'),
                    ('v1.0-0-abcdef0', 'v1.0')]
    for (version_tag, resp) in use_short_name:
        exp = resp
        got = parse_version_tag(version_tag)
        assert got == exp, 'ERROR: got %s, expected %s'%(got, exp)

def build_release_file(version_string):
    lines = ['import sys']
    
    # Ensure that the equipment and procedures are on the path so they 
    # can be easily imported by the other scripts
    lines.append("sys.path.insert(0, './procedures')")
    lines.append("sys.path.insert(0, './equipment')")
    
    # Add the imports for the built in procedures
    for file in glob('procedures/*.py'):
        lines.append('import %s'%os.path.basename(file).replace('.py', ''))
    
    # Add the version string
    lines.append("version = '%s'"%parse_version_tag(version_string))

    release_file = open('release.py', 'w')
    release_file.write('\n'.join(lines))
    release_file.close()

if __name__ == "__main__":
    test_parse_version_tag()
    
    version_string = sys.argv[1]
    build_release_file(version_string)