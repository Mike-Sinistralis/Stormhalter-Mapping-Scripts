from bs4 import BeautifulSoup
import glob
import pyodbc
import os
import re


class loadxml():

    def __init__(self):
        self.conn = pyodbc.connect(
            r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
            r"DBQ=.\stormhalter item & spell.accdb;"
        )
        self.cur = self.conn.cursor()
        self.cur.execute(
            "delete from itemsprite"
        )
        self.conn.commit()
        self.xmlfiles()

    def xmlfiles(self):
        self.isno = 0
        for fn in glob.glob(r".\unzip\**\items*.xml", recursive=True):
            print(os.path.basename(fn))
            with open(fn, "r") as file:
                xml = file.read()
                xml = re.sub(r'\s*\n\s*', r'', xml, flags=re.M)
                soup = BeautifulSoup(xml, "xml")

                # tagdict = {}
                # for tag in soup.attrs:
                #     tagdict[tag] = soup[tag]
                # for tag in soup.find_all(recursive=False):
                #     tagdict[tag.name] = tag.string
                # print("soup:", tagdict)

                for tag in soup.find_all(recursive=False):
                    if tag.name == "data":
                        self.process_data(tag)
                self.conn.commit()

    def process_data(self, datatag):
        # tagdict = {}
        # for tag in datatag.attrs:
        #     tagdict[tag] = datatag[tag]
        # for tag in datatag.find_all(recursive=False):
        #     tagdict[tag.name] = tag.string
        # print("data:", tagdict)

        for tag in datatag.find_all(recursive=False):
            if tag.name == "item":
                self.process_item(tag)

    def process_item(self, itemtag):
        tagdict = {}
        for tag in itemtag.attrs:
            tagdict[tag] = itemtag[tag]
        for tag in itemtag.find_all(recursive=False):
            tagdict[tag.name] = tag.string

        tagdict["texture"] = tagdict.get("texture", "").replace("/", "\\")
        tagdict["source"] = tagdict.get("source", "").strip("()")
        tagdict["offset"] = tagdict.get("offset", "0,0").strip("()")
        # print("item:", tagdict)

        self.isno += 1
        cx, cy, sx, sy = tagdict["source"].split(",")
        ox, oy = tagdict["offset"].split(",")
        self.cur.execute(
            "insert into itemsprite ("
            "    isno, itemid, resolution,"
            "    texture, cx, cy, sx, sy, ox, oy)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self.isno, tagdict["id"], tagdict.get("resolution"),
            tagdict["texture"], cx, cy, sx, sy, ox, oy
        )


if __name__ == "__main__":
    loadxml()
