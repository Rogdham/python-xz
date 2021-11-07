<div align="center">

# python-xz

Pure Python implementation of the XZ file format with random access support

_Leveraging the lzma module for fast (de)compression_

[![GitHub build status](https://img.shields.io/github/workflow/status/rogdham/python-xz/build/master)](https://github.com/rogdham/python-xz/actions?query=branch:master)
[![Release on PyPI](https://img.shields.io/pypi/v/python-xz)](https://pypi.org/project/python-xz/)
[![Code coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/rogdham/python-xz/search?q=fail+under&type=Code)
[![Mypy type checker](https://img.shields.io/badge/type_checker-mypy-informational)](https://mypy.readthedocs.io/)
[![MIT License](https://img.shields.io/pypi/l/python-xz)](https://github.com/Rogdham/python-xz/blob/master/LICENSE.txt)

---

[📖 Documentation](https://github.com/rogdham/python-xz/#usage)&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;[📃 Changelog](./CHANGELOG.md)

</div>

---

A XZ file can be composed of several streams and blocks. This allows for fast random
access when reading, but this is not supported by Python's builtin `lzma` module (which
would read all previous blocks for nothing).

<div align="center">

|                   |      [lzma]       |      [lzmaffi]       |      python-xz       |
| :---------------: | :---------------: | :------------------: | :------------------: |
|    module type    |      builtin      |  cffi (C extension)  |     pure Python      |
|    📄 **read**    |                   |                      |                      |
|   random access   | ❌ no<sup>1</sup> |  ✔️ yes<sup>2</sup>  |  ✔️ yes<sup>2</sup>  |
|  several blocks   |      ✔️ yes       | ✔️✔️ yes<sup>3</sup> | ✔️✔️ yes<sup>3</sup> |
|  several streams  |      ✔️ yes       |        ✔️ yes        | ✔️✔️ yes<sup>4</sup> |
|  stream padding   | ❌ no<sup>5</sup> |        ✔️ yes        |        ✔️ yes        |
|   📝 **write**    |                   |                      |                      |
|     `w` mode      |      ✔️ yes       |        ✔️ yes        |        ✔️ yes        |
|     `x` mode      |      ✔️ yes       |        ❌ no         |        ✔️ yes        |
|     `a` mode      |   ✔️ new stream   |    ✔️ new stream     |      ⏳ planned      |
| `r+`/`w+`/… modes |       ❌ no       |        ❌ no         |        ✔️ yes        |
|  several blocks   |       ❌ no       |        ❌ no         |        ✔️ yes        |
|  several streams  | ❌ no<sup>6</sup> |  ❌ no<sup>6</sup>   |        ✔️ yes        |
|  stream padding   |       ❌ no       |        ❌ no         |      ⏳ planned      |

</div>

<details>
<summary>Notes</summary>

1. Reading from a position will read the file from the very beginning
2. Reading from a position will read the file from the beginning of the block
3. Block positions available with the `block_boundaries` attribute
4. Stream positions available with the `stream_boundaries` attribute
5. Related [issue](https://bugs.python.org/issue44134)
6. Possible by manually closing and re-opening in append mode

</details>

[lzma]: https://docs.python.org/3/library/lzma.html
[lzmaffi]: https://github.com/r3m0t/backports.lzma

---

## Usage

The API is similar to [lzma]: you can use either `xz.open` or `xz.XZFile`.

### Read mode

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

Writing is only supported from the end of file. It is however possible to truncate the
file first. Note that truncating is only supported on block boundaries.

```python
>>> with xz.open('test.xz', 'w') as fout:
...     fout.write(b'Hello, world!\n')
...     fout.write(b'This sentence is still in the previous block\n')
...     fout.change_block()
...     fout.write(b'But this one is in its own!\n')
...
14
45
28
```

Advanced usage:

- Modes like `r+`/`w+`/`x+` allow to open for both read and write at the same time;
  however in the current implementation, a block with writing in progress is
  automatically closed when reading data from it.
- The `check`, `preset` and `filters` arguments to `xz.open` and `xz.XZFile` allow to
  configure the default values for new streams and blocks.
- Change block with the `change_block` method (the `preset` and `filters` attributes can
  be changed beforehand to apply to the new block).
- Change stream with the `change_stream` method (the `check` attribute can be changed
  beforehand to apply to the new stream).

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

You can open the file for writing and use the `change_block` method to create several
blocks.

Other tools allow to create XZ files with several blocks as well:

- [XZ Utils](https://tukaani.org/xz/) needs to be called with flags:

```sh
$ xz -T0 file                          # threading mode
$ xz --block-size 16M file             # same size for all blocks
$ xz --block-list 16M,32M,8M,42M file  # specific size for each block
```

- [PIXZ](https://github.com/vasi/pixz) creates files with several blocks by default:

```sh
$ pixz file
```
