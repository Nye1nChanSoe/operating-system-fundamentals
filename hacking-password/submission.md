### Memory Analysis of password.arm64.elf

#### System setup and initial check

First I run the uname command to display the information of my system

```bash
uname -m
```

It shows `aarch64` so basically ARM64.

So I will be using `password.arm64.elf` binaries to examine further.

---

#### Running program and locating process

I run the program:

```bash
./password.arm64.elf
```

Then check the PID using:

```bash
ps -Af | grep "password"
```

---

#### Inspecting memory layout

Then I check the virtual memory layout of this process using:

```bash
cat /proc/<pid>/maps
```

My intuition is to examine these addresses further:

```
aaaada960000-aaaada961000 r--p 00000000 00:2d 26537  /workspace/hacking-password/password.arm64.elf
aaaada961000-aaaada962000 rw-p 00001000 00:2d 26537  /workspace/hacking-password/password.arm64.elf
aaaadb6fc000-aaaadb71d000 rw-p 00000000 00:00 0      [heap]
ffffc1eb9000-ffffc1eda000 rw-p 00000000 00:00 0      [stack]
```

First two contain constants and variables so the password could be in there.

Heap is the MUST place to check since runtime data probably lives here and allocated memory for password.

Stack is least likely but I will check if I cannot find in above these 3 places.

---

#### Attaching debugger and observing runtime behavior

To check with GNU debugger for this process:

```bash
gdb -p <pid>
```

I observed this:

```
0x0000ffff85961244 in __GI___libc_read (fd=0, buf=0xaaaae22d52c0, nbytes=1024)
```

When I attached gdb, I observed the program executing `read()`, storing user input at address `0xaaaae22d52c0`.

By checking `/proc/<pid>/maps`, I confirmed this address lies within the heap, indicating that input is stored in dynamically allocated memory.

Since the program must compare user input with the correct password, both are likely present in memory at the same time.

Based on this, I focused on the heap region.

---

#### Dumping heap memory

I dumped the heap using gdb:

```gdb
dump memory heap.dump 0xaaaae22d5000 0xaaaae22f6000
```

Then searched for readable strings:

```bash
strings heap.dump
```

I found:

```
pwAW96B6
```

---

#### Locating exact memory address

I want to find the exact memory location so I run:

```gdb
find 0xaaaae22d5000, 0xaaaae22f6000, "pwAW96B6"
```

Result:

```
0xaaaae22d52a0
```

Then I verify:

```gdb
x/s 0xaaaae22d52a0
```

```
"pwAW96B6"
```

Then I check raw bytes:

```gdb
x/16bx 0xaaaae22d52a0
```

```
0x70 0x77 0x41 0x57 0x39 0x36 0x42 0x36
0x00 0x00 0x00 0x00 ...
```

So the password is ASCII encoded null terminated string.

---

#### Verifying using hexdump

hexdump also helps:

```bash
hexdump -C heap.dump
```


```
00000000  00 00 00 00 00 00 00 00  91 02 00 00 00 00 00 00  |................|
00000010  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
*
00000290  00 00 00 00 00 00 00 00  21 00 00 00 00 00 00 00  |........!.......|
000002a0  70 77 41 57 39 36 42 36  00 00 00 00 00 00 00 00  |pwAW96B6........|
000002b0  00 00 00 00 00 00 00 00  11 04 00 00 00 00 00 00  |................|
000002c0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
*
000006c0  00 00 00 00 00 00 00 00  41 09 02 00 00 00 00 00  |........A.......|
000006d0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
```

This confirms the password in the heap dump.

---

#### Conclusion

The password is stored in plaintext in heap memory as a null-terminated ASCII string.

This means it can be extracted directly from memory using debugging tools.