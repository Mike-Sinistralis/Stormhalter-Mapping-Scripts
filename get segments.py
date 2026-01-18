from db_config import get_connection


def main():
    conn = get_connection()
    cur = conn.cursor()

    sql = """\
        select segmentid, segmentname
        from segment
        order by segmentid
        """
    cur.execute(sql)
    rows = cur.fetchall()

    if not rows:
        print("No segments found.")
        return

    print(f"{'ID':<6} {'Name'}")
    print("-" * 30)
    for row in rows:
        print(f"{row['segmentid']:<6} {row['segmentname']}")


if __name__ == "__main__":
    main()
