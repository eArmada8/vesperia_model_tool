# Tales of Vesperia (PC) mesh export
A script to get the mesh data out of the files from Tales of Vesperia: Definitive Edition (PC).  The output is in .glb files, although there is an option for .fmt/.ib/.vb/.vgmap that are compatible with DarkStarSword Blender import plugin for 3DMigoto.  The goal is eventually turn this into a modding tool, although there is no specific timeline for that feature.

## Credits:
I am as always very thankful for the dedicated reverse engineers at the Tales of ABCDE discord and the Kiseki modding discord, for their brilliant work, and for sharing that work so freely.  Thank you to NeXoGone and the original author of the Tales of Graces f noesis scripts for structural information as well!

## Requirements:
1. Python 3.10 and newer is required for use of these scripts.  It is free from the Microsoft Store, for Windows users.  For Linux users, please consult your distro.
2. The numpy module for python is needed.  Install by typing "python3 -m pip install numpy" in the command line / shell.  (The struct, json, io, glob, copy, subprocess, os, sys, and argparse modules are also required, but these are all already included in most basic python installations.)
3. The output can be imported into Blender as .glb, or as raw buffers using DarkStarSword's amazing plugin: https://github.com/DarkStarSword/3d-fixes/blob/master/blender_3dmigoto.py (tested on commit [5fd206c](https://raw.githubusercontent.com/DarkStarSword/3d-fixes/5fd206c52fb8c510727d1d3e4caeb95dac807fb2/blender_3dmigoto.py))
4. vesperia_export_model.py is dependent on lib_fmtibvb.py, which must be in the same folder.
5. [HyoutaTools](https://github.com/AdmiralCurtiss/HyoutaTools) can be used to unpack the .svo archives that come with the game.

## Usage:
### vesperia_export_model.py
Double click the python script and it will search for all model files (.DAT files).  Textures will be placed in a `textures` folder.

The script will search for an external skeleton.  If `BASEBONES.DAT` is in the same folder, it will preferentially use that file over loose skeleton files.  If it is not present, it will search for files with the word `BONE` in the name.  If you prefer loose files, decompress and unpack `BASEBONES.DAT` with HyoutaTools, and use the loose files (you do not need to rename them).  Generally you want to use the file that matches the character - for example if you are extracting Estelle's model `EST_C000.DAT` then you can use her skeleton file `EST_C000_BONE.0016` in place of `BASEBONES.DAT`.

**Command line arguments:**
`vesperia_export_model.py [-h] [-t] [-d] [-o] mdl_file`

`-t, --textformat`
Output .gltf/.bin format instead of .glb format.

`-d, --dumprawbuffers`
Dump .fmt/.ib/.vb/.vgmap files in a folder with the same name as the .mdl file.  Use DarkStarSword's plugin to view.

`-h, --help`
Shows help message.

`-o, --overwrite`
Overwrite existing files without prompting.