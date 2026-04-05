from dataclasses import dataclass
import struct
import io
import os
import math
import sys
import random

# flags
IS_USED = 1
IS_DIR = 2
IS_INDIRECT = 4

BLOCK_SIZE = 4096
BLOCKS_IN_DIRECTORY_ENTRY = 16
BLOCKS_IN_INDIRECT_BLOCK = BLOCK_SIZE // 4
INDIRECT_BLOCK_FORMAT = "<1024I"


# HSFS
# The Harbour Space Filesystem (HSFS) is a simple block-based filesystem where all data is stored in fixed-size blocks of 4096 bytes.
# It doesn't use inode structure, each file or directory is represented directly by a directory entry, which contains both metadata and block pointers.

# Directory Entry Structure
# [B][NAME][SIZE][BLOCK_POINTERS]

# 1  bytes    -> Flag
# 59 bytes    -> filename
# 4  bytes    -> size
# 16x4 bytes  -> block pointers

# if file < 16 blocks:
#   entry pointing to blocks directly
# if file > 16 blocks
#   entry -> indirect blocks -> data blocks
# EACH indirect block stores 1024 direct pointers

# Directory Storage
# Directories are stored as files containing directory entries
#   Entry size = 128 bytes
#   Block size = 4096 bytes
#   Entries per block = 32

# Must occupy extact 1 block
# Maximum 32 blocks

# Travesal
# /a/b/file.txt
# Read root (block 0)
# Find "a"
# Follow its block
# Find "b"
# Repeat

# Limitations
#   - No inode structure
#   - No free space finding
#   - Root limited to 32 entries
#   - Max file size ~64MB
#   - Filename limited to 59 bytes
#   - Linear search space for lookup O(n)
#   - No permission | no timestamp | no ownership
#   - No crash recovery (journaling)

# nyeinchan ~/Desktop/hs-operating-system/hsfs [master] $ python hsfs_write.py extract hsfs.img out
# nyeinchan ~/Desktop/hs-operating-system/hsfs [master] $ find out -type f -exec wc -c {} \;
#   250096 out/root/subdir/winlin.png
#     8400 out/root/crrry/small_file.txt

# The logical file size field is necessary because data blocks are fixed at 4096 bytes. 
# Without it, the final block would contain padding or leftover data, making it impossible to 
# determine the actual end of file content.

@dataclass
class DirEntry:
    name: str
    is_dir: bool
    is_indirect: bool
    size: int
    entry_blocks: list[int]


DIR_ENTRY_SIZE = 128
DIR_ENTRY_FORMAT = "<B59sI16I"


def add_entry(directory_block: io.BytesIO, entry: DirEntry) -> bool:
    offset = 0
    while offset < BLOCK_SIZE:
        flags, name_bytes, size, *starting_blocks = struct.unpack_from(
            "B59sI16I", directory_block, offset
        )
        if flags & IS_USED == 0:
            break
        offset += DIR_ENTRY_SIZE
    if offset >= BLOCK_SIZE:
        return False
    write_entry(directory_block, offset, entry)
    return True


def write_entry(directory_block: io.BytesIO, offset: int, entry: DirEntry):
    flags = IS_USED
    if entry.is_dir:
        flags |= IS_DIR
    if entry.is_indirect:
        flags |= IS_INDIRECT

    name_bytes = entry.name.encode("utf-8")
    starting_blocks = entry.entry_blocks
    starting_blocks += [0] * (BLOCKS_IN_DIRECTORY_ENTRY - len(entry.entry_blocks))

    struct.pack_into(
        "B59sI16I",
        directory_block,
        offset,
        flags,
        name_bytes,
        entry.size,
        *starting_blocks
    )


def convert_to_indirect_blocks_if_necessary(entry: DirEntry, target_file: io.FileIO, next_block: int) -> int:
    if len(entry.entry_blocks) > BLOCKS_IN_DIRECTORY_ENTRY:
        all_blocks = entry.entry_blocks
        entry.is_indirect = True
        entry.entry_blocks = []

        offset = 0
        while offset < len(all_blocks):
            entry.entry_blocks.append(next_block)
            blocks_page = all_blocks[offset:offset + BLOCKS_IN_INDIRECT_BLOCK]
            blocks_page += [0] * (BLOCKS_IN_INDIRECT_BLOCK - len(blocks_page))

            target_file.seek(BLOCK_SIZE * next_block)
            target_file.write(struct.pack(INDIRECT_BLOCK_FORMAT, *blocks_page))

            next_block += 1
            offset += BLOCKS_IN_INDIRECT_BLOCK

        return next_block + 1

    return next_block


def convert_directory_to_hsfs_recursively(directory: str, target_file: io.FileIO, next_block: int):
    target_file.seek(BLOCK_SIZE * next_block)
    entries_per_block = BLOCK_SIZE // DIR_ENTRY_SIZE

    entries = list(os.scandir(directory))
    dir_blocks_count = math.ceil(len(entries) / entries_per_block)

    if next_block == 0 and dir_blocks_count != 1:
        raise Exception("root directory data should occupy exactly one block")

    dir_block_start = next_block
    empty_block = bytearray(BLOCK_SIZE)

    for _ in range(dir_blocks_count):
        target_file.write(empty_block)

    next_block += dir_blocks_count
    my_entries = []

    for e in entries:
        if e.is_dir():
            next_block, dir_size, all_blocks = convert_directory_to_hsfs_recursively(e.path, target_file, next_block)
            my_entry = DirEntry(e.name, True, False, dir_size, all_blocks)
        else:
            file_size = os.path.getsize(e.path)
            file_blocks_count = math.ceil(file_size / BLOCK_SIZE)

            block_ids = list(range(next_block, next_block + file_blocks_count))
            next_block += file_blocks_count
            random.shuffle(block_ids)

            data = open(e.path, "rb")
            buffer = bytearray(BLOCK_SIZE)

            for i in range(file_blocks_count):
                data.readinto(buffer)
                block_id = block_ids[i]
                target_file.seek(BLOCK_SIZE * block_id)
                target_file.write(buffer)

            my_entry = DirEntry(e.name, False, False, file_size, block_ids)

        next_block = convert_to_indirect_blocks_if_necessary(my_entry, target_file, next_block)
        my_entries.append(my_entry)

    dir_blocks = []

    for b_index in range(dir_blocks_count):
        block = bytearray(BLOCK_SIZE)
        entries = my_entries[b_index * entries_per_block:(b_index+1) * entries_per_block]

        for e in entries:
            assert(add_entry(block, e))

        target_file.seek((dir_block_start + b_index) * BLOCK_SIZE)
        target_file.write(block)
        dir_blocks.append(dir_block_start + b_index)

    return (next_block, DIR_ENTRY_SIZE * len(my_entries), dir_blocks)


def read_block(f, block_id):
    f.seek(block_id * BLOCK_SIZE)
    return f.read(BLOCK_SIZE)


def parse_entries(block):
    entries = []
    for i in range(0, BLOCK_SIZE, DIR_ENTRY_SIZE):
        chunk = block[i:i+DIR_ENTRY_SIZE]
        flags, name, size, *blocks = struct.unpack(DIR_ENTRY_FORMAT, chunk)

        if not (flags & IS_USED):
            continue

        name = name.split(b'\x00')[0].decode()
        blocks = [b for b in blocks if b != 0]

        entries.append({
            "name": name,
            "is_dir": bool(flags & IS_DIR),
            "is_indirect": bool(flags & IS_INDIRECT),
            "size": size,
            "blocks": blocks
        })

    return entries


def resolve_blocks(f, entry):
    if not entry["is_indirect"]:
        return entry["blocks"]

    real_blocks = []

    for ib in entry["blocks"]:
        block = read_block(f, ib)
        pointers = struct.unpack(INDIRECT_BLOCK_FORMAT, block)
        real_blocks.extend([p for p in pointers if p != 0])

    return real_blocks


def extract_file(f, entry, output_path):
    blocks = resolve_blocks(f, entry)
    data = b""

    for b in blocks:
        data += read_block(f, b)

    data = data[:entry["size"]]

    with open(output_path, "wb") as out:
        out.write(data)


def extract_dir(f, block_id, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    block = read_block(f, block_id)
    entries = parse_entries(block)

    for entry in entries:
        path = os.path.join(output_dir, entry["name"])

        if entry["is_dir"]:
            sub_blocks = resolve_blocks(f, entry)
            for b in sub_blocks:
                extract_dir(f, b, path)
        else:
            extract_file(f, entry, path)


def update_file(img_path, entry, new_data):
    with open(img_path, "r+b") as f:
        blocks = resolve_blocks(f, entry)

        needed_blocks = math.ceil(len(new_data) / BLOCK_SIZE)

        if needed_blocks > len(blocks):
            raise Exception("Cannot grow file (no free space management)")

        for i, block_id in enumerate(blocks):
            f.seek(block_id * BLOCK_SIZE)

            chunk = new_data[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE]
            chunk += b'\x00' * (BLOCK_SIZE - len(chunk))

            f.write(chunk)


if __name__ == "__main__":
    if sys.argv[1] == "write":
        convert_directory_to_hsfs_recursively(sys.argv[2], open(sys.argv[3], "wb"), 0)

    elif sys.argv[1] == "extract":
        with open(sys.argv[2], "rb") as f:
            extract_dir(f, 0, sys.argv[3])