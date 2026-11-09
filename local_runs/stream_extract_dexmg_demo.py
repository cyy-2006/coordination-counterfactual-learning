"""Extract one DexMimicGen episode from a remote HDF5 file via HTTP ranges."""

from __future__ import annotations

import argparse
import io
import os
import subprocess
from collections import OrderedDict

import h5py
import requests


class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url: str, size: int | None = None, block_size: int = 8 * 1024 * 1024, max_blocks: int = 16):
        self.url = url
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.session = requests.Session()
        self.size = size
        if self.size is None:
            probe = self.session.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
            probe.raise_for_status()
            content_range = probe.headers.get("Content-Range")
            if probe.status_code != 206 or not content_range:
                raise RuntimeError("Server did not honor HTTP byte ranges")
            self.size = int(content_range.rsplit("/", 1)[1])
        self.pos = 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            target = offset
        elif whence == os.SEEK_CUR:
            target = self.pos + offset
        elif whence == os.SEEK_END:
            target = self.size + offset
        else:
            raise ValueError(f"Unsupported whence {whence}")
        if target < 0:
            raise ValueError("Negative seek")
        self.pos = target
        return self.pos

    def _block(self, index: int) -> bytes:
        if index in self.cache:
            data = self.cache.pop(index)
            self.cache[index] = data
            return data
        start = index * self.block_size
        end = min(self.size - 1, start + self.block_size - 1)
        command = [
            "curl.exe", "-L", "--fail", "--silent", "--show-error",
            "--range", f"{start}-{end}", self.url,
        ]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE)
        data = result.stdout
        expected = end - start + 1
        if len(data) != expected:
            raise RuntimeError(f"Expected {expected} bytes, received {len(data)}")
        self.cache[index] = data
        while len(self.cache) > self.max_blocks:
            self.cache.popitem(last=False)
        print(f"fetched block {index}: {len(data) / 1024 / 1024:.1f} MB", flush=True)
        return data

    def read(self, size=-1):
        if self.pos >= self.size:
            return b""
        if size is None or size < 0:
            size = self.size - self.pos
        size = min(size, self.size - self.pos)
        parts = []
        remaining = size
        while remaining:
            block_index = self.pos // self.block_size
            offset = self.pos % self.block_size
            block = self._block(block_index)
            take = min(remaining, len(block) - offset)
            parts.append(block[offset : offset + take])
            self.pos += take
            remaining -= take
        return b"".join(parts)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def copy_attrs(src, dst):
    for key, value in src.attrs.items():
        dst.attrs[key] = value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--episode", default=None)
    parser.add_argument("--size", type=int, default=None)
    args = parser.parse_args()

    remote = HTTPRangeReader(args.url, size=args.size)
    with h5py.File(remote, "r") as source:
        print("root keys:", list(source.keys()), flush=True)
        data = source["data"]
        episode = args.episode or "demo_0"
        src_demo = data[episode]
        print("episode:", episode, "keys:", list(src_demo.keys()), flush=True)
        print("actions:", src_demo["actions"].shape, "states:", src_demo["states"].shape, flush=True)

        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with h5py.File(args.output, "w") as target:
            dst_data = target.create_group("data")
            copy_attrs(data, dst_data)
            dst_demo = dst_data.create_group(episode)
            copy_attrs(src_demo, dst_demo)
            for name in ("actions", "states", "rewards", "dones"):
                if name in src_demo:
                    dst_demo.create_dataset(name, data=src_demo[name][...], compression="gzip")
            if "action_dict" in src_demo:
                source.copy(src_demo["action_dict"], dst_demo, name="action_dict")
            dst_data.attrs["source_file_size"] = remote.size
            dst_data.attrs["source_episode"] = episode
    print("saved:", args.output, flush=True)


if __name__ == "__main__":
    main()
