#!/usr/bin/env python3
import json
import os
import shutil
import subprocess

GPU_DEV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "gpu", "devcontainer.json")
)
NOGPU_DEV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "nogpu", "devcontainer.json")
)

PRETTIER_CMD = [
    ["prettier"],
    ["pnpx", "prettier"],
    ["bun", "x", "prettier"],
    ["bunx", "prettier"],
    ["npx", "prettier"],
]


def find_prettier():
    for cmd in PRETTIER_CMD:
        if shutil.which(cmd[0]) is not None:
            return cmd
    return None


def gpu_from_nogpu(nogpu_json):
    """
    Converts a GPU devcontainer.json to a no-GPU devcontainer.json.
    difference:
        - no --gpus=all
        - has NVIDIA_VISIBLE_DEVICES and NVIDIA_DRIVER_CAPABILITIES
    """
    gpu_json = nogpu_json.copy()
    if "runArgs" not in gpu_json:
        gpu_json["runArgs"] = []
    elif not isinstance(gpu_json["runArgs"], list):
        raise ValueError("runArgs must be a list")

    gpu_json["runArgs"].append("--gpus=all")

    if "containerEnv" not in gpu_json:
        gpu_json["features"] = {}
    elif not isinstance(gpu_json["containerEnv"], dict):
        raise ValueError("containerEnv must be a dict")

    if "NVIDIA_VISIBLE_DEVICES" not in gpu_json["containerEnv"]:
        gpu_json["containerEnv"]["NVIDIA_VISIBLE_DEVICES"] = "all"
    if "NVIDIA_DRIVER_CAPABILITIES" not in gpu_json["containerEnv"]:
        gpu_json["containerEnv"]["NVIDIA_DRIVER_CAPABILITIES"] = "compute,utility"

    return gpu_json


def save_gpu_json():
    with open(NOGPU_DEV, "r") as f:
        nogpu_json = json.load(f)
    gpu_json = gpu_from_nogpu(nogpu_json)
    with open(GPU_DEV, "w") as f:
        json.dump(gpu_json, f, indent=4)


def main():
    save_gpu_json()
    prettier_cmd = find_prettier()
    if prettier_cmd is not None:
        print(f"Found prettier: {prettier_cmd[0]}")
        subprocess.run(
            prettier_cmd + ["--write", GPU_DEV, "--tab-width", "4"], check=True
        )
    else:
        print("No prettier found")


if __name__ == "__main__":
    main()
