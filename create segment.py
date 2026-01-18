import argparse

from db_config import get_connection


def main():
    parser = argparse.ArgumentParser(
        description='Create a new segment for mapping')
    parser.add_argument('--segmentname', type=str, required=True,
        help='Name of the new segment')
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    # Check if segment already exists by name
    sql = """\
        select segmentid, segmentname
        from segment
        where segmentname = %s
        """
    cur.execute(sql, (args.segmentname,))
    row = cur.fetchone()
    if row:
        print(f"Segment '{args.segmentname}' already exists with segmentid {row['segmentid']}")
        return

    # Find the next available segmentid
    sql = """\
        select coalesce(max(segmentid), 0) + 1 as next_id
        from (
            select segmentid from segment
            union
            select segmentid from segmentids
        ) combined
        """
    cur.execute(sql)
    next_id = cur.fetchone()["next_id"]

    print(f"Creating segment '{args.segmentname}' with segmentid {next_id}")

    # Insert into segment table
    sql = """\
        insert into segment (segmentid, segmentname)
        values (%s, %s)
        returning sno
        """
    cur.execute(sql, (next_id, args.segmentname))
    sno = cur.fetchone()["sno"]
    print(f"  segment: inserted (sno={sno})")

    # Insert into segmentids table
    sql = """\
        insert into segmentids (segmentid, segmentname)
        values (%s, %s)
        returning sino
        """
    cur.execute(sql, (next_id, args.segmentname))
    sino = cur.fetchone()["sino"]
    print(f"  segmentids: inserted (sino={sino})")

    conn.commit()
    print("Done.")


if __name__ == "__main__":
    main()
