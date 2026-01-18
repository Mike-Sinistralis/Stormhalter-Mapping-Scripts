import os
import sys
from PIL import Image

import bitmapfiles
from db_config import get_connection

DEBUG = False


def main():
    if DEBUG:
        print("arguments", sys.argv)

    conn = get_connection()

    tss = conn.cursor()

    if sys.argv[1] == "V":
        sql = """\
            select 0 as tx, 0 as ty, render,
                texture, cx, cy, sx, sy, ox, oy, color
            from accessview
            order by render
            """
        tss.execute(sql)

        tlx = -1
        tly = -1
        brx = 2
        bry = 2

    else:  # T
        asrno = int(sys.argv[2])
        atx = int(sys.argv[3])
        aty = int(sys.argv[4])
        abase = int(sys.argv[5])
        awall = int(sys.argv[6])
        adoor = int(sys.argv[7])

        tlx = atx - 3
        tly = aty - 3
        brx = atx + 4
        bry = aty + 4

        sql = """\
            select rt.tx, rt.ty, bs.render, tc.color,
                tb.texture, tb.cx, tb.cy, tb.sx, tb.sy, tb.ox, tb.oy
            from regiontile as rt
            inner join tilecomponent as tc
                on tc.rtno = rt.rtno
            inner join componentterrain as ct
                on ct.tcno = tc.tcno
            inner join terraintexture as tt
                on tt.terrainid = ct.terrainid
            inner join texturebitmap as tb
                on tb.ttno = tt.ttno
            inner join bitmapsprites as bs
                on bs.texture = tb.texture
                and bs.cx = tb.cx
                and bs.cy = tb.cy
            where rt.srno = %s
            and (mod(ct.base / %s, 2) <> 0
            or mod(ct.wall / %s, 2) <> 0
            or mod(ct.door / %s, 2) <> 0)

            and rt.tx between %s and %s
            and rt.ty between %s and %s

            order by rt.tx, rt.ty, bs.render, tc.tcno
            """
        val = (asrno, abase, awall, adoor, tlx, brx, tly, bry)
        tss.execute(sql, val)

    sx = (brx - tlx + 1) * 110 + 90
    sy = (bry - tly + 1) * 110 + 90
    new = Image.new(mode="RGBA", size=(sx, sy), color=(0, 0, 0, 0))

    while True:
        ts = tss.fetchone()
        if not ts:
            break
        if DEBUG:
            print("ts", ts)
        x = (ts["tx"] - tlx) * 110
        y = (ts["ty"] - tly) * 110
        sprite = bitmapfiles.extract_sprite(
            ts["texture"], ts["cx"], ts["cy"],
            ts["sx"], ts["sy"], ts["ox"], ts["oy"], ts["color"]
            )
        box = (x, y, x + sprite.size[0], y + sprite.size[1])
        new.paste(sprite, box, sprite)

    new = new.crop((0, 0, sx - 110, sy - 110))
    fn = r".\view.png"
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    new.save(fn)


if __name__ == "__main__":
    main()
