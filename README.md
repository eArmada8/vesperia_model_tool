# Tales of Vesperia (PC) mesh toolset
Scripts to get the mesh data in and out of the files from Tales of Vesperia: Definitive Edition (PC).   The meshes are exported as raw buffers in the .fmt/.ib/.vb/.vgmap that are compatible with DarkStarSword Blender import plugin for 3DMigoto. A glTF file is also exported for purposes of weight painting and texture assignment, but the glTF file is not used for modding.

NOTE: There are multiple mesh types, denoted by the lower four bits of the second flag byte (0x100: standard skeletal animation, 0x400: not animated e.g weapons, 0x700: unsure animation e.g. faces). While vesperia_export_model.py is able to get mesh data out of all three, a lot of data is not interpreted for 0x400/0x700 meshes and vesperia_import_meshes.py cannot rebuild them.

## Tutorials:

Please see the [wiki](https://github.com/eArmada8/vesperia_model_tool/wiki), and the detailed documentation below.

## Credits:
I am as always very thankful for the dedicated reverse engineers at the Tales of ABCDE discord and the Kiseki modding discord, for their brilliant work, and for sharing that work so freely.  Thank you to NeXoGone and the original author of the Tales of Graces f noesis scripts for structural information as well!  This toolset also utilizes the tstrip module (python file format interface) adapted for [Sega_NN_tools](https://github.com/Argx2121/Sega_NN_tools/) by Argx2121, and I am grateful for its use - it is unmodified and is distributed under its original license.

## Requirements:
1. Python 3.10 and newer is required for use of these scripts.  It is free from the Microsoft Store, for Windows users.  For Linux users, please consult your distro.
2. The numpy module for python is needed.  Install by typing "python3 -m pip install numpy" in the command line / shell.  (The struct, json, io, glob, copy, subprocess, shutil, math, zlib, os, sys, and argparse modules are also required, but these are all already included in most basic python installations.)
3. The output can be imported into Blender as .glb, or as raw buffers using DarkStarSword's amazing plugin: https://github.com/DarkStarSword/3d-fixes/blob/master/blender_3dmigoto.py (tested on commit [5fd206c](https://raw.githubusercontent.com/DarkStarSword/3d-fixes/5fd206c52fb8c510727d1d3e4caeb95dac807fb2/blender_3dmigoto.py))
4. vesperia_export_model.py is dependent on lib_fmtibvb.py, which must be in the same folder.  vesperia_import_model.py is dependent on vesperia_export_model.py, lib_fmtibvb.py and the pyffi_tstrip module, all of which must be in the same folder.
5. vesperia_extract_svo.py can be used to unpack the .svo archives that come with the game, alternatively [HyoutaTools](https://github.com/AdmiralCurtiss/HyoutaTools) can be used.

## Usage:
### vesperia_extract_svo.py
Drag an .svo file onto vesperia_extract_svo.py to unpack it (or double-click the script to unpack all the .svo files in the same directory at once).  To make the game use the loose files, rename or delete the original .svo file.

### vesperia_export_model.py
Double click the python script and it will search for all model files (.DAT files).  Textures will be placed in a `textures` folder.

The script will search for an external skeleton.  If `BASEBONES.DAT` is in the same folder, it will preferentially use that file over loose skeleton files.  If it is not present, it will search for files with the word `BONE` in the name.  If you prefer loose files, decompress and unpack `BASEBONES.DAT` with HyoutaTools, and use the loose files (you do not need to rename them).  Generally you want to use the file that matches the character - for example if you are extracting Estelle's model `EST_C000.DAT` then you can use her skeleton file `EST_C000_BONE.0016` in place of `BASEBONES.DAT`.

**Command line arguments:**
`vesperia_export_model.py [-h] [-t] [-s] [-o] mdl_file`

`-t, --textformat`
Output .gltf/.bin format instead of .glb format.

`-s, --skiprawbuffers`
By default, the script will dump .fmt/.ib/.vb/.vgmap files in a folder with the same name as the .mdl file for modding.  Use DarkStarSword's plugin to view.  Using this option will trigger the script to skip dumping these files and only output the .glb file and its textures.

`-h, --help`
Shows help message.

`-o, --overwrite`
Overwrite existing files without prompting.

### vesperia_import_model.py
Double click the python script and it will search the current folder for all .DAT files with exported folders, and import the meshes in the folder back into the .DAT files.  Additionally, it will parse the 2 JSON files (mesh metadata, materials) if available and use that information to rebuild the mesh sections  This script requires a working .DAT file already be present as it does not reconstruct the entire file to include key metadata.

The remaining parts of the file (including the skeleton, materials, textures, etc) are copied unaltered from the .fps4 files inside the modding folders.

It will make a backup of the originals, then overwrite the originals.  It will not overwrite backups; for example if "model.DAT.bak" already exists, then it will write the backup to "model.DAT.bak1", then to "model.DAT.bak2", and so on.

*NOTE:* Newer versions of the Blender plugin export .vb0 files instead of .vb files.  Do not attempt to rename .vb0 files to .vb files, just leave them as-is and the scripts will look for the correct file.

**Command line arguments:**
`vesperia_import_model.py [-h] mdl_filename`

`-h, --help`
Shows help message.

**Adding and deleting meshes**

If any of the submeshes are missing (.fmt/.ib/.vb files that have been deleted), then the script will automatically delete that submesh from the model.  Metadata does not need to be altered.

The script only looks for mesh files that are listed in the `mesh_info.json`.  If you want to add a new mesh, you will need to add metadata.  So to add another mesh, add a section to the end of `mesh_info.json` like this:

```
    {
        "id_referenceonly": 5,
        "flags": 256,
        "name": "CHEST_EST_C00SHAPE4",
        "mesh": 58,
        "submesh": 1,
        "node": 58,
        "bounding_sphere_center": [
            0.0,
            99.60404968261719,
            0.8697500228881836
        ],
        "bounding_sphere_radius": 64.162109375,
        "unk_fltarr": [
            0.0,
            0.0,
            0.0,
            -0.0
        ],
        "uv_stride": 20,
        "flags2": 242,
        "total_verts": 1379,
        "total_idx": 2781,
        "unk": 0,
        "material": "CHEST3_EST_C003_MAT",
        "model": "PC/EST_C000/CHEST/EST_C000_CHEST",
        "vgmap": 2
    },
```

`id_referenceonly` is *NOT* used by the script, the meshes are calculated by entry order starting from zero (JSON convention) e.g. the first entry is always `0`, the third entry always `2`, etc, no matter what you put in that spot.  The import script doesn't even read `id_referenceonly`; it is only there for convenience.  When exporting new meshes from Blender, be sure to adhere to the filename convention of id number with 2 digits, underscore and name.  For example, the above entry should be `05_CHEST_EST_C00SHAPE4.vb` for the import script to find it.

The combination of `mesh` and `submesh` should probably be unique in the file.  Most of the time `node` is the same as the mesh.  Flags should match the mesh you are using; only 256 is supported currently.  When figuring out the number of UV maps, it is the presence of the buffer, not whether you use them - so even if the other UV maps are blanks or repeats, they must be accounted for in the flags (`uv_stride` = 8 × number of maps + 4).

All meshes in a submodel must use the same bone palette (the `vgmap` value is not used).  This bone palette is listed in bonemap.json.

The following fields are calculated, and thus are not read from the .json file: `bounding_sphere_center`, `bounding_sphere_radius`, `total_verts`, `total_idx`, `vgmap`.

Be sure to add a comma to the } for the section prior if you are using a text editor, or better yet use a dedicated JSON editor.  I actually recommend editing JSON in a dedicated editor, because python is not forgiving if you make mistakes with the JSON structure.  (Try https://jsoneditoronline.org)  Also, be sure to point material to a real section in material_info.json.  You might want to create a new section, or use an existing one.

**Changing materials and textures**

The .dds files that are in the same folder as the meshes will be packed in with the meshes.  For example, for model `EST_C000`, the textures that belong to `EST_C000_CHEST` will be in `/EST_C000/EST_C000_CHEST` and those will be packed in with the meshes to be used by those meshes.  The textures inside `/textures` is for the glTF files and are not used for modding.  Only BC7 textures with mipmaps have been confirmed to work thus far.

The materials are in `material_info.json`.  You can add and remove materials; be sure that both `name` and `internal_id` is unique to each entry in the material.

**Changing the skeleton**

It is not possible to change the base skeleton as the skeleton is external.  Each individual model inside the model container does have its own skeleton extension; at this time modifying this skeleton is also not supported directly.  However, you can replace one entire model container with another model container - see below.

**Changing submodel containers**

Each character model is actually several models inside a large container.  When using vesperia_export_model.py, it will unpack each submodel into its own folder.  Inside the submodel folder contains a binary form of the model along with all the unpacked information.  You can copy the entire contents of one submodel folder and replace the entire contents of another submodel folder (for example you could replace `EST_C000/EST_C000_CHEST` with `EST_C001/EST_C001_CHEST` by deleting the entire contents of `EST_C000/EST_C000_CHEST` from `EST_C000.DAT` and copying in the entire contents of `EST_C001/EST_C001_CHEST` from `EST_C001.DAT`).  vesperia_import_model.py will then rewrite the file pointers automatically when importing.  Please note that you cannot remove folders or add new folders, or have empty folders.  The game will refuse to load the model (or crash).

This is mainly for if you want to use a different submodel as a base to mod (for example if you need different bones) or if you want to attempt to replace one costume with another, etc.