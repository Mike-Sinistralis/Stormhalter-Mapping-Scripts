import os
from operator import itemgetter
import tkinter as tk
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk

import bitmapfiles
from regiontiles import tileadjust
from db_config import get_connection


def process_moves():
    global trace, data, index, conn
    move = 0
    srno = None
    px = None
    py = None
    for index in range(len(data) - 14):
        if (data[index:index+4] != bytes.fromhex("00003D00")
        or data[index+5] != 0x08):
            continue
        direction = data[index+4]
        mask = data[index+6:index+14]
        index += 14
        move += 1

        print(file=trace)
        if mask == bytes.fromhex("FFFFFFFFFFFFFFFF"):
            # Generate transition view and prompt for coordinates
            transition_img = None
            if srno is not None and px is not None:
                transition_img = generate_transition_view(srno, px, py)
            srxy = get_start_coords(transition_img)
            if not srxy:
                return
            sid, rid, px, py = srxy
            msg = f"move:{move} sid:{sid}, rid:{rid}, px:{px}, py:{py}" + \
                f" dir:{direction:2X}"
            print(msg, file=trace)
            print(msg)
            srno = segment_region(sid, rid)
            trace.flush()
            # Skip process_tiles for transitions - the FFFFFFFF mask just signals
            # a region change, not actual tile data
            continue
        else:
            px += (direction & 0x0f) - 4
            py += (direction >> 4 & 0x0f) - 4
            print(f"move:{move} px:{px} py:{py} dir:{direction:2X}"
                f" m:{''.join(f'{b:02X}' for b in mask)}", file=trace)
        trace.flush()
        process_tiles(srno, mask, px, py)
        conn.commit()


def process_tiles(srno, mask, px, py):
    global trace, data, index
    ty = py - 3
    for m in mask:
        print(f"m:{m:02X} index:{index:06X}", file=trace)
        tx = px - 3
        for bit in (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80):
            if m & bit == 0:
                tx = tx + 1
                continue

            tiletype = data[index]
            print(f"  tx:{tx} ty:{ty} type:{tiletype:02X}", end="", file=trace)
            index += 1

            if tiletype not in (
                0x00, 0x02, 0x04, 0x05, 0x06, 0x07,
                0x08, 0x0A, 0x0C, 0x0D, 0x0E, 0x0F,
                0x12, 0x16, 0x17, 0x1A, 0x1E, 0x1F,
                0x22, 0x26, 0x27, 0x2A, 0x2E, 0x2F,
                0x45, 0x47, 0x4D, 0x4F,
                0x57, 0x5F,
                0x67, 0x6F
            ):
                print(file=trace)
                trace.flush()
                msg = f"Bad tiletype {tiletype:02X}: " + \
                    " ".join(f"{x:02X}"
                        for x in data[index:index + 20])
                raise ValueError(msg)

            if tiletype in (
                0x00, 0x02, 0x08, 0x0A,
                0x12, 0x1A,
                0x22, 0x2A
            ):
                print(file=trace)
                tx = tx + 1
                continue
            rtno = region_tile(srno, tx, ty)
            terrcnt = data[index]
            index += 1

            print(f" count:{terrcnt:02X}", end="", file=trace)
            terrainlist = load_terrainlist(tiletype, terrcnt)

            terrainlist.sort(key=itemgetter(1, 0))  # sort color, terrainid
            colorsave = None
            for terrainid, color in terrainlist:
                if (colorsave is None
                or color != colorsave):
                    tcno = tile_component(rtno, color)
                    colorsave = color
                component_terrain(tcno, terrainid)
            tileadjust(cur, rtno)
            tx = tx + 1
        ty = ty + 1


def load_terrainlist(tiletype, terrcnt):
    global trace, data, index
    terrainlist = []
    for _ in range(terrcnt):
        terrainid = int.from_bytes(
            data[index:index+2],
            byteorder="little")
        index += 2
        print(f" tid:{terrainid}", end="", file=trace)
        color = "-"
        if tiletype in (
            0x0C, 0x0D, 0x0E, 0x0F,
            0x1E, 0x1f,
            0x2E, 0x2F,
            0x4D, 0x4F,
            0x5F,
            0x6F
        ):
            color = data[index:index+4]
            index += 4
            if color == bytes.fromhex("FFFFFFFF"):
                color = "-"
            else:
                color = ", ".join(f"{c}" for c in color)
                print(f" color:{color}", end="", file=trace)
        terrainlist.append([terrainid, color])

    if tiletype in (
        0x05, 0x0D,
        0x45, 0x4d
    ):
        movecost = data[index]
        index += 1
        print(f" move:{movecost:02X}", end="", file=trace)
    print(file=trace)
    return terrainlist


def generate_transition_view(srno, px, py):
    """Generate a map image centered on the last position before a transition.
    Returns the PIL Image object for display in the dialog."""
    global conn

    # Define view bounds (7x7 tiles centered on position)
    tlx = px - 3
    tly = py - 3
    brx = px + 3
    bry = py + 3

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
        and (mod(ct.base, 2) <> 0
        or mod(ct.wall, 2) <> 0
        or mod(ct.door, 2) <> 0)
        and rt.tx between %s and %s
        and rt.ty between %s and %s
        order by rt.tx, rt.ty, bs.render, tc.tcno
        """
    tss = conn.cursor()
    tss.execute(sql, (srno, tlx, brx, tly, bry))

    # Create image
    sx = (brx - tlx + 1) * 110 + 90
    sy = (bry - tly + 1) * 110 + 90
    new = Image.new(mode="RGBA", size=(sx, sy), color=(0, 0, 0, 0))

    while True:
        ts = tss.fetchone()
        if not ts:
            break
        x = (ts["tx"] - tlx) * 110
        y = (ts["ty"] - tly) * 110
        sprite = bitmapfiles.extract_sprite(
            ts["texture"], ts["cx"], ts["cy"],
            ts["sx"], ts["sy"], ts["ox"], ts["oy"], ts["color"]
        )
        box = (x, y, x + sprite.size[0], y + sprite.size[1])
        new.paste(sprite, box, sprite)

    # Crop off the extra padding
    new = new.crop((0, 0, sx - 90, sy - 90))

    # Also save to file for reference
    fn = r".\transition_view.png"
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    new.save(fn)
    print(f"Transition view saved to {fn} (centered on {px}, {py})")

    return new


def get_start_coords(transition_img=None):
    result = []

    def validate_data():
        nonlocal result
        try:
            sid, px, py, rid = entry.get().replace(" ", "").split(",")
            result.append(int(sid))
            result.append(int(rid))
            result.append(int(px))
            result.append(int(py))
        except ValueError:
            result = []
            entry.focus_set()
            return
        root.quit()
        root.destroy()

    def close_window():
        root.quit()
        root.destroy()

    root = tk.Tk()
    root.title("Region Transition")
    root.protocol("WM_DELETE_WINDOW", close_window)

    # If we have a transition image, display it
    if transition_img is not None:
        # Scale image to fit reasonably in dialog (max 400px)
        img_width, img_height = transition_img.size
        max_size = 500
        if img_width > max_size or img_height > max_size:
            scale = min(max_size / img_width, max_size / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            display_img = transition_img.resize((new_width, new_height), Image.LANCZOS)
        else:
            display_img = transition_img

        # Convert to PhotoImage for tkinter (specify master to avoid conflicts)
        photo = ImageTk.PhotoImage(display_img, master=root)
        img_label = tk.Label(root, image=photo)
        img_label.image = photo  # Keep reference to prevent garbage collection
        img_label.pack(pady=5)

        label = tk.Label(root, text="Last position before transition")
        label.pack()

    # Description of what's needed
    desc = tk.Label(root, text="Enter the coordinates where your character is now standing.",
        wraplength=400, justify="center")
    desc.pack(fill="x", padx=10, pady=(10, 5))

    desc2 = tk.Label(root, text="Segment ID is the world area (run get segments.py to list).\n"
        "X/Y are your tile coordinates in the region.\n"
        "Region ID identifies the specific map area.\n\n"
        "Tip: Use /props in-game to see x, y, [region]",
        wraplength=400, justify="center", fg="gray")
    desc2.pack(fill="x", padx=10, pady=(0, 10))

    label = tk.Label(root, text="Format: segment, x, y, region")
    label.pack(fill="x")
    label = tk.Label(root, text="Example: 1, 25, 30, 5")
    label.pack(fill="x")
    entry = tk.Entry(root, justify='center')
    entry.pack(fill="x", padx=10)
    button = tk.Button(root, text="Submit", command=validate_data)
    button.pack(pady=5)
    entry.focus_set()

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()
    return result


def segment_region(sid, rid):
    global conn, cur
    sql = """\
        select sno
        from segment
        where segmentid = %s
        """
    prm = (sid,)
    cur.execute(sql, prm)
    if not cur.rowcount:
        msg = f"Segment {sid} not found."
        raise ValueError(msg)
    sno = cur.fetchone()["sno"]

    sql = """\
        select srno
        from segmentregion
        where regionid = %s
        and sno = %s
        """
    prm = (rid, sno)
    cur.execute(sql, prm)
    if not cur.rowcount:
        sql = """\
            insert into segmentregion
                (sno, regionid, regionname)
            values (%s, %s, %s)
            returning srno
            """
        prm = (sno, rid, f"region {rid}")
        cur.execute(sql, prm)
    srno = cur.fetchone()["srno"]
    return srno


def region_tile(srno, tx, ty):
    global conn, cur
    sql = """\
        select rtno
        from regiontile
        where srno = %s
        and tx = %s
        and ty = %s
        """
    prm = (srno, tx, ty)
    cur.execute(sql, prm)
    if not cur.rowcount:
        sql = """\
            insert into regiontile
                (srno, tx, ty)
            values (%s, %s, %s)
            returning rtno
            """
        prm = (srno, tx, ty)
        cur.execute(sql, prm)
    rtno = cur.fetchone()["rtno"]
    return rtno


def tile_component(rtno, color):
    global conn, cur
    sql = """\
        select tcno
        from tilecomponent
        where rtno = %s
        and color = %s
        """
    prm = (rtno, color)
    cur.execute(sql, prm)
    if not cur.rowcount:
        sql = """\
            insert into tilecomponent
                (rtno, color)
            values (%s, %s)
            returning tcno
            """
        prm = (rtno, color)
        cur.execute(sql, prm)
    tcno = cur.fetchone()["tcno"]
    return tcno


def component_terrain(tcno, terrainid):
    global conn, cur
    sql = """\
        select ctno
        from componentterrain
        where tcno = %s
        and terrainid = %s
        """
    prm = (tcno, terrainid)
    cur.execute(sql, prm)
    if not cur.rowcount:
        sql = """\
            insert into componentterrain
                (tcno, terrainid, base, wall, door)
            values (%s, %s, 0, 0, 0)
            """
        prm = (tcno, terrainid)
        cur.execute(sql, prm)


def load_replay_file():
    root = tk.Tk()
    root.withdraw()
    fn = askopenfilename(
        title="Select the replay file to load",
        initialdir=r"C:\Users\mzimm\Downloads\Stormhalter\Replays",
        filetypes=[("Replay Files", "*.sr")]
        )
    root.destroy()  # Properly destroy the root to avoid tkinter conflicts
    if fn:
        print(fn, file=trace)
        print(fn)
        with open(fn, "rb") as file:
            data = file.read()
    else:
        data = None
    return data


if __name__ == "__main__":
    trace = open(r".\trace.txt", "w")
    data = load_replay_file()
    if data:
        conn = get_connection()
        cur = conn.cursor()
        process_moves()
