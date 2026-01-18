import os
import sys

import bitmapfiles


def main():

    atexture = sys.argv[1]
    acx = int(sys.argv[2])
    acy = int(sys.argv[3])
    asx = int(sys.argv[4])
    asy = int(sys.argv[5])
    aox = int(sys.argv[6])
    aoy = int(sys.argv[7])

    sprite = bitmapfiles.extract_sprite(
        atexture, acx, acy, asx, asy, aox, aoy, "-")

    fn = r".\view.png"
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    sprite.save(fn)


if __name__ == "__main__":
    main()
