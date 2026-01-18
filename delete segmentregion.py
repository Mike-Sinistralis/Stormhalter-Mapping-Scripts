import argparse

from db_config import get_connection


def main():
    parser = argparse.ArgumentParser(
        description='Remove all tile data for a segment region')
    parser.add_argument('--segment', type=int, required=True,
        help='Segment ID')
    parser.add_argument('--region', type=int, required=True,
        help='Region ID')
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    # Look up the srno
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
    print(f"Deleting: {row['segmentname']} / {row['regionname']} (srno={srno})")

    # Delete keepeffect via componentterrain via tilecomponent via regiontile
    sql = """\
        delete from keepeffect
        where ctno in (
            select ct.ctno
            from componentterrain ct
            inner join tilecomponent tc on tc.tcno = ct.tcno
            inner join regiontile rt on rt.rtno = tc.rtno
            where rt.srno = %s
        )
        """
    cur.execute(sql, (srno,))
    print(f"  keepeffect: {cur.rowcount} rows deleted")

    # Delete componentterrain via tilecomponent via regiontile
    sql = """\
        delete from componentterrain
        where tcno in (
            select tc.tcno
            from tilecomponent tc
            inner join regiontile rt on rt.rtno = tc.rtno
            where rt.srno = %s
        )
        """
    cur.execute(sql, (srno,))
    print(f"  componentterrain: {cur.rowcount} rows deleted")

    # Delete tilecomponent via regiontile
    sql = """\
        delete from tilecomponent
        where rtno in (
            select rtno from regiontile where srno = %s
        )
        """
    cur.execute(sql, (srno,))
    print(f"  tilecomponent: {cur.rowcount} rows deleted")

    # Delete tileannotate via regiontile
    sql = """\
        delete from tileannotate
        where rtno in (
            select rtno from regiontile where srno = %s
        )
        """
    cur.execute(sql, (srno,))
    print(f"  tileannotate: {cur.rowcount} rows deleted")

    # Delete tiledestination via regiontile
    sql = """\
        delete from tiledestination
        where rtno in (
            select rtno from regiontile where srno = %s
        )
        """
    cur.execute(sql, (srno,))
    print(f"  tiledestination: {cur.rowcount} rows deleted")

    # Delete regiontile
    sql = "delete from regiontile where srno = %s"
    cur.execute(sql, (srno,))
    print(f"  regiontile: {cur.rowcount} rows deleted")

    # Delete segmentregion
    sql = "delete from segmentregion where srno = %s"
    cur.execute(sql, (srno,))
    print(f"  segmentregion: {cur.rowcount} rows deleted")

    conn.commit()
    print("Done.")


if __name__ == "__main__":
    main()
