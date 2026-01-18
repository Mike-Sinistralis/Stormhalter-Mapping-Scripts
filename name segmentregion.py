import argparse

from db_config import get_connection


def main():
    parser = argparse.ArgumentParser(
        description='Update the region name for a segment region')
    parser.add_argument('--segment', type=int, required=True,
        help='Segment ID')
    parser.add_argument('--region', type=int, required=True,
        help='Region ID')
    parser.add_argument('--regionname', type=str, required=True,
        help='New region name')
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    # Look up the srno and current name
    sql = """\
        select sr.srno, sr.regionname, s.segmentname
        from segmentregion sr
        inner join segment s
            on s.sno = sr.sno
        where s.segmentid = %s
        and sr.regionid = %s
        """
    cur.execute(sql, (args.segment, args.region))
    row = cur.fetchone()

    if not row:
        print(f"No region found for segment {args.segment}, region {args.region}")
        return

    srno = row["srno"]
    old_name = row["regionname"]
    print(f"Updating: {row['segmentname']} / {old_name} (srno={srno})")
    print(f"  Old name: {old_name}")
    print(f"  New name: {args.regionname}")

    # Update the region name
    sql = """\
        update segmentregion
        set regionname = %s
        where srno = %s
        """
    cur.execute(sql, (args.regionname, srno))

    conn.commit()
    print("Done.")


if __name__ == "__main__":
    main()
