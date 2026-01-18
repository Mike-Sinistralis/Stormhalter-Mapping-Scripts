from bs4 import BeautifulSoup
import glob
import os
import re

from db_config import get_connection


class terrain():

    def __init__(self):
        self.conn = get_connection()
        self.cur = self.conn.cursor()

        self.ttno = 0
        self.tbno = 0

        self.cur.execute("delete from texturebitmap")
        self.cur.execute("delete from terraintexture")
        self.conn.commit()

        self.xmlfiles()

    def xmlfiles(self):
        for fn in glob.glob(r".\unzip\**\terrain*.xml", recursive=True):
            print(os.path.basename(fn))
            with open(fn, "r", encoding="utf-8-sig") as file:
                xml = file.read()

            xml = xml.replace("frame", "xframe")
            xml = re.sub(r'\s*\n\s*', r'', xml, flags=re.M)

            soup = BeautifulSoup(xml, "xml")

            # Terrain.xml root IS <data>, so check that first
            root_data = soup.find("data")
            if root_data:
                self.process_data(root_data)
            else:
                # fallback if the file is wrapped differently
                for datatag in soup.find_all("data"):
                    self.process_data(datatag)

            self.conn.commit()


    def process_data(self, datatag):
        # tagdict = {}
        # for tag in datatag.attrs:
        #     tagdict[tag] = datatag[tag]
        # for tag in datatag.find_all(recursive=False):
        #     tagdict[tag.name] = tag.string
        # print("data:", tagdict)

        for terraintag in datatag.find_all("terrain"):
            self.process_terrain(terraintag)

    def process_terrain(self, terraintag):
        # tagdict = {}
        # for tag in terraintag.attrs:
        #     tagdict[tag] = terraintag[tag]
        # for tag in terraintag.find_all(recursive=False):
        #     tagdict[tag.name] = tag.string
        # print("terrain:", tagdict)

        terrain_id = terraintag["id"]

        # Check if this terrain ID already exists (from another XML file)
        self.cur.execute("select ttno from terraintexture where terrainid = %s", (terrain_id,))
        existing = self.cur.fetchone()

        if existing:
            # Use existing ttno for this terrain
            self.ttno = existing["ttno"]
            # Delete old texture bitmaps for this terrain so we can re-add them
            self.cur.execute("delete from texturebitmap where ttno = %s", (self.ttno,))
        else:
            # Create new terrain texture entry
            self.ttno += 1
            sql = """\
                insert into terraintexture
                    (ttno, terrainid)
                values (%s, %s)
                """
            prm = (self.ttno, terrain_id)
            self.cur.execute(sql, prm)

        for spritetag in terraintag.find_all("sprite"):
            self.process_sprite(spritetag)


    def process_sprite(self, spritetag):
        tagdict = {}
        for tag in spritetag.attrs:
            tagdict[tag] = spritetag[tag]
        for tag in spritetag.find_all(recursive=False):
            tagdict[tag.name] = tag.string
        if "xframes" in tagdict:
            for tag in spritetag.find_all(recursive=False):
                if tag.name == "xframes":
                    tagdict["source"] = self.select_frame(tag).strip("()")
        tagdict["texture"] = tagdict.get("texture", "").replace("/", "\\")
        tagdict["source"] = tagdict.get("source", "").strip("()")
        tagdict["offset"] = tagdict.get("offset", "0,0").strip("()")
        # print("sprite:", tagdict)

        self.tbno += 1
        cx, cy, sx, sy = tagdict["source"].split(",")
        ox, oy = tagdict["offset"].split(",")

        sql = """\
            insert into texturebitmap
                (tbno, ttno, texture, cx, cy, sx, sy, ox, oy)
             values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        prm = (self.tbno, self.ttno, tagdict["texture"], cx, cy, sx, sy, ox, oy)
        self.cur.execute(sql, prm)

    def select_frame(self, framestag):
        # tagdict = {}
        # for tag in framestag.attrs:
        #     tagdict[tag] = framestag[tag]
        # for tag in framestag.find_all(recursive=False):
        #     tagdict[tag.name] = tag.string
        # print("frames:", tagdict)

        framelist = []
        for tag in framestag.find_all(recursive=False):
            if tag.name == "xframe":
                framelist.append(tag.string)
        return framelist[len(framelist) // 3]


if __name__ == "__main__":
    terrain()
