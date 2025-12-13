# Tool to extract files from the .svo format used by Tales of Vesperia DE (PC/Steam).
#
# Usage:  Run by itself without commandline arguments and it will search for .svo files
# and export them all.
#
# For command line options, run:
# /path/to/python3 vesperia_extract_svo.py --help
#
# GitHub eArmada8/vesperia_model_tool

import struct, glob, os, sys

def extract_svo (svo_file):
    with open(svo_file, 'rb') as f:
        magic = f.read(4)
        if magic == b'FPS4':
            header = struct.unpack(">3I2H2I", f.read(24))
            toc = []
            for i in range(header[0] - 1): # Final entry is padding
                toc_entry = struct.unpack(">3I", f.read(12)) # offset, padded length, true length
                toc_name = f.read(0x20).rstrip(b'\x00').decode('utf-8')
                toc.append({'name': toc_name, 'offset': toc_entry[0],
                    'padded_size': toc_entry[2], 'true_size': toc_entry[2]})
            if not os.path.exists(svo_file[:-4]):
                os.mkdir(svo_file[:-4])
            for i in range(len(toc)):
                f.seek(toc[i]['offset'] * 0x80)
                open(svo_file[:-4] + '/' + toc[i]['name'], 'wb').write(f.read(toc[i]['true_size']))

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('svo_file', help="Name of svo file to extract.")
        args = parser.parse_args()
        if os.path.exists(args.svo_file) and args.svo_file[-4:] == '.svo':
            extract_svo(args.svo_file)
    else:
        svo_files = glob.glob('*.svo')
        for svo_file in svo_files:
            extract_svo(svo_file)
