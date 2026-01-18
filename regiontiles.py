from db_config import get_connection


def main():
    conn = get_connection()
    cur = conn.cursor()
    sql = """\
        select rtno
        from regiontile
        -- where srno = 93
        """
    cur.execute(sql)
    rows = cur.fetchall()
    i = 0
    for row in rows:
        if i % 500 == 0:
            print(i)
        i += 1
        tileadjust(cur, row["rtno"])
        conn.commit()
    print(i)
    # tileadjust(cur, 94594)
    # conn.commit()


def tileadjust(cur, rtno):
    # sql = """\
    #     # delete ct.*
    #     # from componentterrain as ct
    #     # on ct.tcno = tc.tcno
    #     # where tc.rtno = ?
    #     # -- 7 dark, 131 web, 134 icestorm, 135 fireball
    #     # -- 187 poison cloud, 188 lightning, 340 concussion
    #     # and ct.terrainid in (7,131,134,135,187,188,340)
    #     # and (select ke.rtno
    #     #     from keepeffect as ke
    #     #     where ke.rtno = tc.rtno
    #     #     and ke.terrainid = ct.terrainid) is null,
    #     """
    # prm = (rtno,)
    # cur.execute(sql, prm)
    sql = """\
        select ct.ctno, ct.terrainid, bs.spritecategory, ke.keno
        from tilecomponent tc
        inner join componentterrain ct
            on ct.tcno = tc.tcno
        inner join terraintexture tt
            on tt.terrainid = ct.terrainid
        inner join texturebitmap tb
            on tb.ttno = tt.ttno
        inner join bitmapsprites bs
            on bs.texture = tb.texture
            and bs.cx = tb.cx
            and bs.cy = tb.cy
        left join keepeffect ke
            on ke.ctno = ct.ctno
        where tc.rtno = %s
        order by ct.ctno
        """
    prm = (rtno,)
    cur.execute(sql, prm)
    rows = cur.fetchall()

    # -- 7 dark, 131 web, 134 icestorm, 135 fireball
    # -- 187 poison cloud, 188 lightning, 340 concussion
    # for row in rows:
    # if row["keno"]:
    #     print("keno", row)
    # if row["terrainid"] in (7, 131, 134, 135, 187, 188, 340):
    # if (row["terrainid"] in (7, 131, 134, 135, 187, 188, 340)
    # and row["keno"] is None):
    #     print("terrainid", row)

    dh = False
    dho = False
    dhc = False
    dhr = False
    dv = False
    dvo = False
    dvc = False
    dvr = False

    wv = False
    wvn = False
    wvd = False
    wh = False
    whn = False
    whd = False
    wc = False
    wcn = False
    wcd = False

    for row in rows:

        if row["spritecategory"] == "door vertical closed":
            dvc = True
        elif row["spritecategory"] == "door vertical open":
            dvo = True
        elif row["spritecategory"] == "door vertical ruins":
            dvr = True

        elif row["spritecategory"] == "door horizontal closed":
            dhc = True
        elif row["spritecategory"] == "door horizontal open":
            dho = True
        elif row["spritecategory"] == "door horizontal ruins":
            dhr = True

        elif row["spritecategory"] == "wall vertical normal":
            wvn = True
        elif row["spritecategory"] == "wall vertical destroyed":
            wvd = True

        elif row["spritecategory"] == "wall horizontal normal":
            whn = True
        elif row["spritecategory"] == "wall horizontal destroyed":
            whd = True

        elif row["spritecategory"] == "wall corner normal":
            wcn = True
        elif row["spritecategory"] == "wall corner destroyed":
            wcd = True

    if (dvc
    or dvo
    or dvr):
        dv = True
        if dvo:
            dvc = False
            dvr = False
        elif dvc:
            dvr = False
        wvn = False
        wvd = False

    if (dhc
    or dho
    or dhr):
        dh = True
        if dho:
            dhc = False
            dhr = False
        elif dhc:
            dhr = False
        whn = False
        whd = False

    if (wvn
    or wvd):
        wv = True
    if wvn:
        wvd = False

    if (whn
    or whd):
        wh = True
    if whn:
        whd = False

    if (wcn
    or wcd):
        wc = True
    if wcn:
        wcd = False

    ctno = None
    base = None
    wall = None
    door = None
    for row in rows:
        if (row["ctno"] != ctno
        and ctno):
            update_componentterrain(cur, ctno, base, wall, door)
        if (row["ctno"] != ctno
        or not ctno):
            ctno = row["ctno"]
            base = 0
            wall = 0
            door = 0

        if row["spritecategory"] == "door vertical threshhold":
            if dv:
                door |= 16 | 4 | 2 | 1
        elif row["spritecategory"] == "door vertical open":
            door |= 2 | 1
        elif row["spritecategory"] == "door vertical closed":
            door |= 4
            if dvc:
                door |= 1
        elif row["spritecategory"] == "door vertical ruins":
            door |= 16
            if dvr:
                door |= 1
        elif (row["spritecategory"] == "door vertical jamb"
        or row["spritecategory"] == "door vertical ruins jamb"
        or row["spritecategory"] == "door vertical layers"):
            pass  # controlled by another part of the terraintexture

        elif row["spritecategory"] == "door horizontal threshhold":
            if dh:
                door |= 16 | 4 | 2 | 1
        elif row["spritecategory"] == "door horizontal open":
            door |= 2 | 1
        elif row["spritecategory"] == "door horizontal closed":
            door |= 4
            if dhc:
                door |= 1
        elif row["spritecategory"] == "door horizontal ruins":
            door |= 16
            if dhr:
                door |= 1
        elif (row["spritecategory"] == "door horizontal jamb"
        or row["spritecategory"] == "door horizontal ruins jamb"
        or row["spritecategory"] == "door horizontal layers"):
            pass  # controlled by another part of the terraintexture

        elif row["spritecategory"] == "wall vertical normal":
            wall |= 2  # wall normal
            if wvn:
                wall |= 1  # wall normal on map
            else:  # door
                door |= 8  # wall normal when door hidden
        elif row["spritecategory"] == "wall vertical destroyed":
            wall |= 16  # wall destroyed
            if wvd:
                wall |= 1  # wall destroyed on map
        elif row["spritecategory"] == "wall vertical layers":
            if wv:
                wall |= 2  # wall normal
                if wvn:
                    wall |= 1  # wall normal on map
                if dv:
                    door |= 8  # wall normal when door hidden
            else:
                base |= 1  # no wall - always show on map

        elif row["spritecategory"] == "wall horizontal normal":
            wall |= 2  # wall normal
            if whn:
                wall |= 1  # wall normal on map
            else:  # door
                door |= 8  # wall normal when door hidden
        elif row["spritecategory"] == "wall horizontal destroyed":
            wall |= 16  # wall destroyedv
            if whd:
                wall |= 1  # wall destroyed on map
        elif row["spritecategory"] == "wall horizontal layers":
            if wh:
                wall |= 2  # wall normal
                if whn:
                    wall |= 1  # wall normal on map
                if dh:
                    door |= 8  # wall normal when door hidden
            else:
                base |= 1  # no wall - always show on map

        elif row["spritecategory"] == "wall corner normal":
            wall |= 2  # wall normal
            if wcn:
                wall |= 1  # wall normal on map
        elif row["spritecategory"] == "wall corner destroyed":
            wall |= 16  # wall destroyed
            if wcd:
                wall |= 1  # wall destroyed on map
        elif row["spritecategory"] == "wall corner layers":
            if wc:
                wall |= 2  # wall normal
                if wcn:
                    wall |= 1  # wall normal on map
            else:
                base |= 1  # no wall - always show on map

        elif row["spritecategory"] == "wall rubble":
            if (wv
            or wh
            or wc):  # wall exists
                wall |= 16  # wall destroyed
                if (wvd
                or whd
                or wcd):
                    wall |= 1  # wall destroyed on map
            else:
                base |= 1  # no wall - always show on map
        elif row["spritecategory"] == "wall vertical rubble":
            if wv:   # wall exists
                wall |= 16  # wall destroyed
                if wvd:
                    wall |= 1  # wall destroyed on map
            else:
                base |= 1  # no wall - always show on map
        elif row["spritecategory"] == "wall horizontal rubble":
            if wh:   # wall exists
                wall |= 16  # wall destroyed
                if whd:
                    wall |= 1  # wall destroyed on map
            else:
                base |= 1  # no wall - always show on map

        else:
            base |= 1

    update_componentterrain(cur, ctno, base, wall, door)


def update_componentterrain(cur, ctno, base, wall, door):
    sql = """\
        update componentterrain
        set base = %s, wall =  %s, door = %s
        where ctno = %s
        """
    prm = (base, wall, door, ctno)
    cur.execute(sql, prm)


if __name__ == "__main__":
    main()
