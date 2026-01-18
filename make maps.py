import os
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import bitmapfiles
from db_config import get_connection

COORDS = True

# Thread-safe lock for bitmapfiles cache access
bitmap_lock = threading.Lock()

# Shared resources that are read-only after initialization
font50 = None
coord_template = None
annotate_template = None


def init_shared_resources():
    """Initialize shared resources used by all threads."""
    global font50, coord_template, annotate_template

    font50 = ImageFont.truetype(r"font\CommitMono-400-Regular.otf", 50)

    if COORDS:
        coord_template = Image.new('RGBA', (110, 110), (255, 255, 255, 255))
        pixels = coord_template.load()
        # add border around the coordinate numbers
        for i in range(110):
            pixels[0, i] = (0, 0, 0, 255)
            pixels[i, 0] = (0, 0, 0, 255)
            pixels[109, i] = (0, 0, 0, 255)
            pixels[i, 109] = (0, 0, 0, 255)

    annotate_template = Image.new('RGBA', (110, 110), (255, 255, 0, 192))


def extract_sprite_threadsafe(texture, cx, cy, sx, sy, ox, oy, color):
    """Thread-safe wrapper for bitmapfiles.extract_sprite."""
    with bitmap_lock:
        return bitmapfiles.extract_sprite(texture, cx, cy, sx, sy, ox, oy, color)


def generate_map(sr_data):
    """Generate a single map. Called from thread pool."""
    # Each thread gets its own database connection
    conn = get_connection()

    try:
        sr = sr_data
        segment_name = sr["segmentname"]
        region_name = sr["regionname"]
        srno = sr["srno"]

        # Get X coordinates
        sql = """\
            select distinct tx
            from regiontile
            where srno = %s
            order by tx
            """
        rtc = conn.cursor()
        rtc.execute(sql, (srno,))
        rows = rtc.fetchall()

        if not rows:
            return f"{segment_name} {region_name} - No tile data"

        xadj = []
        low = None
        high = None
        adj = None
        tlx = 0
        if COORDS:
            tlx += 1
        for row in rows:
            tx = row["tx"]
            if (low is None or tlx - tx != adj):
                if low is not None:
                    xadj.append([low, high, adj])
                    tlx += 1
                low = tx
                adj = tlx - low
            high = tx
            tlx += 1
        xadj.append([low, high, adj])

        # Get Y coordinates
        sql = """
            select distinct ty
            from regiontile
            where srno = %s
            order by ty
            """
        rtc.execute(sql, (srno,))
        rows = rtc.fetchall()
        yadj = []
        low = None
        high = None
        adj = None
        tly = 0
        if COORDS:
            tly += 1
        for row in rows:
            ty = row["ty"]
            if (low is None or tly - ty != adj):
                if low is not None:
                    yadj.append([low, high, adj])
                    tly += 1
                low = ty
                adj = tly - low
            high = ty
            tly += 1
        yadj.append([low, high, adj])

        # Make room for right and bottom coordinates
        if COORDS:
            tlx += 1
            tly += 1

        # Create the empty map image
        sx = tlx * 110 + 90
        sy = tly * 110 + 90
        new = Image.new(mode="RGBA", size=(sx, sy), color=(0, 0, 0, 0))

        if COORDS:
            # Create top X coordinates
            x = 0
            for low, high, _ in xadj:
                for c in range(low, high + 1):
                    x += 1
                    newcoord = coord_template.copy()
                    draw = ImageDraw.Draw(newcoord)
                    _, _, w, h = draw.textbbox((0, 0), str(c), font=font50)
                    draw.text(((110 - w) / 2, (110 - h) - 5), str(c),
                        (0, 0, 0, 255), font=font50)
                    box = (110 * x + 90, 0, 110 * x + 90 + 110, 110)
                    new.paste(newcoord, box, newcoord)
                x += 1

            # Copy X coordinates to bottom
            box = (0, 0, tlx * 110 + 90, 110)
            crop = new.crop(box)
            box = (0, tly * 110 + 90 - 110, tlx * 110 + 90, tly * 110 + 90)
            new.paste(crop, box, crop)

            # Create left Y coordinates
            y = 0
            for low, high, _ in yadj:
                for c in range(low, high + 1):
                    y += 1
                    newcoord = coord_template.copy()
                    draw = ImageDraw.Draw(newcoord)
                    _, _, w, h = draw.textbbox((0, 0), str(c), font=font50)
                    draw.text((110 - w - 5, (110 - h) / 2), str(c),
                        (0, 0, 0, 255), font=font50)
                    box = (0, 110 * y + 90, 110, 110 * y + 90 + 110)
                    new.paste(newcoord, box, newcoord)
                y += 1

            # Copy Y coordinates to right
            box = (0, 0, 110, tly * 110 + 90)
            crop = new.crop(box)
            box = (tlx * 110 + 90 - 110, 0, tlx * 110 + 90, tly * 110 + 90)
            new.paste(crop, box, crop)

        # Get tile sprites
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
            order by rt.tx, rt.ty, bs.render
            """
        tss = conn.cursor()
        tss.execute(sql, (srno,))

        while True:
            ts = tss.fetchone()
            if ts is None:
                break
            xindex = 0
            while ts["tx"] > xadj[xindex][1]:
                xindex += 1
            yindex = 0
            while ts["ty"] > yadj[yindex][1]:
                yindex += 1
            x = (ts["tx"] + xadj[xindex][2]) * 110
            y = (ts["ty"] + yadj[yindex][2]) * 110

            # Use thread-safe sprite extraction
            sprite = extract_sprite_threadsafe(
                ts["texture"], ts["cx"], ts["cy"], ts["sx"], ts["sy"],
                ts["ox"], ts["oy"], ts["color"]
            )
            box = (x, y, x + sprite.size[0], y + sprite.size[1])
            new.paste(sprite, box, sprite)

        mapfile = rf".\newmaps\{segment_name}\{region_name}.png"
        os.makedirs(os.path.dirname(mapfile), exist_ok=True)
        new.save(mapfile)

        # Annotated map
        sql = """
            select rt.tx, rt.ty, ta.line1, ta.line2
            from regiontile rt
            inner join tileannotate ta
                on ta.rtno = rt.rtno
            where rt.srno = %s
            order by rt.tx, rt.ty
            """
        tas = conn.cursor()
        tas.execute(sql, (srno,))

        if tas.rowcount:
            while True:
                ta = tas.fetchone()
                if ta is None:
                    break
                xindex = 0
                while ta["tx"] > xadj[xindex][1]:
                    xindex += 1
                yindex = 0
                while ta["ty"] > yadj[yindex][1]:
                    yindex += 1
                x = (ta["tx"] + xadj[xindex][2]) * 110 + 90
                y = (ta["ty"] + yadj[yindex][2]) * 110 + 90

                newannotate = annotate_template.copy()
                draw = ImageDraw.Draw(newannotate)
                if ta["line1"]:
                    font = find_font_size(ta["line1"])
                    _, _, w, h = font.getbbox(ta["line1"])
                    if ta["line2"]:
                        draw.text(
                            ((110 - w) / 2, 5), str(ta["line1"]),
                            (0, 48, 128, 255), font=font)
                    else:
                        draw.text(
                            ((110 - w) / 2, (110 - h) / 2), str(ta["line1"]),
                            (0, 48, 128, 255), font=font)
                if ta["line2"]:
                    font = find_font_size(ta["line2"])
                    _, _, w, h = font.getbbox(ta["line2"])
                    if ta["line1"]:
                        draw.text(
                            ((110 - w) / 2, 110 - h - 5), str(ta["line2"]),
                            (0, 48, 128, 255), font=font)
                    else:
                        draw.text(
                            ((110 - w) / 2, (110 - h) / 2), str(ta["line2"]),
                            (0, 48, 128, 255), font=font)

                box = (x, y, x + newannotate.size[0], y + newannotate.size[1])
                new.paste(newannotate, box, newannotate)

            mapfile = rf".\newmaps\{segment_name}\{region_name} Annotated.png"
            os.makedirs(os.path.dirname(mapfile), exist_ok=True)
            new.save(mapfile)

        return f"{segment_name} {region_name}"

    except Exception as e:
        return f"{sr_data['segmentname']} {sr_data['regionname']} - ERROR: {e}"

    finally:
        conn.close()


def find_font_size(text):
    size = 50
    while size > 0:
        font = ImageFont.truetype(r"font\CommitMono-400-Regular.otf", size)
        _, _, w, h = font.getbbox(text)
        if w <= 100:
            break
        size -= 1
    return font


def main():
    parser = argparse.ArgumentParser(description='Generate maps for Stormhalter segments and regions')
    parser.add_argument('--segment', type=int, help='Filter by segment ID')
    parser.add_argument('--region', type=int, help='Filter by region ID')
    parser.add_argument('--threads', type=int, default=4, help='Number of worker threads (default: 4)')
    args = parser.parse_args()

    # Initialize shared resources before spawning threads
    init_shared_resources()

    conn = get_connection()

    # Build the WHERE clause based on command line arguments
    where_clauses = []
    params = []

    # Base exclusion filter
    where_clauses.append("""(s.segmentname <> 'Bloodlands'
        or sr.regionname not in
        ('Hells Gate', 'Temple', 'Karma', 'tower top',
        'Praetoseba Surface', 'upper temple', 'tower level 2',
        'Sekhmet', 'Lower Praetoseba'))""")

    if args.segment:
        where_clauses.append("s.segmentid = %s")
        params.append(args.segment)

    if args.region:
        where_clauses.append("sr.regionid = %s")
        params.append(args.region)

    where_clause = " AND ".join(where_clauses)

    sql = f"""\
        select s.segmentid, s.segmentname, sr.srno, sr.regionid, sr.regionname
        from segment s
        inner join segmentregion sr
            on sr.sno = s.sno
        where {where_clause}
        order by s.segmentname, sr.regionname
        """

    srs = conn.cursor()
    if params:
        srs.execute(sql, params)
    else:
        srs.execute(sql)

    # Fetch all regions to process
    regions = srs.fetchall()
    conn.close()

    if not regions:
        print("No regions found to generate maps for.")
        return

    total = len(regions)
    print(f"Generating {total} maps using {args.threads} threads...")

    # Use ThreadPoolExecutor to process maps in parallel
    completed = 0
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # Submit all tasks
        future_to_region = {executor.submit(generate_map, sr): sr for sr in regions}

        # Process completed tasks as they finish
        for future in as_completed(future_to_region):
            completed += 1
            result = future.result()
            print(f"[{completed}/{total}] {result}")

    print(f"\nCompleted generating {total} maps.")


if __name__ == "__main__":
    main()
