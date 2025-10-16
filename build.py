"""
Build script for creating redistributable package using PyInstaller.
"""
import os
import subprocess
import sys
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from consts import APP_NAME, APP_VERSION

def build():
  print(f"Build {APP_NAME} {APP_VERSION} package...")

  app_name = APP_NAME.replace(" ", "-").lower() + "-" + APP_VERSION
  dist_dir = "dist"
  app_dir = f"{dist_dir}/{app_name}"
  config_file = "board_config.ini"

  cmd = [
    "pyinstaller",
    #"--onefile",                    # Single executable file
    "--onedir",                     # Unpacked directory
    #"--windowed",                   # No console window (GUI only)
    "--name", app_name,             # Executable name
    "--clean",                      # Clean cache before building
    "--noconfirm",                  # Don't ask overwriting confirmation
    "--icon", "img/main.ico",       # Executable file icon
    "--add-data", "img;img",        # Include img directory in build
    #"--version-file", "TODO"
    "main.py"
  ]
  subprocess.run(cmd, check=True)

  print("\nCopy additional files...")
  shutil.copyfile(config_file, f"{app_dir}/{config_file}")

  print("\nPack to single archive...")
  # Needs to be here to have a proper directory structure inside the zip
  # There will be one app directory e.g. pulse-inspector-0.0.1
  # it can be easily dragged from the archive to a target folder
  os.chdir(dist_dir)
  zip_name = f"{dist_dir}/{app_name}.zip"
  with ZipFile(f"../{zip_name}", mode = 'w', compression = ZIP_DEFLATED) as z:
    for dirname, subdirs, filenames in os.walk(app_name):
      for filename in filenames:
        z.write(os.path.join(dirname, filename))

  print("\n" + "="*60)
  print("Build successful!")
  print("="*60)
  print(f"\nPackage location: {zip_name}")

if __name__ == "__main__":
  build()
