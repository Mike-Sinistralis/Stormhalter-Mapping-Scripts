from db_config import get_connection


# from PIL import Image
# im = Image.open(image_filename)
# width, height = im.size


def main():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "delete from bitmapgeneratedsprites"
    )
    conn.commit()
    sql = """\
        select *
        from bitmapfiles
        """
    cur.execute(sql)
    rows = cur.fetchall()
    sql = """\
        insert into bitmapgeneratedsprites
            (texture, cx, cy)
        values (%s, %s, %s)
        """
    for row in rows:
        texture = row["texture"].replace("/", "\\")
        for x in range(0, row["dx"], row["sx"]):
            for y in range(0, row["dy"], row["sy"]):
                prm = (texture, x, y)
                cur.execute(sql, prm)

    conn.commit()


if __name__ == "__main__":
    main()
