import os
import subprocess
import zipfile
import urllib.request
import shutil
from enum import Enum
import json

class OSType(Enum):
    WINDOWS = 1,
    MAC = 2,
    LINUX = 3

class BuildTask:
    def __init__(self, downloadFileName: str, osType: OSType, releaseName: str):
        self.downloadFileName = downloadFileName
        self.osType = osType
        self.releaseName = releaseName

def downloadFile(url, outputFileName):
    print(f"Downloading {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(url) as u:
        with open(outputFileName, "wb") as f:
            while True:
                data = u.read(4096)
                if data:
                    f.write(data)
                else:
                    break

def call(args, **kwargs):
    print("running: {}".format(args))
    retcode = subprocess.call(args, shell=True, **kwargs)  # use shell on windows
    if retcode != 0:
        # don't print args here to avoid leaking secrets
        raise Exception(f"ERROR: The last call() failed with retcode {retcode}")

# Determine the latest file prefix for the repo, e.g. "ponscr-4.0.0-"
latest_file_prefix = None
tags_url = "https://api.github.com/repos/07th-mod/ponscripter-fork/tags"
req = urllib.request.Request(tags_url)
with urllib.request.urlopen(tags_url) as u:
    j = json.loads(u.read())

    latest_tag_info = j[0]

    latest_tag_name = latest_tag_info['name']
    latest_file_prefix = f"ponscr-{latest_tag_name.lstrip("v")}-"


print(">>> Running initial setup...")
ponscripterForkLatestReleaseURL = "https://github.com/07th-mod/ponscripter-fork/releases/latest/download/"

buildTasks = [
    # Note: names do not include repo url or prefix
    BuildTask("windows.zip", OSType.WINDOWS, "windows"),
    BuildTask("windows-steam.zip", OSType.WINDOWS, "windows-steam"),
    BuildTask("osx.zip", OSType.MAC, "osx"),
    BuildTask("osx-steam.zip", OSType.MAC, "osx-steam"),
    BuildTask("linux.zip", OSType.LINUX, "linux"),
    BuildTask("linux-steam.zip", OSType.LINUX, "linux-steam"),
    BuildTask("linux-nodep.zip", OSType.LINUX, "linux-nodep"),
]

resourceHackerZip = "resource_hacker.zip"
resourceHackerExeName = "ResourceHacker.exe"
downloadFile("https://github.com/07th-mod/ponscripter-umineko/releases/download/v0.0.0/resource_hacker.zip", "resource_hacker.zip")
with zipfile.ZipFile(resourceHackerZip, 'r') as zip_ref:
    zip_ref.extract(resourceHackerExeName)

macBaseZipName = "mac.zip"
downloadFile("https://github.com/07th-mod/ponscripter-umineko/releases/download/v0.0.0/umineko-mac-exe-base.zip", macBaseZipName)

for task in buildTasks:
    # Download the file
    downloadURL = f"{ponscripterForkLatestReleaseURL}{latest_file_prefix}{task.downloadFileName}"
    downloadFile(downloadURL, task.downloadFileName)

    # Extract the archive
    originalExecutableName = "ponscr.exe" if task.osType == OSType.WINDOWS else "ponscr"
    with zipfile.ZipFile(task.downloadFileName, 'r') as zip_ref:
        zip_ref.extract(originalExecutableName)

    # If building windows exe, embed umineko icon instead of POnscripter icon
    if task.osType == OSType.WINDOWS:
        call([resourceHackerExeName,
            "-open", originalExecutableName,
            "-save", originalExecutableName,
            "-action", "addskip",
            "-res", "icons/beato.ico",
            "-mask", "ICONGROUP,MAINICON,"])

    if task.osType == OSType.WINDOWS:
        copyTargets = ["Umineko1to4.exe", "Umineko5to8.exe"]
    elif task.osType == OSType.LINUX:
        copyTargets = ["Umineko1to4", "Umineko5to8"]
    elif task.osType == OSType.MAC:
        copyTargets = ["Umineko1to4.app/Contents/MacOS/Umineko4", "Umineko5to8.app/Contents/MacOS/Umineko8"]
    else:
        raise Exception("Unknown type")

    arcNames = ["question", "answer"]
    for arcName, target in zip(arcNames, copyTargets):
        # Figure out what the final outpt zip file will be called (excluding file extension)
        zipName = f"umineko-{task.releaseName}-{arcName}"
        print(f">>> Producing {zipName}.zip...")

        zipPath = f"{zipName}.zip"
        if os.path.exists(zipPath):
            print("Warning: Output Zip file already exists - deleting it...")
            os.remove(zipPath)

        # Prepare output dir
        stagingFolder = f"{zipName}-output"
        os.makedirs(stagingFolder, exist_ok=True)

        if task.osType == OSType.MAC:
            with zipfile.ZipFile(macBaseZipName, 'r') as zip_ref:
                zip_ref.extractall(stagingFolder)

        # copy file to staging dir
        shutil.copy(originalExecutableName, os.path.join(stagingFolder, target))

        # zip the staging dir into final zip to be uploaded to release
        shutil.make_archive(zipName, 'zip', stagingFolder)

        # Delete the staging folder
        shutil.rmtree(stagingFolder)

    # Delete the original ponscripter exe
    os.remove(originalExecutableName)

    # Delete the downloaded zip file
    os.remove(task.downloadFileName)

# Delete Resource Hacker files
os.remove(resourceHackerZip)
os.remove(resourceHackerExeName)
resourceHackerIni = "ResourceHacker.ini"
if os.path.exists(resourceHackerIni):
    os.remove(resourceHackerIni)

# Delete the mac zip file
os.remove(macBaseZipName)
