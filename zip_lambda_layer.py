import os
import sys
from pathlib import Path

# NOTE: psycopg2 is not packaged in the layer. It can be separately added
# Compiled code from this repo can be dropped in the root directory:
# https://github.com/jkehler/awslambda-psycopg2


def main(req_file, output_zip):
    os.system("pip3 install --upgrade pip")
    os.system("mkdir python")
    os.system(
        f"pip3 install --no-cache-dir "
        f"-r {req_file} "
        f"--platform=manylinux1_x86_64 --only-binary=:all: "
        f"-t python"
    )

    layer_zip_path = Path.cwd() / Path(output_zip)
    layer_zip_path.parent.mkdir(parents=True, exist_ok=True)
    os.system(f"zip -q -r  {layer_zip_path} python")
    os.system("rm -r python")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
