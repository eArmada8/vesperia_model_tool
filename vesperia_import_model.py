# Tool to import model data into the dlb/dlp format used by Tales of Vesperia.
#
# Usage:  Run by itself without commandline arguments and it will replace
# only the mesh and textures sections of every model it finds in the folder
# and replace them with fmt/ib/vb and dds files in the same named directory.
#
# For command line options, run:
# /path/to/python3 vesperia_import_model.py --help
#
# Requires pyffi_tstrip module and lib_fmtibvb.py, put in the same directory
#
# GitHub eArmada8/vesperia_model_tool

try:
    import struct, json, io, math, shutil, zlib, glob, os, sys
    from lib_fmtibvb import *
    from vesperia_export_model import *
    from pyffi_tstrip.tristrip import *
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise

# Global variable, do not edit
e = '<'
addr_size = 4

def set_endianness (endianness):
    global e
    if endianness in ['<', '>']:
        e = endianness
    return

def write_offset (header_size, header_block, data_block):
    offset = header_size - len(header_block) + len(data_block)
    header_block.extend(struct.pack("{}{}".format(e, {4: "I", 8: "Q"}[addr_size]), offset))
    return

def compress_tlzc (unc_data):
    cmp_data = zlib.compress(unc_data)
    tlzc_data = bytearray(b'TLZC')
    tlzc_data.extend(struct.pack("<5I", 0x0201, len(cmp_data) + 0x18, len(unc_data), 0, 0))
    tlzc_data.extend(cmp_data)
    return(tlzc_data)

def read_fps4_with_names (fps4_filename):
    fps4_struct = []
    with open(fps4_filename, 'rb') as f:
        magic = f.read(4)
        if magic == b'FPS4':
            header = struct.unpack(">3I2H2I".format(e), f.read(24))
            toc = []
            for i in range(header[0]): # entry_stride should be 0x10
                toc_entry = struct.unpack(">4I".format(e), f.read(16)) # offset, padded length, true length, name offset
                toc_name = read_string(f, toc_entry[3])
                toc.append({'name': toc_name, 'offset': toc_entry[0],
                    'padded_size': toc_entry[2], 'true_size': toc_entry[2]})
            for i in range(len(toc) - 1):
                f.seek(toc[i]['offset'])
                fps4_struct.append({'name': toc[i]['name'], 'data': f.read(toc[i]['padded_size'])})
    return(fps4_struct)

def read_fps4_shell_type (fps4_filename):
    data_blocks = []
    with open(fps4_filename, 'rb') as f:
        magic = f.read(4)
        if magic == b'FPS4':
            header = struct.unpack(">3I2H2I".format(e), f.read(24))
            toc = []
            for i in range(header[0]): # entry_stride should be 0x10
                toc.append(struct.unpack(">3I".format(e), f.read(12))) # offset, padded length, true length
            start_offset = toc[0][0]
            base_name = read_string(f, f.tell())
            for i in range(len(toc) - 1):
                f.seek(toc[i][0])
                data_blocks.append(bytearray(f.read(toc[i][1])))
    return(data_blocks)

#Materials
def create_section_4 (material_struct):
    num_mats = len(material_struct)
    num_tex = sum([len(x['textures']) for x in material_struct])
    header_sz = 20 + (num_mats * 64) + (num_tex * 40)
    header_block = bytearray()
    name_data_block = bytearray()
    header_block.extend(struct.pack("{}5I".format(e), 0x30000, 0, 0x10, num_mats, num_tex))
    for i in range(num_mats):
        header_block.extend(struct.pack("{}2i".format(e), len(material_struct[i]['textures']),
            material_struct[i]['internal_id']))
        header_block.extend(struct.pack("{}if4i".format(e), *material_struct[i]['unk_parameters']['set_0']['base']))
        for j in range(len(material_struct[i]['textures'])):
            header_block.extend(struct.pack("{}2i".format(e), *material_struct[i]['unk_parameters']['set_0']['tex'][j]))
    for i in range(num_mats):
        header_block.extend(struct.pack("{}I".format(e), material_struct[i]['unk_parameters']['set_1']['base'][0]))
        write_offset(header_sz, header_block, name_data_block)
        name_data_block.extend(material_struct[i]['name'].encode('utf-8') + b'\x00')
        write_offset(header_sz, header_block, name_data_block)
        name_data_block.extend(b'\x00')
        header_block.extend(struct.pack("{}I".format(e), material_struct[i]['unk_parameters']['set_1']['base'][1]))
        for j in range(len(material_struct[i]['textures'])):
            write_offset(header_sz, header_block, name_data_block)
            name_data_block.extend(material_struct[i]['textures'][j].encode('utf-8') + b'\x00')
            header_block.extend(struct.pack("{}I".format(e), material_struct[i]['unk_parameters']['set_1']['tex'][j]))
    for i in range(num_mats):
        header_block.extend(struct.pack("{}4f".format(e), *material_struct[i]['unk_parameters']['set_2']['base_floats']))
        for j in range(len(material_struct[i]['textures'])):
            header_block.extend(struct.pack("{}6f".format(e), *material_struct[i]['unk_parameters']['set_2']['tex_floats'][j]))
    sec_4_block = bytearray(header_block + name_data_block)
    while len(sec_4_block) % 0x10:
        sec_4_block.extend(b'\x00')
    sec_4_block[4:8] = struct.pack("{}I".format(e), len(sec_4_block))
    return (sec_4_block)

#Meshes
def create_section_67 (model_base_name, mesh_blocks_info, bone_palette_ids, material_struct):
    material_dict = {material_struct[i]['name']:material_struct[i]['internal_id'] for i in range(len(material_struct))}
    # Generate mesh blocks first (vertices, indices, uv coordinates)
    base_num_verts, total_verts, total_idxs = [], [], []
    material_list = []
    mesh_midpoint_list, mesh_radii_list = [], []
    vert_blocks, idx_blocks, uv_blocks = [], [], []
    inserted_meshes_info = []
    for i in range(len(mesh_blocks_info)):
        safe_filename = "".join([x if x not in "\\/:*?<>|" else "_" for x in mesh_blocks_info[i]["name"]])
        num_uvs = (mesh_blocks_info[i]["uv_stride"] - 4) // 8
        try:
            mesh_filename = model_base_name + '/{0:02d}_{1}'.format(i, safe_filename)
            fmt = read_fmt(mesh_filename + '.fmt')
            ib = read_ib(mesh_filename + '.ib', fmt)
            vb = read_vb(mesh_filename + '.vb', fmt)
            assert ([x['SemanticName'] for x in fmt['elements']]
                == ['POSITION', 'NORMAL']
                + ['TEXCOORD'] * num_uvs
                + ['BLENDWEIGHTS', 'BLENDINDICES'])
            stride_semantic = 'vb0 stride' if 'vb0 stride' in fmt else 'stride'
            assert (int(fmt[stride_semantic]) == 44 + (8 * num_uvs))
        except (FileNotFoundError, AssertionError) as err:
            print("Submesh {0} not found or corrupt, skipping...".format(mesh_filename))
            continue
        print("Processing submesh {0}...".format(mesh_filename))
        try:
            material_list.append(material_dict[mesh_blocks_info[i]["material"]])
        except:
            print("Unable to read material for {}!  The material assignment is either missing or invalid.".format(safe_filename))
            input("Press Enter to quit.")
            raise
            #pass
        x0,x1 = max([x[0] for x in vb[0]['Buffer']]), min([x[0] for x in vb[0]['Buffer']])
        y0,y1 = max([x[1] for x in vb[0]['Buffer']]), min([x[1] for x in vb[0]['Buffer']])
        z0,z1 = max([x[2] for x in vb[0]['Buffer']]), min([x[2] for x in vb[0]['Buffer']])
        mesh_midpoint = ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2)
        bounding_sphere_radius = max([math.dist(x, mesh_midpoint) for x in vb[0]['Buffer']])
        mesh_midpoint_list.append(mesh_midpoint)
        mesh_radii_list.append(bounding_sphere_radius)
        # Standard weighted meshes
        vert_block = bytearray()
        idx_dat_block = bytearray()
        uv_block = bytearray()
        total_vert = 0
        total_idx = 0
        if mesh_blocks_info[i]["flags"] & 0xF00 == 0x100:
            ib_blocks = [ib]
            vb_blocks = [vb]
            idx_header_block = bytearray(struct.pack("{}I".format(e), len(ib_blocks)))
            for j in range(1): # splitting later
                # Split vertices into weight types
                vgrp = [4 if not x[3]==0.0 else 3 if not x[2]==0.0 else 2 if not x[1]==0.0 else 1 for x in vb_blocks[j][-2]['Buffer']]
                v_by_grp = [[l for l, vgrpval in enumerate(vgrp) if vgrpval == k] for k in range(1,5)]
                new_v_assgn = {}
                counter = 0
                for k in range(len(v_by_grp)):
                    for l in range(len(v_by_grp[k])):
                        new_v_assgn[v_by_grp[k][l]] = counter
                        counter += 1
                if j == 0:
                    base_num_verts.append([len(x) for x in v_by_grp])
                else:
                    vert_block.extend(struct.pack("{}4I".format(e), *[len(x) for x in v_by_grp]))
                for k in range(len(v_by_grp)):
                    for l in range(len(v_by_grp[k])):
                        vert_block.extend(struct.pack("{}3f".format(e), *vb_blocks[j][0]['Buffer'][v_by_grp[k][l]])) # Vertices
                        vert_block.extend(struct.pack("{}3f".format(e), *vb_blocks[j][1]['Buffer'][v_by_grp[k][l]])) # Normals
                        vert_block.extend(struct.pack("{}4B".format(e), *vb_blocks[j][-1]['Buffer'][v_by_grp[k][l]][::-1])) # Blend indices
                        if k > 0:
                            vert_block.extend(struct.pack("{}{}f".format(e, k),
                                *vb_blocks[j][-2]['Buffer'][v_by_grp[k][l]][:k])) # Blend weights
                        uv_block.extend(struct.pack("{}i".format(e), -1)) # Padding
                        for m in range(num_uvs):
                            uv_block.extend(struct.pack("{}2f".format(e), *vb_blocks[j][2+m]['Buffer'][v_by_grp[k][l]])) # UVs
                total_vert += len(vb_blocks[j][0]['Buffer'])
                new_ib = [new_v_assgn[x] for x in stripify(ib_blocks[j], stitchstrips = True)[0]]
                idx_dat_block.extend(struct.pack("{}{}H".format(e, len(new_ib)), *new_ib)) # Triangles
                total_idx += len(new_ib)
                idx_header_block.extend(struct.pack("{}2H".format(e), len(vb_blocks[j][0]['Buffer']), len(new_ib)))
            idx_block = bytearray(idx_header_block + idx_dat_block)
            if len(idx_block) % 4:
                idx_block += b'\x00' * (4 - (len(idx_block) % 4))
        # Unsupported mesh type, e.g. 0x400 mesh
        else:
            return
        vert_block.extend(struct.pack("<4I", *[0]*4)) # Padding
        vert_blocks.append(vert_block)
        idx_blocks.append(idx_block)
        uv_blocks.append(uv_block)
        total_verts.append(total_vert)
        total_idxs.append(total_idx)
        inserted_meshes_info.append(mesh_blocks_info[i])
    # Generate mesh block header
    num_meshes = len(inserted_meshes_info)
    palette_count = len(bone_palette_ids)
    head_sz = round_up_align(0x24 + (0x6c * num_meshes) + (0x4 * palette_count), align = 16)
    vblock_sz = sum([len(x) for x in vert_blocks])
    iblock_sz = sum([len(x) for x in idx_blocks])
    # The second value is the size of the final block, will need to be updated at the end
    header_block = bytearray(struct.pack("<9I", 0x10000, 0, 0x10, num_meshes, palette_count, 0, 0, 0, 0))
    vert_data_block = bytearray()
    idx_data_block = bytearray()
    uv_data_block = bytearray()
    name_data_block = bytearray()
    for i in range(num_meshes):
        header_block.extend(struct.pack("{}3f".format(e), *mesh_midpoint_list[i]))
        header_block.extend(struct.pack("{}f".format(e), mesh_radii_list[i]))
        header_block.extend(struct.pack("{}4I".format(e), *base_num_verts[i]))
    for i in range(num_meshes):
        header_block.extend(struct.pack("{}4f".format(e), *inserted_meshes_info[i]['unk_fltarr']))
    for i in range(num_meshes):
        header_block.extend(struct.pack("{}4I".format(e), inserted_meshes_info[i]['flags'],
            inserted_meshes_info[i]['mesh'], inserted_meshes_info[i]['submesh'], inserted_meshes_info[i]['node']))
        header_block.extend(struct.pack("{}I".format(e), material_list[i]))
        header_block.extend(struct.pack("{}I".format(e), len(uv_data_block)))
        uv_data_block.extend(uv_blocks[i])
        write_offset(head_sz + vblock_sz, header_block, idx_data_block)
        idx_data_block.extend(idx_blocks[i])
        write_offset(head_sz, header_block, vert_data_block)
        vert_data_block.extend(vert_blocks[i])
        header_block.extend(struct.pack("{}5I".format(e), inserted_meshes_info[i]['uv_stride'],
            inserted_meshes_info[i]['flags2'], total_verts[i], total_idxs[i], inserted_meshes_info[i]['unk']))
        write_offset(head_sz + vblock_sz + iblock_sz, header_block, name_data_block)
        name_data_block.extend(inserted_meshes_info[i]['name'].encode('utf-8') + b'\x00')
        write_offset(head_sz + vblock_sz + iblock_sz, header_block, name_data_block)
        name_data_block.extend(b'\x00')
    header_block.extend(struct.pack("{}{}I".format(e, palette_count), *bone_palette_ids))
    while len(header_block) % 0x10:
        header_block.extend(b'\x00')
    sec_6_block = bytearray(header_block + vert_data_block + idx_data_block + name_data_block)
    while len(sec_6_block) % 0x10:
        sec_6_block.extend(b'\x00')
    sec_6_block[4:8] = struct.pack("{}I".format(e), len(sec_6_block))
    while len(uv_data_block) % 0x10:
        uv_data_block.extend(b'\x00')
    uv_data_block.extend(struct.pack("{}16I".format(e), *[0]*16))
    return (sec_6_block, uv_data_block)

#Textures
def create_section_89 (model_base_name, tex_names):
    current_endian = e
    set_endianness('>') # This section is in big endian (and most of the data is actually wrong)
    sec_9_block = bytearray()
    sec_8_header_sz = (0x18 + (0x1C * len(tex_names)))
    sec_8_header_block = bytearray(struct.pack("{}6I".format(e), 0x20000, 0, 0x10, len(tex_names), 0, 0))
    sec_8_name_block = bytearray()
    for i in range(len(tex_names)):
        with open(model_base_name + '/' + tex_names[i] + '.dds', 'rb') as f:
            img_dat = f.read()
        magic = img_dat[0:4].decode("ASCII")
        if magic == 'DDS ':
            header = {}
            header['dwSize'], header['dwFlags'], header['dwHeight'], header['dwWidth'],\
                    header['dwPitchOrLinearSize'], header['dwDepth'], header['dwMipMapCount']\
                    = struct.unpack("<7I", img_dat[4:32])
            sec_8_header_block.extend(struct.pack("{}4I".format(e), header['dwWidth'], header['dwHeight'],
                header['dwMipMapCount'], 0x8804aae4)) # The last hex value is wrong, even in native files
            write_offset(sec_8_header_sz, sec_8_header_block, sec_8_name_block)
            sec_8_name_block.extend(tex_names[i].encode('utf-8') + b'\x00')
            sec_8_header_block.extend(struct.pack("{}2I".format(e), len(sec_9_block), 0))
            sec_9_block.extend(struct.pack("{}I".format(e), len(img_dat)))
            sec_9_block.extend(img_dat)
    sec_8_block = bytearray(sec_8_header_block + sec_8_name_block)
    while len(sec_8_block) % 0x10:
        sec_8_block.extend(b'\x00')
    sec_8_block[4:8] = struct.pack("{}I".format(e), len(sec_8_block))
    while len(sec_9_block) % 0x10:
        sec_9_block.extend(b'\x00')
    set_endianness(current_endian) # Restore original endianness
    return (sec_8_block, sec_9_block)

def rebuild_mdl (mdl_file):
    new_model_fps4 = bytearray()
    with open(mdl_file, 'rb') as f:
        magic = f.read(4)
        if magic == b'TLZC':
            unc_data = decompress_tlzc(f)
        elif magic == b'FPS4':
            f.seek(0)
            unc_data = f.read()
    with io.BytesIO(unc_data) as f:
        set_endianness('<') # Figure out later how to determine this
        magic = f.read(4)
        if magic == b'FPS4':
            header = struct.unpack(">3I2H2I".format(e), f.read(24)) # num_entries, unk, len_header, entry_stride, unk * 3
            toc = []
            for i in range(header[0]): # entry_stride should be 0x10
                toc.append(struct.unpack(">3I".format(e), f.read(12))) # offset, padded length, true length
            start_offset = toc[0][0]
            base_name = read_string(f, f.tell())
            # Model is the first file
            f.seek(start_offset)
            magic_1 = f.read(4)
            if magic_1 == b'FPS4':
                header_1 = struct.unpack(">3I2H2I".format(e), f.read(24))
                toc_1 = []
                for i in range(header_1[0]): # entry_stride should be 0x10
                    toc_entry = struct.unpack(">4I".format(e), f.read(16)) # offset, padded length, true length, name offset
                    toc_name = read_string(f, start_offset + toc_entry[3])
                    toc_1.append({'name': toc_name, 'offset': toc_entry[0] + start_offset,
                        'padded_size': toc_entry[2], 'true_size': toc_entry[2]})
                model_dir = {}
                for i in range(len(toc_1)):
                    if toc_1[i]['name'] in model_dir:
                        model_dir[toc_1[i]['name']].append(i)
                    else:
                        model_dir[toc_1[i]['name']] = [i]
                if 'FPS4' in model_dir:
                    del(model_dir['FPS4']) # The final entry is padding
                model_skel_struct = read_struct_from_json(base_name + '/primary_skeleton_info.json')\
                    + [x for y in [read_struct_from_json(base_name + '/' + os.path.basename(model)
                    + '/model_skeleton_info.json') for model in model_dir] for x in y]
                tail_fps4_blocks = read_fps4_shell_type(base_name + '/model_tail_blocks.fps4')
                fps4_struct = []
                for model in model_dir:
                    model_base_name = base_name + '/' + os.path.basename(model)
                    base_model_data_blocks = read_fps4_with_names('{0}/zz_base_model.bin'.format(model_base_name))
                    for i in range(len(base_model_data_blocks)):
                        base_model_data_blocks[i]['name'] = model
                    # Build new material section
                    material_struct = read_struct_from_json(model_base_name + "/material_info.json")
                    sec4 = create_section_4 (material_struct)
                    base_model_data_blocks[4]['data'] = sec4
                    # Build new mesh section
                    mesh_blocks_info = read_struct_from_json(model_base_name + "/mesh_info.json")
                    if all([mesh_blocks_info[i]["flags"] & 0xF00 in [0x100] for i in range(len(mesh_blocks_info))]):
                        bonemap = read_struct_from_json(model_base_name + "/bonemap.json")
                        bone_dict = {x['name']:x['id'] for x in model_skel_struct}
                        bone_palette_ids = [bone_dict[bonemap[i]] if bonemap[i] in bone_dict
                            else int(bonemap[i].replace('bone_','')) for i in range(len(bonemap))]
                        sec6, sec7 = create_section_67 (model_base_name, mesh_blocks_info, bone_palette_ids, material_struct)
                        base_model_data_blocks[6]['data'] = sec6
                        base_model_data_blocks[7]['data'] = sec7
                    else:
                        print("Skipping mesh rebuild for sub-model {}... (unsupported mesh types)".format(model))
                    # Build new texture section
                    tex_names = [os.path.basename(x)[:-4] for x in glob.glob(model_base_name + '/*.dds')]
                    sec8, sec9 = create_section_89 (model_base_name, tex_names)
                    base_model_data_blocks[8]['data'] = sec8
                    base_model_data_blocks[9]['data'] = sec9
                    fps4_struct.extend(base_model_data_blocks)
                new_model_inner_fps4 = write_fps4_with_names (fps4_struct)
                new_model_fps4 = write_fps4_shell_type ([new_model_inner_fps4]
                    + tail_fps4_blocks, shell_name = base_name)
    return (new_model_fps4)

def process_mdl(mdl_file):
    print("Processing {}...".format(mdl_file))
    new_model_fps4 = rebuild_mdl(mdl_file)
    cmp_model_fps4 = compress_tlzc(new_model_fps4)
    # Instead of overwriting backups, it will just tag a number onto the end
    backup_suffix = ''
    if os.path.exists(mdl_file + '.bak' + backup_suffix):
        backup_suffix = '1'
        if os.path.exists(mdl_file + '.bak' + backup_suffix):
            while os.path.exists(mdl_file + '.bak' + backup_suffix):
                backup_suffix = str(int(backup_suffix) + 1)
        shutil.copy2(mdl_file, mdl_file + '.bak' + backup_suffix)
    else:
        shutil.copy2(mdl_file, mdl_file + '.bak')
    open(mdl_file, 'wb').write(cmp_model_fps4)
    return

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # If argument given, attempt to import into file in argument
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('mdl_filename', help="Name of model .DAT file to import into (required).")
        args = parser.parse_args()
        if os.path.exists(args.mdl_filename) and args.mdl_filename[-4:].upper() == '.DAT':
            process_mdl(args.mdl_filename)
    else:
        mdl_filenames = [x for x in glob.glob('*.DAT') if not x == 'BASEBONES.DAT']
        mdl_filenames = [x for x in mdl_filenames if os.path.isdir(x[:-4])]
        for i in range(len(mdl_filenames)):
            process_mdl(mdl_filenames[i])
