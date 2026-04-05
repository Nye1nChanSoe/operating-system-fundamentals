# Harbour Space Filesystem (HSFS)

This project implements a simple custom filesystem called **HSFS**.
It is a block-based filesystem that stores directories and files inside a single binary image.

The design is inspired by FAT and ext2, but simplified for learning purposes.

---

## Overview

* Block size: 4096 bytes
* Directory entry size: 128 bytes
* Each file/directory is stored as a directory entry (no inode layer)
* Supports direct and indirect block addressing

Files and directories are written into a single image file, similar to a `.tar` archive.

---

## How it works

### Directory Entry Format

Each entry contains:

* flags (used, directory, indirect)
* file name (max 59 bytes)
* size
* up to 16 block pointers

If a file is small, block pointers reference data directly.
If it is large, pointers reference indirect blocks which contain more block references.

---

### Storage Model

* Files are split into 4KB blocks
* Directories are stored as blocks of directory entries
* Root directory must fit into a single block (max 32 entries)

---

## Limitations

* No inode structure
* No free space tracking
* Cannot safely grow files
* Root directory limited to 32 entries
* Linear search for file lookup
* No permissions or timestamps
* No crash recovery

Because of this, HSFS behaves more like a simple archive format than a full filesystem.

---

## Usage

### Create filesystem image

```bash
python hsfs_write.py write <input_directory> <output.img>
```

Example:

```bash
python hsfs_write.py write test_dir fs.img
```

---

### Extract filesystem image

```bash
python hsfs_write.py extract <image.img> <output_directory>
```

Example:

```bash
python hsfs_write.py extract fs.img out
```

---

## Notes on Updating Files

Files can only be updated in-place:

* Existing blocks are reused
* New content must not exceed current allocation

Growing a file is not supported due to lack of free space management.

---

## Purpose

This project is mainly for understanding how filesystems work internally:

* block storage
* metadata layout
* directory traversal
* binary parsing

It is not intended for real-world usage.

---