<div align="center" size="15px">

# python-xz

Pure Python implementation of the XZ file format with random access support

[![GitHub build status](https://img.shields.io/github/workflow/status/rogdham/python-xz/build/master)](https://github.com/rogdham/python-xz/actions?query=branch:master)&nbsp;[![Release on PyPI](https://img.shields.io/pypi/v/python-xz)](https://pypi.org/project/python-xz/)&nbsp;[![Code coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/rogdham/python-xz/search?q=fail+under&type=Code)&nbsp;[![MIT License](https://img.shields.io/pypi/l/python-xz)](https://github.com/Rogdham/python-xz/blob/master/LICENSE.txt)

---

[:book: Documentation](https://github.com/rogdham/python-xz/#usage)&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;[:page_with_curl: Changelog](./CHANGELOG.md)

</div>

---

A XZ file can be composed of several streams and blocks. This allows for random access
when reading, but this is not supported by Python's builtin `lzma` module, which would
read all previous blocks for nothing.

|                          |           [lzma]            |          [lzmaffi]          |       python-xz        |
| -----------------------: | :-------------------------: | :-------------------------: | :--------------------: |
|              Module type |           builtin           |     cffi (C extension)      |         native         |
| **Random access (read)** | :heavy_multiplication_x: no |   :heavy_check_mark: yes    | :heavy_check_mark: yes |
|   Several streams (read) |   :heavy_check_mark: yes    |   :heavy_check_mark: yes    | :heavy_check_mark: yes |
|  Several streams (write) | :heavy_multiplication_x: no | :heavy_multiplication_x: no |  :hourglass: planned   |
|    Several blocks (read) |   :heavy_check_mark: yes    |   :heavy_check_mark: yes    | :heavy_check_mark: yes |
|   Several blocks (write) | :heavy_multiplication_x: no | :heavy_multiplication_x: no |  :hourglass: planned   |
|    Stream padding (read) | :heavy_multiplication_x: no |   :heavy_check_mark: yes    | :heavy_check_mark: yes |
|   Stream padding (write) | :heavy_multiplication_x: no | :heavy_multiplication_x: no |  :hourglass: planned   |

[lzma]: https://docs.python.org/3/library/lzma.html
[lzmaffi]: https://github.com/r3m0t/backports.lzma

---

## Usage

### Read mode

The API is similar to [lzma]: you can use either `xz.open` or `xz.XZFile`.

```python
>>> with xz.open('example.xz') as fin:
...     fin.read(18)
...     fin.stream_boundaries  # 2 streams
...     fin.block_boundaries   # 4 blocks in first stream, 2 blocks in second stream
...     fin.seek(1000)
...     fin.read(31)
...
b'Hello, world! \xf0\x9f\x91\x8b'
[0, 2000]
[0, 500, 1000, 1500, 2000, 3000]
1000
b'\xe2\x9c\xa8 Random access is fast! \xf0\x9f\x9a\x80'
```

Opening in text mode works as well, but notice that seek arguments as well as boundaries
are still in bytes (just like with `lzma.open`).

```python
>>> with xz.open('example.xz', 'rt') as fin:
...     fin.read(15)
...     fin.stream_boundaries
...     fin.block_boundaries
...     fin.seek(1000)
...     fin.read(26)
...
'Hello, world! 👋'
[0, 2000]
[0, 500, 1000, 1500, 2000, 3000]
1000
'✨ Random access is fast! 🚀'
```

### Write mode

_This mode is not available yet._

---

## FAQ

### How does random-access works?

XZ files are made of a number of streams, and each stream is composed of a number of
block. This can be seen with `xz --list`:

```sh
$ xz --list file.xz
Strms  Blocks   Compressed Uncompressed  Ratio  Check   Filename
    1      13     16.8 MiB    297.9 MiB  0.056  CRC64   file.xz
```

To read data from the middle of the 10th block, we will decompress the 10th block from
its start it until we reach the middle (and drop that decompressed data), then returned
the decompressed data from that point.

Choosing the good block size is a tradeoff between seeking time during random access and
compression ratio.

### How can I create XZ files optimized for random-access?

[XZ Utils](https://tukaani.org/xz/) can create XZ files with several blocks:

```sh
$ xz -T0 file                          # threading mode
$ xz --block-size 16M file             # same size for all blocks
$ xz --block-list 16M,32M,8M,42M file  # specific size for each block
```

[PIXZ](https://github.com/vasi/pixz) creates files with several blocks by default:

```sh
$ pixz file
```
