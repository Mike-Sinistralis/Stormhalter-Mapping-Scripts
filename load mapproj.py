from operator import itemgetter
import re
import tkinter as tk
from tkinter.filedialog import askopenfilename
from bs4 import BeautifulSoup

from regiontiles import tileadjust
from db_config import get_connection


def process_map():
    global soup, conn, cur
    # tagdict = {}
    # for tag in soup.attrs:
    #     tagdict[tag] = soup[tag]
    # for tag in soup.find_all(recursive=False):
    #     tagdict[tag.name] = tag.string
    # print("soup:", tagdict)

    for tag in soup.find_all(recursive=False):
        if tag.name == "segment":
            process_segment(tag)


def process_segment(segmenttag):
    global conn, cur
    # tagdict = {}
    # for tag in segmenttag.attrs:
    #     tagdict[tag] = segmenttag[tag]
    # for tag in segmenttag.find_all(recursive=False):
    #     tagdict[tag.name] = tag.string
    # print("segment:", tagdict)

    print(segmenttag["name"])

    sql = """\
        select sno
        from segment
        where segmentname = %s
        """
    prm = (segmenttag["name"],)
    cur.execute(sql, prm)
    if not cur.rowcount:
        msg = f"Segment {segmenttag["name"]} not found."
        raise ValueError(msg)
    sno = cur.fetchone()["sno"]

    for tag in segmenttag.find_all(recursive=False):
        if tag.name == "regions":
            process_regions(sno, tag)


def process_regions(sno, regionstag):
    global conn, cur
    # tagdict = {}
    # for tag in regionstag.attrs:
    #     tagdict[tag] = regionstag[tag]
    # for tag in regionstag.find_all(recursive=False):
    #     tagdict[tag.name] = tag.string
    # print("regions:", tagdict)

    for tag in regionstag.find_all(recursive=False):
        if tag.name == "region":
            process_region(sno, tag)


def process_region(sno, regiontag):
    global conn, cur
    tagdict = {}
    for tag in regiontag.attrs:
        tagdict[tag] = regiontag[tag]
    for tag in regiontag.find_all(recursive=False):
        tagdict[tag.name] = tag.string
    # print("region:", tagdict)

    print(tagdict["name"])

    # This should not be run unless there is a new mapproj file.
    # sql = """\
    #     delete from segmentregion
    #     where regionid = %s
    #     and sno = %s
    #     """
    # prm = (tagdict["id"], sno)
    # cur.execute(sql, prm)

    sql = """\
        select srno
        from segmentregion
        where regionid = %s
        and sno = %s
        """
    prm = (tagdict["id"], sno)
    cur.execute(sql, prm)
    if not cur.rowcount:
        sql = """\
            insert into segmentregion
                (sno, regionid, regionname)
            values (%s, %s, %s)
            returning srno
            """
        prm = (sno, tagdict["id"], tagdict["name"])
        cur.execute(sql, prm)
    srno = cur.fetchone()["srno"]

    for tag in regiontag.find_all(recursive=False):
        if tag.name == "tile":
            process_tile(srno, tag)


def process_tile(srno, tiletag):
    global conn, cur
    destinationdict, terrainlist = load_tile(tiletag)
    if (destinationdict
    or terrainlist):
        sql = """\
            select rtno
            from regiontile
            where srno = %s
            and tx = %s
            and ty = %s
            """
        prm = (srno, tiletag["x"], tiletag["y"])
        cur.execute(sql, prm)
        if not cur.rowcount:
            sql = """\
                insert into regiontile
                    (srno, tx, ty)
                values (%s, %s, %s)
                returning rtno
                """
            prm = (srno, tiletag["x"], tiletag["y"])
            cur.execute(sql, prm)
        rtno = cur.fetchone()["rtno"]

    if destinationdict:
        segmentid = destinationdict["destinationsegment"]
        sql = """\
            select td.tdno
            from tiledestination td
            inner join segment s
                on s.sno = td.sno
            where td.rtno = %s
            and s.segmentid = %s
            """
        prm = (rtno, segmentid)
        cur.execute(sql, prm)
        if not cur.rowcount:
            sql = """\
                insert into tiledestination
                    (rtno, sno)
                values (%s,
                    (select sno
                    from segment
                    where segmentid = %s))
                """
            prm = (rtno, segmentid)
            cur.execute(sql, prm)

    if terrainlist:
        terrainlist.sort(key=itemgetter(1, 0))  # sort color, terrainid
        colorsave = None
        for terrainid, color in terrainlist:
            if (colorsave is None
            or color != colorsave):
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
                colorsave = color
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
        tileadjust(cur, rtno)
    conn.commit()


def load_tile(tiletag):
    global conn, cur
    # tagdict = {}
    # for tag in tiletag.attrs:
    #     tagdict[tag] = tiletag[tag]
    # for tag in tiletag.find_all(recursive=False):
    #     tagdict[tag.name] = tag.string
    # print("tile:", tagdict)
    destinationdict = {}
    terrainlist = []
    for componenttag in tiletag.find_all(recursive=False):
        if componenttag.name != "component":
            continue
        componenttype = None
        for tag in componenttag.attrs:
            if tag == "type":
                componenttype = componenttag[tag].lower()
            tagdict = {}
            color = "-"
            secret = None
            indestructible = None
            for tag in componenttag.find_all(recursive=False):
                tagname = tag.name.lower()
                tagvalue = tag.string
                if tagvalue:
                    tagvalue = tagvalue.lower()
                if tagname == "color":
                    color = f"{tag["r"]}, {tag["g"]}, {tag["b"]}, {tag["a"]}"
                    continue
                if tagname == "issecret":
                    secret = tagvalue
                    continue
                if tagname == "indestructible":
                    indestructible = tagvalue
                    continue
                tagdict[tagname] = tagvalue
        for tagname, tagvalue in tagdict.items():
            if (tagvalue is None
            or not tagvalue.isdigit()
            or tagvalue == "0"):
                continue

            if (secret == "true"
            and componenttype == "ropecomponent"  # leave out secret ropes
            and tagname == "teleporterid"):
                continue

            if (indestructible == "true"
            and componenttype == "wallcomponent"  # leave out indestructible destroyed walls
            and tagname in ("destroyed", "ruins")):
                continue

            if tagname in (
                "destinationsegment",
                # "destinationregion", "destinationsegment",
                # "destinationx", "destinationy"
            ):
                destinationdict[tagname] = tagvalue

            if tagname in (
                "altar", "closedid", "counter", "destroyed", "destroyedid",
                "egress", "ground", "obstruction", "openid", "ruins",
                "secretid", "static", "teleporterid", "tree", "wall"
            ):
                terrainlist.append([tagvalue, color])
    return destinationdict, terrainlist


def load_map_file():
    root = tk.Tk()
    root.withdraw()
    fn = askopenfilename(
        title="Select the map file to load",
        initialdir=r".\mapprojs",
        filetypes=[("Map Files", "*.mapproj")]
        )
    if fn:
        print(fn)
        with open(fn, "r") as file:
            xml = file.read()
            xml = re.sub(r'\s*\n\s*', r'', xml, flags=re.M)
            soup = BeautifulSoup(xml, "xml")
    else:
        soup = None
    return soup


if __name__ == "__main__":
    soup = load_map_file()
    if soup:
        conn = get_connection()
        cur = conn.cursor()
        process_map()
